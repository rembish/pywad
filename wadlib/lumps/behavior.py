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

from .base import BaseLump

_ACS0_MAGIC = b"ACS\x00"
_ACSE_MAGIC = b"ACSE"
_ACSe_MAGIC = b"ACSe"


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
        raise ValueError(f"BEHAVIOR lump too short ({len(data)} bytes)")

    magic = data[:4]
    if magic == _ACS0_MAGIC:
        return _parse_acs0(data)
    if magic in (_ACSE_MAGIC, _ACSe_MAGIC):
        return _parse_acse(data, magic.decode("ascii"))
    raise ValueError(f"Unknown BEHAVIOR format: {magic!r}")


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
        return disassemble_acs(data, script.offset, self.parsed.strings)


# ---------------------------------------------------------------------------
# ACS opcode table (subset — covers the most common instructions)
# Reference: https://doomwiki.org/wiki/ACS_bytecode
# ---------------------------------------------------------------------------

# (name, number_of_immediate_args)
_ACS_OPCODES: dict[int, tuple[str, int]] = {
    0: ("NOP", 0),
    1: ("Terminate", 0),
    2: ("Suspend", 0),
    3: ("PushNumber", 1),
    4: ("LSpec1", 1),
    5: ("LSpec2", 1),
    6: ("LSpec3", 1),
    7: ("LSpec4", 1),
    8: ("LSpec5", 1),
    9: ("LSpec1Direct", 2),
    10: ("LSpec2Direct", 3),
    11: ("LSpec3Direct", 4),
    12: ("LSpec4Direct", 5),
    13: ("LSpec5Direct", 6),
    14: ("Add", 0),
    15: ("Subtract", 0),
    16: ("Multiply", 0),
    17: ("Divide", 0),
    18: ("Modulus", 0),
    19: ("EQ", 0),
    20: ("NE", 0),
    21: ("LT", 0),
    22: ("GT", 0),
    23: ("LE", 0),
    24: ("GE", 0),
    25: ("AssignScriptVar", 1),
    26: ("AssignMapVar", 1),
    27: ("AssignWorldVar", 1),
    28: ("PushScriptVar", 1),
    29: ("PushMapVar", 1),
    30: ("PushWorldVar", 1),
    31: ("AddScriptVar", 1),
    32: ("AddMapVar", 1),
    33: ("AddWorldVar", 1),
    34: ("SubScriptVar", 1),
    35: ("SubMapVar", 1),
    36: ("SubWorldVar", 1),
    37: ("MulScriptVar", 1),
    38: ("MulMapVar", 1),
    39: ("MulWorldVar", 1),
    40: ("DivScriptVar", 1),
    41: ("DivMapVar", 1),
    42: ("DivWorldVar", 1),
    43: ("ModScriptVar", 1),
    44: ("ModMapVar", 1),
    45: ("ModWorldVar", 1),
    46: ("IncScriptVar", 1),
    47: ("IncMapVar", 1),
    48: ("IncWorldVar", 1),
    49: ("DecScriptVar", 1),
    50: ("DecMapVar", 1),
    51: ("DecWorldVar", 1),
    52: ("Goto", 1),
    53: ("IfGoto", 1),
    54: ("Drop", 0),
    55: ("Delay", 0),
    56: ("DelayDirect", 1),
    57: ("Random", 0),
    58: ("RandomDirect", 2),
    59: ("ThingCount", 0),
    60: ("ThingCountDirect", 2),
    61: ("TagWait", 0),
    62: ("TagWaitDirect", 1),
    63: ("PolyWait", 0),
    64: ("PolyWaitDirect", 1),
    65: ("ChangeFloor", 0),
    66: ("ChangeFloorDirect", 1),
    67: ("ChangeCeiling", 0),
    68: ("ChangeCeilingDirect", 1),
    69: ("Restart", 0),
    70: ("AndLogical", 0),
    71: ("OrLogical", 0),
    72: ("AndBitwise", 0),
    73: ("OrBitwise", 0),
    74: ("EorBitwise", 0),
    75: ("NegateLogical", 0),
    76: ("LShift", 0),
    77: ("RShift", 0),
    78: ("UnaryMinus", 0),
    79: ("IfNotGoto", 1),
    80: ("LineSide", 0),
    81: ("ScriptWait", 0),
    82: ("ScriptWaitDirect", 1),
    83: ("ClearLineSpecial", 0),
    84: ("CaseGoto", 2),
    85: ("BeginPrint", 0),
    86: ("EndPrint", 0),
    87: ("PrintString", 0),
    88: ("PrintNumber", 0),
    89: ("PrintCharacter", 0),
    90: ("PlayerCount", 0),
    91: ("GameType", 0),
    92: ("GameSkill", 0),
    93: ("Timer", 0),
    94: ("SectorSound", 0),
    95: ("AmbientSound", 0),
    96: ("SoundSequence", 0),
    97: ("SetLineTexture", 0),
    98: ("SetLineBlocking", 0),
    99: ("SetLineSpecial", 0),
    100: ("ThingSound", 0),
    101: ("EndPrintBold", 0),
}


def disassemble_acs(
    data: bytes,
    start_offset: int,
    strings: list[str] | None = None,
    max_instructions: int = 200,
) -> str:
    """Disassemble ACS bytecode starting at *start_offset*.

    Returns human-readable assembly text. Stops at Terminate/Suspend
    or after *max_instructions*.
    """
    lines: list[str] = []
    pos = start_offset
    count = 0

    while pos + 4 <= len(data) and count < max_instructions:
        opcode = struct.unpack("<I", data[pos : pos + 4])[0]
        pos += 4
        count += 1

        if opcode in _ACS_OPCODES:
            name, argc = _ACS_OPCODES[opcode]
            args: list[str] = []
            for _ in range(argc):
                if pos + 4 > len(data):
                    break
                arg = struct.unpack("<i", data[pos : pos + 4])[0]
                pos += 4
                # Annotate string references for print instructions
                if name == "PushNumber" and strings and 0 <= arg < len(strings):
                    args.append(f"{arg}  ; {strings[arg]!r}")
                elif name in ("PrintString",) and strings:
                    args.append(str(arg))
                else:
                    args.append(str(arg))

            arg_str = ", ".join(args)
            lines.append(f"  {name}{f'  {arg_str}' if arg_str else ''}")
        else:
            lines.append(f"  ??? opcode {opcode}")

        # Stop at terminator instructions
        if opcode in (1, 2):  # Terminate, Suspend
            break

    return "\n".join(lines)
