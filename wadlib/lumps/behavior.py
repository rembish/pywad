"""ACS BEHAVIOR lump parser — compiled script bytecode for Hexen/ZDoom maps.

The BEHAVIOR lump contains compiled ACS (Action Code Script) bytecode.
This parser extracts the script directory and string table without
executing the bytecode.

Supported formats:
- ACS0: Original Hexen format (4-byte magic "ACS\\0")
- ACSE: ZDoom enhanced format (4-byte magic "ACSE")
- ACSe: ZDoom enhanced little-endian (4-byte magic "ACSe")

Reference: https://doomwiki.org/wiki/Behavior

Usage::

    from wadlib.lumps.behavior import parse_behavior

    with open("BEHAVIOR.lmp", "rb") as f:
        info = parse_behavior(f.read())
    print(f"{len(info.scripts)} scripts, {len(info.strings)} strings")
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from ..exceptions import CorruptLumpError
from .base import BaseLump

_ACS0_MAGIC = b"ACS\x00"
_ACSE_MAGIC = b"ACSE"
_ACSE_LOWER_MAGIC = b"ACSe"


@dataclass
class AcsScript:
    """A single ACS script entry from the directory."""

    number: int
    script_type: int  # 0=closed, 1=open, 2=respawn, 3=death, 4=enter, 5=lightning
    arg_count: int
    offset: int  # bytecode offset in the lump

    @property
    def type_name(self) -> str:
        names = {0: "closed", 1: "open", 2: "respawn", 3: "death", 4: "enter", 5: "lightning"}
        return names.get(self.script_type, f"unknown({self.script_type})")


@dataclass
class BehaviorInfo:
    """Parsed BEHAVIOR lump metadata."""

    format: str  # "ACS0", "ACSE", or "ACSe"
    scripts: list[AcsScript] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)
    bytecode_size: int = 0


def parse_behavior(data: bytes) -> BehaviorInfo:
    """Parse a BEHAVIOR lump and extract script directory + strings."""
    if len(data) < 8:
        raise CorruptLumpError(f"BEHAVIOR lump too short ({len(data)} bytes)")

    magic = data[:4]
    if magic == _ACS0_MAGIC:
        return _parse_acs0(data)
    if magic in (_ACSE_MAGIC, _ACSE_LOWER_MAGIC):
        return _parse_acse(data, magic.decode("ascii"))
    raise CorruptLumpError(f"Unknown BEHAVIOR format: {magic!r}")


def _parse_acs0(data: bytes) -> BehaviorInfo:
    """Parse original Hexen ACS0 format."""
    info = BehaviorInfo(format="ACS0", bytecode_size=len(data))

    # Directory offset is at byte 4
    dir_offset = struct.unpack("<I", data[4:8])[0]
    if dir_offset >= len(data):
        return info

    # Script count
    pos = dir_offset
    if pos + 4 > len(data):
        return info
    (script_count,) = struct.unpack("<I", data[pos : pos + 4])
    pos += 4

    # Script entries: 12 bytes each (number, offset, arg_count)
    for _ in range(script_count):
        if pos + 12 > len(data):
            break
        number, offset, arg_count = struct.unpack("<IIi", data[pos : pos + 12])
        # Script type is encoded in the number: number >= 1000 means "open"
        script_type = 0
        real_number = number
        if number >= 1000:
            script_type = 1  # open
            real_number = number - 1000
        info.scripts.append(AcsScript(real_number, script_type, arg_count, offset))
        pos += 12

    # String table follows the script directory
    if pos + 4 <= len(data):
        (string_count,) = struct.unpack("<I", data[pos : pos + 4])
        pos += 4
        for _ in range(string_count):
            if pos + 4 > len(data):
                break
            (str_offset,) = struct.unpack("<I", data[pos : pos + 4])
            pos += 4
            if str_offset < len(data):
                end = data.index(0, str_offset) if 0 in data[str_offset:] else len(data)
                info.strings.append(data[str_offset:end].decode("latin-1"))

    return info


def _parse_acse(data: bytes, fmt: str) -> BehaviorInfo:
    """Parse ZDoom ACSE/ACSe enhanced format."""
    info = BehaviorInfo(format=fmt, bytecode_size=len(data))

    # Directory offset at byte 4
    dir_offset = struct.unpack("<I", data[4:8])[0]
    if dir_offset >= len(data):
        return info

    # ACSE directory is a series of chunks
    pos = dir_offset
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        chunk_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        chunk_data = data[pos + 8 : pos + 8 + chunk_size]
        pos += 8 + chunk_size

        if chunk_id == b"SPTR":
            # Script pointer table: 8 bytes per entry (number:2, type:1, argcount:1, offset:4)
            for j in range(0, len(chunk_data) - 7, 8):
                number, stype, argc, offset = struct.unpack("<HBBi", chunk_data[j : j + 8])
                info.scripts.append(AcsScript(number, stype, argc, offset))

        elif chunk_id == b"STRL" and len(chunk_data) >= 12:
            _flags, count, _first = struct.unpack("<III", chunk_data[:12])
            str_offsets_start = 12
            for j in range(count):
                off_pos = str_offsets_start + j * 4
                if off_pos + 4 > len(chunk_data):
                    break
                (str_off,) = struct.unpack("<I", chunk_data[off_pos : off_pos + 4])
                if str_off < len(chunk_data):
                    end = (
                        chunk_data.index(0, str_off)
                        if 0 in chunk_data[str_off:]
                        else len(chunk_data)
                    )
                    info.strings.append(chunk_data[str_off:end].decode("latin-1"))

    return info


class BehaviorLump(BaseLump[Any]):
    """A BEHAVIOR lump containing compiled ACS scripts."""

    @cached_property
    def parsed(self) -> BehaviorInfo:
        return parse_behavior(self.raw())

    @property
    def scripts(self) -> list[AcsScript]:
        return self.parsed.scripts

    @property
    def strings(self) -> list[str]:
        return self.parsed.strings

    @property
    def format(self) -> str:
        return self.parsed.format

    def disassemble(self, script_index: int = 0) -> str:
        """Disassemble a script to human-readable p-code.

        Returns a multi-line string showing each instruction.
        """
        if script_index >= len(self.scripts):
            raise IndexError(f"Script index {script_index} out of range")
        script = self.scripts[script_index]
        data = self.raw()
        from .acs import disassemble_acs  # lazy import to avoid circular dependency

        return disassemble_acs(data, script.offset, self.parsed.strings)
