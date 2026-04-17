"""Tests for DMX sound lump decoder."""

from __future__ import annotations

import itertools
import struct

from wadlib.lumps.sound import (
    _PC_SAMPLE_RATE,
    _PC_SPEAKER_FORMAT,
    _PC_TONES,
    DmxSound,
)
from wadlib.source import MemoryLumpSource
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pc_lump(notes: bytes) -> DmxSound:
    """Build a synthetic format-0 PC speaker lump from raw note bytes."""
    header = struct.pack("<HH", _PC_SPEAKER_FORMAT, len(notes))
    return DmxSound(MemoryLumpSource("DPTEST", header + notes))


def test_sounds_not_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.sounds) > 0


def test_sounds_keys_start_with_ds_or_dp(freedoom1_wad: WadFile) -> None:
    for name in freedoom1_wad.sounds:
        assert name.startswith("DS") or name.startswith("DP"), name


def test_get_sound_returns_dmxsound(freedoom1_wad: WadFile) -> None:
    snd = freedoom1_wad.get_sound("DSPISTOL")
    assert isinstance(snd, DmxSound)


def test_get_sound_case_insensitive(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_sound("dspistol") is not None


def test_get_sound_missing_returns_none(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_sound("DSNOEXIST") is None


def test_to_wav_starts_with_riff(freedoom1_wad: WadFile) -> None:
    snd = freedoom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    wav = snd.to_wav()
    assert wav[:4] == b"RIFF"


def test_to_wav_has_wave_marker(freedoom1_wad: WadFile) -> None:
    snd = freedoom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    wav = snd.to_wav()
    assert wav[8:12] == b"WAVE"


def test_to_wav_returns_bytes(freedoom1_wad: WadFile) -> None:
    snd = freedoom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    assert isinstance(snd.to_wav(), bytes)


# ---------------------------------------------------------------------------
# PC speaker format (format 0) — unit tests using synthetic lumps
# ---------------------------------------------------------------------------


class TestPcSpeaker:
    """Unit tests for DmxSound.to_wav() on format-0 PC speaker lumps."""

    def test_format_property_is_zero(self) -> None:
        snd = _make_pc_lump(b"\x00")
        assert snd.format == _PC_SPEAKER_FORMAT

    def test_rate_returns_synthesis_rate(self) -> None:
        snd = _make_pc_lump(b"\x01")
        assert snd.rate == _PC_SAMPLE_RATE

    def test_sample_count_is_note_count(self) -> None:
        notes = b"\x01\x02\x00"
        snd = _make_pc_lump(notes)
        assert snd.sample_count == 3

    def test_to_wav_returns_riff_wave(self) -> None:
        snd = _make_pc_lump(b"\x01" * 10)
        wav = snd.to_wav()
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    def test_wav_sample_rate_field_matches(self) -> None:
        snd = _make_pc_lump(b"\x01" * 10)
        wav = snd.to_wav()
        # WAV fmt chunk sample rate is at offset 24
        sample_rate = struct.unpack_from("<I", wav, 24)[0]
        assert sample_rate == _PC_SAMPLE_RATE

    def test_silence_note_produces_mid_level_samples(self) -> None:
        snd = _make_pc_lump(b"\x00" * 10)
        wav = snd.to_wav()
        # Find data chunk payload
        data_offset = 44  # standard PCM WAV: RIFF(12) + fmt(24) + data header(8)
        pcm = wav[data_offset:]
        assert all(b == 0x80 for b in pcm)

    def test_tone_note_produces_square_wave(self) -> None:
        snd = _make_pc_lump(b"\x01" * 10)  # index 1 → non-zero timer → audible tone
        wav = snd.to_wav()
        data_offset = 44
        pcm = wav[data_offset:]
        # Square wave should contain both high (0xC0) and low (0x40) samples
        assert 0xC0 in pcm and 0x40 in pcm

    def test_out_of_range_note_treated_as_silence(self) -> None:
        snd = _make_pc_lump(bytes([200]))  # index 200 > len(_PC_TONES)-1
        wav = snd.to_wav()
        data_offset = 44
        pcm = wav[data_offset:]
        assert all(b == 0x80 for b in pcm)

    def test_empty_notes_produces_empty_pcm(self) -> None:
        snd = _make_pc_lump(b"")
        wav = snd.to_wav()
        # data chunk size should be 0
        data_size = struct.unpack_from("<I", wav, 40)[0]
        assert data_size == 0

    def test_wav_length_proportional_to_note_count(self) -> None:
        short = _make_pc_lump(b"\x01" * 10)
        long_ = _make_pc_lump(b"\x01" * 20)
        wav_s = short.to_wav()
        wav_l = long_.to_wav()
        pcm_s = struct.unpack_from("<I", wav_s, 40)[0]
        pcm_l = struct.unpack_from("<I", wav_l, 40)[0]
        assert pcm_l > pcm_s

    def test_tone_index_one_frequency(self) -> None:
        """Index 1 maps to ~175 Hz; verify WAV encodes a plausible cycle count."""
        # 10 ticks * (11025/140) ~= 788 samples; at ~175 Hz, ~137 samples/cycle
        # expect at least a couple of transitions (not pure silence)
        snd = _make_pc_lump(bytes([1]) * 10)
        wav = snd.to_wav()
        data_offset = 44
        pcm = wav[data_offset:]
        transitions = sum(1 for a, b in itertools.pairwise(pcm) if a != b)
        assert transitions > 4  # well above 0 (silence) or 1 (constant)

    def test_pc_tones_table_length(self) -> None:
        assert len(_PC_TONES) == 128

    def test_pc_tones_index_zero_is_silence(self) -> None:
        assert _PC_TONES[0] == 0
