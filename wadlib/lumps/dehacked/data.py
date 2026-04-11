"""Stock Doom data tables for DEHACKED cross-referencing.

Contains:
- Sprite name table (from info.c sprnames[])
- Stock state-to-sprite mapping (abbreviated)
- BEX flag name mappings
- Mobj flag constants
"""

from __future__ import annotations

import re

# Doom mobj flag bit values
MF_COUNTKILL: int = 0x00400000
MF_COUNTITEM: int = 0x00800000

# BEX text -> numeric bit mapping
BEX_BITS: dict[str, int] = {
    "SPECIAL": 0x00000001,
    "SOLID": 0x00000002,
    "SHOOTABLE": 0x00000004,
    "NOSECTOR": 0x00000008,
    "NOBLOCKMAP": 0x00000010,
    "AMBUSH": 0x00000020,
    "JUSTHIT": 0x00000040,
    "JUSTATTACKED": 0x00000080,
    "SPAWNCEILING": 0x00000100,
    "NOGRAVITY": 0x00000200,
    "DROPOFF": 0x00000400,
    "PICKUP": 0x00000800,
    "NOCLIP": 0x00001000,
    "SLIDE": 0x00002000,
    "FLOAT": 0x00004000,
    "TELEPORT": 0x00008000,
    "MISSILE": 0x00010000,
    "DROPPED": 0x00020000,
    "SHADOW": 0x00040000,
    "NOBLOOD": 0x00080000,
    "CORPSE": 0x00100000,
    "INFLOAT": 0x00200000,
    "COUNTKILL": MF_COUNTKILL,
    "COUNTITEM": MF_COUNTITEM,
    "SKULLFLY": 0x01000000,
    "NOTDMATCH": 0x02000000,
    # MBF extensions
    "TRANSLUCENT": 0x04000000,
    "TOUCHY": 0x10000000,
    "BOUNCES": 0x20000000,
    "FRIEND": 0x40000000,
    "FRIENDLY": 0x40000000,
}

# Stock Doom sprite names (index -> 4-char prefix)
# From info.c sprnames[] — 138 entries for Doom 2 v1.9
STOCK_SPRITE_NAMES: list[str] = [
    "TROO",
    "SHTG",
    "PUNG",
    "PISG",
    "PISF",
    "SHTF",
    "SHT2",
    "CHGG",
    "CHGF",
    "MISG",
    "MISF",
    "SAWG",
    "PLSG",
    "PLSF",
    "BFGG",
    "BFGF",
    "BLUD",
    "PUFF",
    "BAL1",
    "BAL2",
    "PLSS",
    "PLSE",
    "MISL",
    "BFS1",
    "BFE1",
    "BFE2",
    "TFOG",
    "IFOG",
    "PLAY",
    "POSS",
    "SPOS",
    "VILE",
    "FIRE",
    "FATB",
    "FBXP",
    "SKEL",
    "MANF",
    "FATT",
    "CPOS",
    "SARG",
    "HEAD",
    "BAL7",
    "BOSS",
    "BOS2",
    "SKUL",
    "SPID",
    "BSPI",
    "APLS",
    "APBX",
    "CYBR",
    "PAIN",
    "SSWV",
    "KEEN",
    "BBRN",
    "BOSF",
    "ARM1",
    "ARM2",
    "BAR1",
    "BEXP",
    "FCAN",
    "BON1",
    "BON2",
    "BKEY",
    "RKEY",
    "YKEY",
    "BSKU",
    "RSKU",
    "YSKU",
    "STIM",
    "MEDI",
    "SOUL",
    "PINV",
    "PSTR",
    "PINS",
    "MEGA",
    "SUIT",
    "PMAP",
    "PVIS",
    "CLIP",
    "AMMO",
    "ROCK",
    "BROK",
    "CELL",
    "CELP",
    "SHEL",
    "SBOX",
    "BPAK",
    "BFUG",
    "MGUN",
    "CSAW",
    "LAUN",
    "PLAS",
    "SHOT",
    "SGN2",
    "COLU",
    "SMT2",
    "GOR1",
    "POL2",
    "POL5",
    "POL4",
    "POL3",
    "POL1",
    "POL6",
    "GOR2",
    "GOR3",
    "GOR4",
    "GOR5",
    "SMIT",
    "COL1",
    "COL2",
    "COL3",
    "COL4",
    "CAND",
    "CBRA",
    "COL6",
    "TRE1",
    "TRE2",
    "ELEC",
    "CEYE",
    "FSKU",
    "COL5",
    "TBLU",
    "TGRN",
    "TRED",
    "SMBT",
    "SMGT",
    "SMRT",
    "HDB1",
    "HDB2",
    "HDB3",
    "HDB4",
    "HDB5",
    "HDB6",
    "POB1",
    "POB2",
    "BRS1",
    "TLMP",
    "TLP2",
]

# Stock state -> sprite index (abbreviated subset for common things)
STOCK_STATE_SPRITES: dict[int, int] = {
    174: 28,
    175: 28,
    176: 28,
    177: 28,  # Player
    206: 29,
    207: 29,  # Zombieman
    252: 0,
    253: 0,  # Imp
    294: 39,  # Demon
    319: 40,  # Cacodemon
    344: 42,  # Baron
    370: 44,  # Lost Soul
    384: 45,  # Spider Mastermind
    398: 48,  # Cyberdemon
}


def parse_bits(value: str) -> int:
    """Parse a DEHACKED Bits value: either a decimal integer or BEX flag names."""
    value = value.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    result = 0
    for token in re.split(r"[+|,\s]+", value.upper()):
        token = token.strip()
        if token:
            result |= BEX_BITS.get(token, 0)
    return result
