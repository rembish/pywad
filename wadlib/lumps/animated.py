"""ANIMATED and SWITCHES binary lumps (Boom format).

ANIMATED defines flat and texture animation cycles as fixed-size records.
SWITCHES defines wall switch textures (on/off pairs).

These are the binary equivalents of the text-based ANIMDEFS lump used by
Hexen and ZDoom.

ANIMATED binary layout (each record is 23 bytes):
  [1]  type      (0 = flat, 1 = texture, 0xFF = end of list)
  [9]  last      (null-padded ASCII — last frame name)
  [9]  first     (null-padded ASCII — first frame name)
  [4]  speed     (uint32 LE — tics between frames)

SWITCHES binary layout (each record is 20 bytes):
  [9]  off_name  (null-padded ASCII — switch off texture)
  [9]  on_name   (null-padded ASCII — switch on texture)
  [2]  episode   (uint16 LE — 0 = end, 1 = shareware, 2 = registered, 3 = commercial)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal

from .base import BaseLump

_ANIM_RECORD_SIZE = 23
_ANIM_FMT = "<B9s9sI"
_SWITCH_RECORD_SIZE = 20
_SWITCH_FMT = "<9s9sH"

_ANIM_END = 0xFF


def _decode_name(raw: bytes) -> str:
    return raw.rstrip(b"\x00").decode("ascii", errors="replace")


def _encode_name9(name: str) -> bytes:
    return name.encode("ascii")[:9].ljust(9, b"\x00")


@dataclass
class AnimatedEntry:
    """A single ANIMATED record — a flat or texture animation cycle."""

    kind: Literal["flat", "texture"]
    first: str
    last: str
    speed: int

    def to_bytes(self) -> bytes:
        type_byte = 0 if self.kind == "flat" else 1
        return struct.pack(
            _ANIM_FMT, type_byte, _encode_name9(self.last), _encode_name9(self.first), self.speed
        )


@dataclass
class SwitchEntry:
    """A single SWITCHES record — an on/off texture pair."""

    off_name: str
    on_name: str
    episode: int

    def to_bytes(self) -> bytes:
        return struct.pack(
            _SWITCH_FMT, _encode_name9(self.off_name), _encode_name9(self.on_name), self.episode
        )


class AnimatedLump(BaseLump[Any]):
    """Boom ANIMATED lump — binary flat/texture animation definitions."""

    @cached_property
    def entries(self) -> list[AnimatedEntry]:
        data = self.raw()
        result: list[AnimatedEntry] = []
        pos = 0
        while pos + _ANIM_RECORD_SIZE <= len(data):
            type_byte, last_raw, first_raw, speed = struct.unpack(
                _ANIM_FMT, data[pos : pos + _ANIM_RECORD_SIZE]
            )
            if type_byte == _ANIM_END:
                break
            kind: Literal["flat", "texture"] = "flat" if type_byte == 0 else "texture"
            result.append(
                AnimatedEntry(kind, _decode_name(first_raw), _decode_name(last_raw), speed)
            )
            pos += _ANIM_RECORD_SIZE
        return result

    @property
    def flats(self) -> list[AnimatedEntry]:
        return [e for e in self.entries if e.kind == "flat"]

    @property
    def textures(self) -> list[AnimatedEntry]:
        return [e for e in self.entries if e.kind == "texture"]


class SwitchesLump(BaseLump[Any]):
    """Boom SWITCHES lump — binary wall switch texture pairs."""

    @cached_property
    def entries(self) -> list[SwitchEntry]:
        data = self.raw()
        result: list[SwitchEntry] = []
        pos = 0
        while pos + _SWITCH_RECORD_SIZE <= len(data):
            off_raw, on_raw, episode = struct.unpack(
                _SWITCH_FMT, data[pos : pos + _SWITCH_RECORD_SIZE]
            )
            if episode == 0:
                break
            result.append(SwitchEntry(_decode_name(off_raw), _decode_name(on_raw), episode))
            pos += _SWITCH_RECORD_SIZE
        return result


def animated_to_bytes(entries: list[AnimatedEntry]) -> bytes:
    """Serialize a list of AnimatedEntry to an ANIMATED lump."""
    data = b"".join(e.to_bytes() for e in entries)
    # Terminator record
    data += struct.pack(_ANIM_FMT, _ANIM_END, b"\x00" * 9, b"\x00" * 9, 0)
    return data


def switches_to_bytes(entries: list[SwitchEntry]) -> bytes:
    """Serialize a list of SwitchEntry to a SWITCHES lump."""
    data = b"".join(e.to_bytes() for e in entries)
    # Terminator record (episode = 0)
    data += struct.pack(_SWITCH_FMT, b"\x00" * 9, b"\x00" * 9, 0)
    return data
