"""MUS lump — Doom's compact music format, with conversion to Standard MIDI File.

MUS is a reduced MIDI variant invented by id Software.  Key differences:
  - Channels 0-14 map to MIDI 0-15; MUS channel 15 (percussion) → MIDI 9.
  - Events are packed in a tighter binary encoding (no running status).
  - Timing is in ticks; one MUS tick = one MIDI tick when the tempo is tuned
    to Doom's default 140 BPM with 70 ticks-per-quarter-note.

References:
  The unofficial MUS specification at <https://www.doomworld.com/docs/mus.txt>
  and the mus2mid reference implementations.
"""

from __future__ import annotations

import struct
from typing import Any, ClassVar

from ..exceptions import CorruptLumpError
from .base import BaseLump

# ---------------------------------------------------------------------------
# MUS header
# ---------------------------------------------------------------------------
_MUS_MAGIC = b"MUS\x1a"
_HEADER_FMT = "<4sHHHHHH"  # magic + 6 uint16 fields
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)

# ---------------------------------------------------------------------------
# MUS → MIDI channel mapping
# ---------------------------------------------------------------------------
# MUS percussion channel (15) → MIDI percussion channel (9).
# Channels 9-14 in MUS shift up by one to skip MIDI's channel 9.
_MUS_TO_MIDI_CHAN: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 9]

# ---------------------------------------------------------------------------
# MUS controller → MIDI mapping
# ---------------------------------------------------------------------------
# MUS change-controller (event type 4) ctrl values:
_CTRL_MIDI: dict[int, int] = {
    1: 0,  # bank select
    2: 1,  # modulation
    3: 7,  # volume
    4: 10,  # pan
    5: 11,  # expression
    6: 91,  # reverb depth
    7: 93,  # chorus depth
    8: 64,  # sustain pedal
    9: 67,  # soft pedal
}
# MUS system-event (type 3) controller values → MIDI CC:
_SYS_MIDI: dict[int, int] = {
    10: 120,  # all sounds off
    11: 121,  # reset all controllers
    14: 123,  # all notes off
}

# ---------------------------------------------------------------------------
# MIDI SMF constants
# ---------------------------------------------------------------------------
_TICKS_PER_QN: int = 70
# 140 BPM → microseconds per quarter note
_TEMPO_US: int = 428571


def _vlq(n: int) -> bytes:
    """Encode *n* as a MIDI variable-length quantity."""
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


class Mus(BaseLump[Any]):
    """MUS music lump."""

    _CHAN_COUNT: ClassVar[int] = 16

    # ------------------------------------------------------------------
    # MIDI conversion
    # ------------------------------------------------------------------

    def to_midi(self) -> bytes:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Convert this MUS lump to a Standard MIDI File (SMF type-0) byte string."""
        data = self.raw()
        if len(data) < _HEADER_SIZE:
            raise CorruptLumpError(f"{self.name!r}: MUS lump too short ({len(data)} bytes)")
        if data[:4] != _MUS_MAGIC:
            raise CorruptLumpError(f"{self.name!r}: bad MUS magic {data[:4]!r}")

        _, score_len, score_start, _, _, _num_instruments, _ = struct.unpack_from(_HEADER_FMT, data)
        pos = score_start

        # Per-channel last-used volume (default 127).
        vol: list[int] = [127] * self._CHAN_COUNT
        # Per-channel last patch (program).
        patch: list[int] = [0] * self._CHAN_COUNT

        # MIDI events collected as (abs_tick, bytes).
        events: list[tuple[int, bytes]] = []
        current_tick: int = 0

        # Tempo event at tick 0.
        tempo_bytes = struct.pack(">I", _TEMPO_US)[1:]  # 3 bytes big-endian
        events.append((0, b"\xff\x51\x03" + tempo_bytes))

        end = score_start + score_len
        try:
            while pos < end:
                descriptor = data[pos]
                pos += 1
                last = bool(descriptor & 0x80)
                etype = (descriptor >> 4) & 0x07
                mus_ch = descriptor & 0x0F
                midi_ch = _MUS_TO_MIDI_CHAN[mus_ch]

                if etype == 0:  # release note
                    note = data[pos] & 0x7F
                    pos += 1
                    events.append((current_tick, bytes([0x80 | midi_ch, note, 0])))

                elif etype == 1:  # play note
                    note_byte = data[pos]
                    pos += 1
                    note = note_byte & 0x7F
                    if note_byte & 0x80:
                        vol[mus_ch] = data[pos] & 0x7F
                        pos += 1
                    events.append((current_tick, bytes([0x90 | midi_ch, note, vol[mus_ch]])))

                elif etype == 2:  # pitch wheel
                    raw = data[pos]
                    pos += 1
                    # Map 0-255 to MIDI 0-16383 centred at 8192.
                    bend = raw * 64
                    lsb = bend & 0x7F
                    msb = (bend >> 7) & 0x7F
                    events.append((current_tick, bytes([0xE0 | midi_ch, lsb, msb])))

                elif etype == 3:  # system event
                    ctrl = data[pos]
                    pos += 1
                    if ctrl in _SYS_MIDI:
                        events.append((current_tick, bytes([0xB0 | midi_ch, _SYS_MIDI[ctrl], 0])))

                elif etype == 4:  # change controller
                    ctrl = data[pos]
                    pos += 1
                    value = data[pos] & 0x7F
                    pos += 1
                    if ctrl == 0:  # program change
                        patch[mus_ch] = value
                        events.append((current_tick, bytes([0xC0 | midi_ch, value])))
                    elif ctrl in _CTRL_MIDI:
                        events.append(
                            (current_tick, bytes([0xB0 | midi_ch, _CTRL_MIDI[ctrl], value]))
                        )

                elif etype == 6:  # score end
                    break

                if last:
                    delta = 0
                    while True:
                        b = data[pos]
                        pos += 1
                        delta = delta * 128 + (b & 0x7F)
                        if not b & 0x80:
                            break
                    current_tick += delta
        except IndexError as exc:
            raise CorruptLumpError(f"{self.name!r}: truncated MUS event stream") from exc

        # End-of-track meta event.
        events.append((current_tick, b"\xff\x2f\x00"))

        # Build track data: convert absolute ticks → delta-time VLQ.
        track_bytes = bytearray()
        prev_tick = 0
        for abs_tick, ev_bytes in events:
            track_bytes += _vlq(abs_tick - prev_tick)
            track_bytes += ev_bytes
            prev_tick = abs_tick

        # Assemble SMF.
        header = struct.pack(
            ">4sIHHH",
            b"MThd",
            6,
            0,  # format 0 (single track)
            1,  # 1 track
            _TICKS_PER_QN,
        )
        track = struct.pack(">4sI", b"MTrk", len(track_bytes)) + bytes(track_bytes)
        return header + track
