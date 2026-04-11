"""Tests for MIDI → MUS conversion."""

from __future__ import annotations

import os
import struct

import pytest

from wadlib.lumps.mid2mus import MidiEvent, _parse_midi, midi_to_mus
from wadlib.lumps.mus import Mus
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Helpers — build a minimal MIDI file from scratch
# ---------------------------------------------------------------------------


def _vlq_encode(n: int) -> bytes:
    if n == 0:
        return b"\x00"
    buf: list[int] = []
    while n:
        buf.append(n & 0x7F)
        n >>= 7
    buf.reverse()
    for i in range(len(buf) - 1):
        buf[i] |= 0x80
    return bytes(buf)


def _build_midi(events: list[tuple[int, bytes]], tpqn: int = 70) -> bytes:
    """Build a minimal format-0 MIDI file from (delta, raw_event_bytes) pairs."""
    track_data = bytearray()
    for delta, ev in events:
        track_data += _vlq_encode(delta)
        track_data += ev
    # End of track
    track_data += b"\x00\xff\x2f\x00"

    header = struct.pack(">4sIHHH", b"MThd", 6, 0, 1, tpqn)
    track = struct.pack(">4sI", b"MTrk", len(track_data)) + bytes(track_data)
    return header + track


# ---------------------------------------------------------------------------
# MIDI parser tests
# ---------------------------------------------------------------------------


class TestMidiParser:
    def test_parse_empty_track(self) -> None:
        midi = _build_midi([])
        events = _parse_midi(midi)
        assert events == []

    def test_parse_note_on_off(self) -> None:
        midi = _build_midi([
            (0, bytes([0x90, 60, 100])),    # note on, C4, vel 100
            (70, bytes([0x80, 60, 0])),      # note off after 70 ticks
        ])
        events = _parse_midi(midi)
        assert len(events) == 2
        assert events[0].tick == 0
        assert events[0].status == 0x90
        assert events[1].tick == 70
        assert events[1].status == 0x80

    def test_parse_program_change(self) -> None:
        midi = _build_midi([
            (0, bytes([0xC0, 42])),  # program change to 42
        ])
        events = _parse_midi(midi)
        assert len(events) == 1
        assert events[0].status == 0xC0
        assert events[0].data == bytes([42])

    def test_parse_pitch_bend(self) -> None:
        midi = _build_midi([
            (0, bytes([0xE0, 0, 64])),  # pitch bend center
        ])
        events = _parse_midi(midi)
        assert len(events) == 1
        assert events[0].status == 0xE0

    def test_bad_magic_raises(self) -> None:
        with pytest.raises(ValueError, match="Not a MIDI"):
            _parse_midi(b"NOT_MIDI_DATA")


# ---------------------------------------------------------------------------
# MIDI → MUS conversion — synthetic inputs
# ---------------------------------------------------------------------------


class TestMidiToMus:
    def test_empty_midi(self) -> None:
        midi = _build_midi([])
        mus = midi_to_mus(midi)
        assert mus[:4] == b"MUS\x1a"

    def test_single_note(self) -> None:
        midi = _build_midi([
            (0, bytes([0x90, 60, 100])),   # note on
            (70, bytes([0x80, 60, 0])),     # note off
        ])
        mus = midi_to_mus(midi)
        assert mus[:4] == b"MUS\x1a"
        # Parse header
        _, score_len, score_start, _, _, _, _ = struct.unpack("<4sHHHHHH", mus[:16])
        assert score_len > 0
        assert score_start >= 16

    def test_program_change(self) -> None:
        midi = _build_midi([
            (0, bytes([0xC0, 42])),         # program change
            (0, bytes([0x90, 60, 100])),     # note on
            (70, bytes([0x80, 60, 0])),      # note off
        ])
        mus = midi_to_mus(midi)
        # Should have instrument 42 in the instrument list
        _, _, score_start, _, _, num_instr, _ = struct.unpack("<4sHHHHHH", mus[:16])
        assert num_instr == 1
        instr_start = 16
        (instr,) = struct.unpack("<H", mus[instr_start : instr_start + 2])
        assert instr == 42

    def test_percussion_channel_mapping(self) -> None:
        """MIDI channel 9 (percussion) should map to MUS channel 15."""
        midi = _build_midi([
            (0, bytes([0x99, 36, 100])),   # note on, channel 9 (percussion)
            (70, bytes([0x89, 36, 0])),     # note off
        ])
        mus = midi_to_mus(midi)
        # Parse score data to verify channel 15 is used
        _, _, score_start, _, _, _, _ = struct.unpack("<4sHHHHHH", mus[:16])
        # First event descriptor should have channel 15 in lower nibble
        descriptor = mus[score_start]
        assert (descriptor & 0x0F) == 15

    def test_control_change_volume(self) -> None:
        midi = _build_midi([
            (0, bytes([0xB0, 7, 80])),  # CC 7 = volume
        ])
        mus = midi_to_mus(midi)
        assert mus[:4] == b"MUS\x1a"

    def test_note_on_velocity_zero_is_note_off(self) -> None:
        """MIDI note-on with velocity 0 should become MUS note-off."""
        midi = _build_midi([
            (0, bytes([0x90, 60, 100])),  # note on
            (70, bytes([0x90, 60, 0])),   # note on vel=0 → note off
        ])
        mus = midi_to_mus(midi)
        _, _, score_start, _, _, _, _ = struct.unpack("<4sHHHHHH", mus[:16])
        # Find the second event — should be type 0 (release note)
        # First event: play note (type 1)
        # Skip first event to find second
        pos = score_start
        desc1 = mus[pos]
        etype1 = (desc1 >> 4) & 0x07
        assert etype1 == 1  # play note
        # Skip its data
        note_byte = mus[pos + 1]
        pos += 2
        if note_byte & 0x80:  # has volume byte
            pos += 1
        # Check for delay (last bit)
        if desc1 & 0x80:
            while mus[pos] & 0x80:
                pos += 1
            pos += 1

        desc2 = mus[pos]
        etype2 = (desc2 >> 4) & 0x07
        assert etype2 == 0  # release note

    def test_pitch_bend_conversion(self) -> None:
        midi = _build_midi([
            (0, bytes([0xE0, 0, 64])),  # center bend (8192 / 64 = 128)
        ])
        mus = midi_to_mus(midi)
        _, _, score_start, _, _, _, _ = struct.unpack("<4sHHHHHH", mus[:16])
        descriptor = mus[score_start]
        etype = (descriptor >> 4) & 0x07
        assert etype == 2  # pitch wheel
        bend_val = mus[score_start + 1]
        assert bend_val == 128  # center

    def test_multi_channel(self) -> None:
        midi = _build_midi([
            (0, bytes([0x90, 60, 100])),    # ch 0
            (0, bytes([0x91, 64, 100])),    # ch 1
            (70, bytes([0x80, 60, 0])),
            (0, bytes([0x81, 64, 0])),
        ])
        mus = midi_to_mus(midi)
        _, _, _, prim, sec, _, _ = struct.unpack("<4sHHHHHH", mus[:16])
        assert prim + sec >= 2


# ---------------------------------------------------------------------------
# Round-trip: MUS → MIDI → MUS (structural equivalence)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealMidi:
    def test_convert_real_midi_to_mus(self) -> None:
        """Convert a real MIDI lump from freedoom2 to MUS and verify validity."""
        from wadlib.lumps.ogg import MidiLump

        with WadFile(FREEDOOM2) as wad:
            midi_lump = None
            for lump in wad.music.values():
                if isinstance(lump, MidiLump):
                    midi_lump = lump
                    break
            assert midi_lump is not None

            midi_data = midi_lump.raw()
            mus_data = midi_to_mus(midi_data)
            assert mus_data[:4] == b"MUS\x1a"

            # Verify MUS header
            _, score_len, score_start, prim, sec, num_instr, _ = struct.unpack(
                "<4sHHHHHH", mus_data[:16]
            )
            assert score_len > 0
            assert score_start >= 16
            assert prim + sec <= 16

    def test_convert_multiple_real_midis(self) -> None:
        """Convert several MIDI lumps and verify all produce valid MUS."""
        from wadlib.lumps.ogg import MidiLump

        with WadFile(FREEDOOM2) as wad:
            count = 0
            for name, lump in wad.music.items():
                if not isinstance(lump, MidiLump):
                    continue
                midi_data = lump.raw()
                mus_data = midi_to_mus(midi_data)
                assert mus_data[:4] == b"MUS\x1a", f"Failed for {name}"
                # Verify score end event
                _, score_len, score_start, _, _, _, _ = struct.unpack(
                    "<4sHHHHHH", mus_data[:16]
                )
                last_desc = mus_data[score_start + score_len - 1]
                assert (last_desc >> 4) & 0x07 == 6, f"Missing score end for {name}"
                count += 1
                if count >= 5:
                    break
            assert count > 0

    def test_midi_to_mus_to_midi_round_trip(self) -> None:
        """MIDI → MUS → MIDI should produce a playable MIDI."""
        from wadlib.lumps.ogg import MidiLump

        with WadFile(FREEDOOM2) as wad:
            midi_lump = None
            for lump in wad.music.values():
                if isinstance(lump, MidiLump):
                    midi_lump = lump
                    break
            assert midi_lump is not None

            orig_midi = midi_lump.raw()
            # MIDI → MUS → (need to parse as Mus lump to call to_midi)
            mus_data = midi_to_mus(orig_midi)

            # Create a Mus lump from the raw bytes to convert back
            from wadlib.directory import DirectoryEntry
            from io import BytesIO

            # Build a minimal WadFile-like object for DirectoryEntry
            class _FakeWad:
                def __init__(self, data: bytes) -> None:
                    self.fd = BytesIO(data)

            fake_wad = _FakeWad(mus_data)
            entry = DirectoryEntry(fake_wad, 0, len(mus_data), "D_TEST")  # type: ignore[arg-type]
            mus_lump = Mus(entry)

            # MUS → MIDI
            result_midi = mus_lump.to_midi()
            assert result_midi[:4] == b"MThd"

            # The result should be a valid MIDI that we can parse
            events = _parse_midi(result_midi)
            assert len(events) > 0
