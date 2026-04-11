"""MIDI → MUS converter — encode a Standard MIDI File into Doom's MUS format.

MUS is a compact MIDI subset used by Doom.  The conversion follows the
same channel-mapping and controller tables as the MUS → MIDI path in
``mus.py``, but in reverse.

Limitations (matching what the Doom engine supports):
  - Max 16 channels (MUS channels 0-14 melodic + 15 percussion).
  - Only MIDI channel events are converted (note on/off, program change,
    controller change, pitch bend).  Meta events (tempo, text, etc.) are
    ignored — MUS has no equivalent.
  - MIDI format 0 and 1 are supported; format 2 is not.

Usage::

    from wadlib.lumps.mid2mus import midi_to_mus

    with open("D_E1M1.mid", "rb") as f:
        mus_bytes = midi_to_mus(f.read())
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# MIDI → MUS channel mapping (reverse of mus.py's _MUS_TO_MIDI_CHAN)
# ---------------------------------------------------------------------------
# _MUS_TO_MIDI_CHAN = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 9]
# Invert: MIDI channel → MUS channel
_MIDI_TO_MUS_CHAN: list[int] = [0] * 16
_MIDI_TO_MUS_CHAN[0] = 0
_MIDI_TO_MUS_CHAN[1] = 1
_MIDI_TO_MUS_CHAN[2] = 2
_MIDI_TO_MUS_CHAN[3] = 3
_MIDI_TO_MUS_CHAN[4] = 4
_MIDI_TO_MUS_CHAN[5] = 5
_MIDI_TO_MUS_CHAN[6] = 6
_MIDI_TO_MUS_CHAN[7] = 7
_MIDI_TO_MUS_CHAN[8] = 8
_MIDI_TO_MUS_CHAN[9] = 15  # MIDI percussion → MUS 15
_MIDI_TO_MUS_CHAN[10] = 9
_MIDI_TO_MUS_CHAN[11] = 10
_MIDI_TO_MUS_CHAN[12] = 11
_MIDI_TO_MUS_CHAN[13] = 12
_MIDI_TO_MUS_CHAN[14] = 13
_MIDI_TO_MUS_CHAN[15] = 14

# MIDI CC → MUS controller (reverse of mus.py's _CTRL_MIDI)
_MIDI_CC_TO_MUS: dict[int, int] = {
    0: 1,  # bank select
    1: 2,  # modulation
    7: 3,  # volume
    10: 4,  # pan
    11: 5,  # expression
    91: 6,  # reverb
    93: 7,  # chorus
    64: 8,  # sustain pedal
    67: 9,  # soft pedal
}

# MIDI CC → MUS system event (reverse of mus.py's _SYS_MIDI)
_MIDI_CC_TO_SYS: dict[int, int] = {
    120: 10,  # all sounds off
    121: 11,  # reset all controllers
    123: 14,  # all notes off
}

_MUS_MAGIC = b"MUS\x1a"


# ---------------------------------------------------------------------------
# MIDI parser (minimal, just enough for conversion)
# ---------------------------------------------------------------------------


def _read_vlq(data: bytes, pos: int) -> tuple[int, int]:
    """Read a MIDI variable-length quantity. Returns (value, new_pos)."""
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return value, pos


@dataclass
class MidiEvent:
    """A parsed MIDI channel event with an absolute tick timestamp."""

    tick: int
    status: int  # full status byte (type | channel)
    data: bytes  # event-specific data (1-2 bytes)


def _parse_track(data: bytes, offset: int) -> tuple[list[MidiEvent], int]:
    """Parse a single MTrk chunk. Returns (events, end_offset)."""
    if data[offset : offset + 4] != b"MTrk":
        raise ValueError(f"Expected MTrk at offset {offset}")
    track_len = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
    pos = offset + 8
    end = pos + track_len

    events: list[MidiEvent] = []
    abs_tick = 0
    running_status = 0

    while pos < end:
        delta, pos = _read_vlq(data, pos)
        abs_tick += delta

        status = data[pos]
        if status & 0x80:
            pos += 1
            if status < 0xF0:
                running_status = status
        else:
            # Running status — reuse previous status byte
            status = running_status

        etype = status & 0xF0

        if etype in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
            # Two data bytes
            d1 = data[pos]
            d2 = data[pos + 1]
            pos += 2
            events.append(MidiEvent(abs_tick, status, bytes([d1, d2])))

        elif etype in (0xC0, 0xD0):
            # One data byte
            d1 = data[pos]
            pos += 1
            events.append(MidiEvent(abs_tick, status, bytes([d1])))

        elif status == 0xFF:
            # Meta event: type + length + data
            meta_type = data[pos]
            pos += 1
            length, pos = _read_vlq(data, pos)
            pos += length  # skip meta data
            if meta_type == 0x2F:  # end of track
                break

        elif status in (0xF0, 0xF7):
            # SysEx — skip
            length, pos = _read_vlq(data, pos)
            pos += length

    return events, offset + 8 + track_len


def _parse_midi(data: bytes) -> list[MidiEvent]:
    """Parse an SMF file and return a merged, time-sorted event list."""
    if data[:4] != b"MThd":
        raise ValueError("Not a MIDI file (missing MThd header)")

    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, num_tracks, _tpqn = struct.unpack(">HHH", data[8:14])

    if fmt > 1:
        raise ValueError(f"MIDI format {fmt} is not supported (only 0 and 1)")

    pos = 8 + header_len
    all_events: list[MidiEvent] = []

    for _ in range(num_tracks):
        track_events, pos = _parse_track(data, pos)
        all_events.extend(track_events)

    # Sort by tick (stable sort preserves order within same tick)
    all_events.sort(key=lambda e: e.tick)
    return all_events


# ---------------------------------------------------------------------------
# MUS encoder
# ---------------------------------------------------------------------------


def _encode_mus_delay(ticks: int) -> bytes:
    """Encode a MUS delay as a variable-length quantity (same encoding as MIDI VLQ)."""
    if ticks == 0:
        return b""
    buf: list[int] = []
    while ticks:
        buf.append(ticks & 0x7F)
        ticks >>= 7
    buf.reverse()
    for i in range(len(buf) - 1):
        buf[i] |= 0x80
    return bytes(buf)


def midi_to_mus(midi_data: bytes) -> bytes:
    """Convert a Standard MIDI File to Doom MUS format.

    Accepts raw MIDI bytes (SMF format 0 or 1) and returns raw MUS bytes
    suitable for embedding in a WAD file.
    """
    events = _parse_midi(midi_data)

    # Track which channels and instruments are used
    channels_used: set[int] = set()
    instruments_used: set[int] = set()
    # Per-channel state for volume tracking
    last_vol: dict[int, int] = {}

    mus_events: list[bytes] = []
    prev_tick = 0

    for ev in events:
        etype = ev.status & 0xF0
        midi_ch = ev.status & 0x0F
        mus_ch = _MIDI_TO_MUS_CHAN[midi_ch]
        channels_used.add(mus_ch)

        delay = ev.tick - prev_tick
        prev_tick = ev.tick

        # If there's a delay, attach it to the PREVIOUS event
        if delay > 0 and mus_events:
            # Set the "last" bit on the previous event's descriptor
            last_ev = bytearray(mus_events[-1])
            last_ev[0] |= 0x80
            mus_events[-1] = bytes(last_ev) + _encode_mus_delay(delay)

        if etype == 0x80:  # Note Off
            note = ev.data[0] & 0x7F
            descriptor = (0 << 4) | mus_ch
            mus_events.append(bytes([descriptor, note]))

        elif etype == 0x90:  # Note On
            note = ev.data[0] & 0x7F
            velocity = ev.data[1] & 0x7F
            if velocity == 0:
                # Note on with velocity 0 = note off
                descriptor = (0 << 4) | mus_ch
                mus_events.append(bytes([descriptor, note]))
            else:
                descriptor = (1 << 4) | mus_ch
                if last_vol.get(mus_ch) != velocity:
                    # Include volume byte
                    last_vol[mus_ch] = velocity
                    mus_events.append(bytes([descriptor, note | 0x80, velocity]))
                else:
                    mus_events.append(bytes([descriptor, note]))

        elif etype == 0xE0:  # Pitch Bend
            lsb = ev.data[0]
            msb = ev.data[1]
            bend14 = (msb << 7) | lsb
            # Map 14-bit MIDI bend (0-16383) to 8-bit MUS bend (0-255)
            mus_bend = min(255, bend14 // 64)
            descriptor = (2 << 4) | mus_ch
            mus_events.append(bytes([descriptor, mus_bend]))

        elif etype == 0xC0:  # Program Change
            program = ev.data[0] & 0x7F
            instruments_used.add(program)
            descriptor = (4 << 4) | mus_ch
            mus_events.append(bytes([descriptor, 0, program]))  # ctrl=0 = program change

        elif etype == 0xB0:  # Control Change
            cc = ev.data[0]
            value = ev.data[1] & 0x7F
            if cc in _MIDI_CC_TO_SYS:
                # System event
                descriptor = (3 << 4) | mus_ch
                mus_events.append(bytes([descriptor, _MIDI_CC_TO_SYS[cc]]))
            elif cc in _MIDI_CC_TO_MUS:
                descriptor = (4 << 4) | mus_ch
                mus_events.append(bytes([descriptor, _MIDI_CC_TO_MUS[cc], value]))
            # else: unsupported CC, skip silently

    # Score end event
    mus_events.append(bytes([(6 << 4)]))

    # Concatenate score data
    score_data = b"".join(mus_events)

    # Build instrument list (sorted unique program numbers)
    instr_list = sorted(instruments_used)

    # Header
    num_channels = len(channels_used)
    primary_channels = min(num_channels, 9)
    secondary_channels = max(0, num_channels - 9)
    # score_start = header (16 bytes) + instrument list (2 bytes each)
    instr_bytes = struct.pack(f"<{len(instr_list)}H", *instr_list) if instr_list else b""
    score_start = _header_size() + len(instr_bytes)

    header = struct.pack(
        "<4sHHHHHH",
        _MUS_MAGIC,
        len(score_data),  # score_len
        score_start,  # score_start
        primary_channels,
        secondary_channels,
        len(instr_list),  # num_instruments
        0,  # padding
    )

    return header + instr_bytes + score_data


def _header_size() -> int:
    """Return the fixed MUS header size in bytes."""
    return struct.calcsize("<4sHHHHHH")
