"""ACS assembler and disassembler for Hexen/ZDoom BEHAVIOR lumps.

Provides human-readable disassembly of compiled ACS bytecode and
round-trip assembly back to raw bytes.  The BEHAVIOR lump parser lives
in :mod:`wadlib.lumps.behavior`; this module only handles the opcode
encoding layer.

Usage::

    from wadlib.lumps.acs import assemble_acs, build_behavior, disassemble_acs

    code = assemble_acs('''
        BeginPrint
        PushNumber 0
        PrintString
        EndPrint
        Terminate
    ''')
    behavior = build_behavior(
        scripts=[(1, 1, 0, code)],  # script 1, open, 0 args
        strings=["Hello World"],
    )
"""

from __future__ import annotations

import struct

# ---------------------------------------------------------------------------
# ACS opcode table (subset -- covers the most common instructions)
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

# Reverse lookup: name -> (opcode, argc)
_ACS_NAME_TO_OPCODE: dict[str, tuple[int, int]] = {
    name.lower(): (opcode, argc) for opcode, (name, argc) in _ACS_OPCODES.items()
}

# ACS0 magic used when building BEHAVIOR lumps
_ACS0_MAGIC = b"ACS\x00"


def disassemble_acs(
    data: bytes,
    start_offset: int,
    strings: list[str] | None = None,
    max_instructions: int = 200,
) -> str:
    """Disassemble ACS bytecode starting at *start_offset*.

    Returns human-readable assembly text.  Stops at Terminate/Suspend
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


def assemble_acs(text: str) -> bytes:
    """Assemble ACS p-code text into raw bytecode.

    Accepts the same format produced by :func:`disassemble_acs`::

        bytecode = assemble_acs('''
            BeginPrint
            PushNumber 0
            PrintString
            EndPrint
            Terminate
        ''')

    Lines starting with ``#`` or ``;`` are comments.  Arguments after
    ``;`` on instruction lines are stripped (inline comments).
    """
    result = bytearray()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        # Strip inline comments (after ;)
        if ";" in line:
            line = line[: line.index(";")].strip()
        if not line:
            continue

        parts = line.split()
        mnemonic = parts[0].lower()

        if mnemonic not in _ACS_NAME_TO_OPCODE:
            raise ValueError(f"Unknown ACS instruction: {parts[0]!r}")

        opcode, _argc = _ACS_NAME_TO_OPCODE[mnemonic]
        result += struct.pack("<I", opcode)

        # Parse arguments
        arg_parts = parts[1:] if len(parts) > 1 else []
        # Handle comma-separated args
        arg_strs = []
        for p in arg_parts:
            arg_strs.extend(p.rstrip(",").split(","))
        arg_strs = [a.strip() for a in arg_strs if a.strip()]

        for arg_str in arg_strs:
            result += struct.pack("<i", int(arg_str))

    return bytes(result)


def build_behavior(
    scripts: list[tuple[int, int, int, bytes]],
    strings: list[str] | None = None,
) -> bytes:
    """Build a complete ACS0 BEHAVIOR lump from scripts and strings.

    Parameters:
        scripts:  List of ``(number, script_type, arg_count, bytecode)`` tuples.
                  script_type: 0=closed, 1=open, 2=respawn, etc.
        strings:  Optional list of strings for the string table.

    Returns:
        Raw bytes for a BEHAVIOR lump ready to embed in a WAD.

    Example::

        from wadlib.lumps.acs import assemble_acs, build_behavior

        code = assemble_acs('''
            BeginPrint
            PushNumber 0
            PrintString
            EndPrint
            Terminate
        ''')
        behavior = build_behavior(
            scripts=[(1, 1, 0, code)],  # script 1, open, 0 args
            strings=["Hello World"],
        )
    """
    strings = strings or []

    # Layout: magic(4) + dir_offset(4) + bytecode... + directory + strings
    header_size = 8  # magic + dir_offset

    # Accumulate bytecode and record offsets
    bytecode_blob = bytearray()
    script_entries: list[tuple[int, int, int]] = []  # (number, offset, arg_count)

    for number, stype, argc, code in scripts:
        offset = header_size + len(bytecode_blob)
        # Encode script type in number (ACS0 convention: open = number + 1000)
        encoded_number = number + 1000 if stype == 1 else number
        script_entries.append((encoded_number, offset, argc))
        bytecode_blob += code

    dir_offset = header_size + len(bytecode_blob)

    # Build directory
    dir_data = struct.pack("<I", len(script_entries))
    for num, off, argc in script_entries:
        dir_data += struct.pack("<IIi", num, off, argc)

    # Build string table
    str_count = len(strings)
    str_data = struct.pack("<I", str_count)

    # String offsets are relative to the start of the lump
    # First compute where string data starts
    str_table_start = dir_offset + len(dir_data) + 4 + str_count * 4  # after count + offsets
    encoded_strings = [s.encode("latin-1") + b"\x00" for s in strings]

    str_offset = str_table_start
    for es in encoded_strings:
        str_data += struct.pack("<I", str_offset)
        str_offset += len(es)

    str_data += b"".join(encoded_strings)

    # Assemble
    header = _ACS0_MAGIC + struct.pack("<I", dir_offset)
    return header + bytes(bytecode_blob) + dir_data + str_data
