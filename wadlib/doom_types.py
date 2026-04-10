"""Doom thing type catalog — names and rendering categories for well-known type IDs.

Covers Doom 1, Ultimate Doom, and Doom 2 thing types only.  Heretic and Hexen
share numeric ranges but map IDs to completely different entities; they are
handled by heretic_types.py and hexen_types.py respectively.

# Done:    DEHACKED "ID # = N" custom types parsed by DehackedLump.things.
# TODO:    DECORATE/ZScript lumps — GZDoom PWADs can define actors with new
#          DoomEdNums directly in the WAD; parsing these would complete coverage.
"""

from enum import Enum


class ThingCategory(Enum):
    PLAYER = "player"
    MONSTER = "monster"
    WEAPON = "weapon"
    AMMO = "ammo"
    HEALTH = "health"
    ARMOR = "armor"
    KEY = "key"
    POWERUP = "powerup"
    DECORATION = "decoration"
    UNKNOWN = "unknown"


# (type_id, display_name, category)
_TABLE: list[tuple[int, str, ThingCategory]] = [
    # ---- Player spawns ---------------------------------------------------------
    (1, "Player 1 Start", ThingCategory.PLAYER),
    (2, "Player 2 Start", ThingCategory.PLAYER),
    (3, "Player 3 Start", ThingCategory.PLAYER),
    (4, "Player 4 Start", ThingCategory.PLAYER),
    (11, "Deathmatch Start", ThingCategory.DECORATION),
    (14, "Teleport Landing", ThingCategory.DECORATION),
    # ---- Monsters (Doom 1 + 2) -------------------------------------------------
    (3004, "Zombieman", ThingCategory.MONSTER),
    (9, "Shotgun Guy", ThingCategory.MONSTER),
    (65, "Chaingunner", ThingCategory.MONSTER),
    (3001, "Imp", ThingCategory.MONSTER),
    (3002, "Demon", ThingCategory.MONSTER),
    (58, "Spectre", ThingCategory.MONSTER),
    (3003, "Baron of Hell", ThingCategory.MONSTER),
    (3005, "Cacodemon", ThingCategory.MONSTER),
    (3006, "Lost Soul", ThingCategory.MONSTER),
    (7, "Spider Mastermind", ThingCategory.MONSTER),
    (16, "Cyberdemon", ThingCategory.MONSTER),
    (64, "Arch-Vile", ThingCategory.MONSTER),
    (66, "Revenant", ThingCategory.MONSTER),
    (67, "Mancubus", ThingCategory.MONSTER),
    (68, "Arachnotron", ThingCategory.MONSTER),
    (69, "Hell Knight", ThingCategory.MONSTER),
    (71, "Pain Elemental", ThingCategory.MONSTER),
    (72, "Commander Keen", ThingCategory.MONSTER),
    (84, "Wolfenstein SS", ThingCategory.MONSTER),
    (88, "Boss Brain", ThingCategory.MONSTER),
    (888, "MBF Helper Dog", ThingCategory.MONSTER),  # MBF source port extension
    # ---- Keys ------------------------------------------------------------------
    (5, "Blue Keycard", ThingCategory.KEY),
    (6, "Yellow Keycard", ThingCategory.KEY),
    (13, "Red Keycard", ThingCategory.KEY),
    (38, "Red Skull Key", ThingCategory.KEY),
    (39, "Yellow Skull Key", ThingCategory.KEY),
    (40, "Blue Skull Key", ThingCategory.KEY),
    # ---- Weapons ---------------------------------------------------------------
    (82, "Super Shotgun", ThingCategory.WEAPON),
    (2001, "Shotgun", ThingCategory.WEAPON),
    (2002, "Chaingun", ThingCategory.WEAPON),
    (2003, "Rocket Launcher", ThingCategory.WEAPON),
    (2004, "Plasma Rifle", ThingCategory.WEAPON),
    (2005, "Chainsaw", ThingCategory.WEAPON),
    (2006, "BFG 9000", ThingCategory.WEAPON),
    # ---- Ammo ------------------------------------------------------------------
    (17, "Energy Cell", ThingCategory.AMMO),
    (8, "Backpack", ThingCategory.AMMO),
    (2007, "Ammo Clip", ThingCategory.AMMO),
    (2008, "Shotgun Shells", ThingCategory.AMMO),
    (2010, "Rocket", ThingCategory.AMMO),
    (2046, "Box of Rockets", ThingCategory.AMMO),
    (2047, "Energy Cell Pack", ThingCategory.AMMO),
    (2048, "Box of Ammo", ThingCategory.AMMO),
    (2049, "Box of Shells", ThingCategory.AMMO),
    # ---- Health ----------------------------------------------------------------
    (2011, "Stimpack", ThingCategory.HEALTH),
    (2012, "Medikit", ThingCategory.HEALTH),
    (2013, "Soulsphere", ThingCategory.HEALTH),
    (2014, "Health Bonus", ThingCategory.HEALTH),
    # ---- Armor -----------------------------------------------------------------
    (2015, "Armor Bonus", ThingCategory.ARMOR),
    (2018, "Green Armor", ThingCategory.ARMOR),
    (2019, "Blue Armor", ThingCategory.ARMOR),
    # ---- Powerups --------------------------------------------------------------
    (83, "Megasphere", ThingCategory.POWERUP),
    (2022, "Invulnerability", ThingCategory.POWERUP),
    (2023, "Berserk Pack", ThingCategory.POWERUP),
    (2024, "Partial Invisibility", ThingCategory.POWERUP),
    (2025, "Radiation Suit", ThingCategory.POWERUP),
    (2026, "Computer Map", ThingCategory.POWERUP),
    (2045, "Light Amp Goggles", ThingCategory.POWERUP),
    # ---- Decorations (subset) --------------------------------------------------
    (10, "Bloody Mess", ThingCategory.DECORATION),
    (12, "Pool of Blood", ThingCategory.DECORATION),
    (15, "Dead Player", ThingCategory.DECORATION),
    (18, "Dead Zombieman", ThingCategory.DECORATION),
    (19, "Dead Shotgun Guy", ThingCategory.DECORATION),
    (20, "Dead Imp", ThingCategory.DECORATION),
    (21, "Dead Demon", ThingCategory.DECORATION),
    (22, "Dead Cacodemon", ThingCategory.DECORATION),
    (23, "Dead Lost Soul", ThingCategory.DECORATION),
    (24, "Pool of Blood", ThingCategory.DECORATION),
    (25, "Impaled Human", ThingCategory.DECORATION),
    (26, "Twitching Impaled", ThingCategory.DECORATION),
    (27, "Skull on a Pole", ThingCategory.DECORATION),
    (28, "Five Skulls", ThingCategory.DECORATION),
    (29, "Pile of Skulls", ThingCategory.DECORATION),
    (30, "Tall Green Column", ThingCategory.DECORATION),
    (31, "Short Green Column", ThingCategory.DECORATION),
    (32, "Tall Red Column", ThingCategory.DECORATION),
    (33, "Short Red Column", ThingCategory.DECORATION),
    (34, "Candle", ThingCategory.DECORATION),
    (35, "Candelabra", ThingCategory.DECORATION),
    (36, "Tall Skull Column", ThingCategory.DECORATION),
    (37, "Short Skull Column", ThingCategory.DECORATION),
    (41, "Evil Eye", ThingCategory.DECORATION),
    (42, "Floating Skull", ThingCategory.DECORATION),
    (43, "Burnt Tree", ThingCategory.DECORATION),
    (44, "Tall Blue Firestick", ThingCategory.DECORATION),
    (45, "Tall Green Firestick", ThingCategory.DECORATION),
    (46, "Tall Red Firestick", ThingCategory.DECORATION),
    (47, "Stalagtite", ThingCategory.DECORATION),
    (48, "Techno Column", ThingCategory.DECORATION),
    (49, "Hanging Body", ThingCategory.DECORATION),
    (50, "Hanging Torso", ThingCategory.DECORATION),
    (51, "One-Legged Body", ThingCategory.DECORATION),
    (52, "Hanging Pair Legs", ThingCategory.DECORATION),
    (53, "Hanging Leg", ThingCategory.DECORATION),
    (54, "Large Brown Tree", ThingCategory.DECORATION),
    (55, "Short Blue Firestick", ThingCategory.DECORATION),
    (56, "Short Green Firestick", ThingCategory.DECORATION),
    (57, "Short Red Firestick", ThingCategory.DECORATION),
    (59, "Hanging Body Twitching", ThingCategory.DECORATION),
    (60, "Hanging Body Arms Out", ThingCategory.DECORATION),
    (61, "Hanging Torso Looking Down", ThingCategory.DECORATION),
    (62, "Hanging Torso Open Brain", ThingCategory.DECORATION),
    (63, "Hanging Torso Brain Out", ThingCategory.DECORATION),
    (70, "Burning Barrel", ThingCategory.DECORATION),  # Doom 2
    (73, "Hanging Victim Guts Removed", ThingCategory.DECORATION),
    (74, "Hanging Victim Guts and Brain Removed", ThingCategory.DECORATION),
    (75, "Hanging Torso Looking Down", ThingCategory.DECORATION),
    (76, "Hanging Torso Open Skull", ThingCategory.DECORATION),
    (77, "Hanging Torso Looking Up", ThingCategory.DECORATION),
    (78, "Hanging Torso Brain Removed", ThingCategory.DECORATION),
    (79, "Pool of Blood", ThingCategory.DECORATION),
    (80, "Pool of Blood (small)", ThingCategory.DECORATION),
    (81, "Pool of Brains", ThingCategory.DECORATION),
    (85, "Tall Techno Floor Lamp", ThingCategory.DECORATION),
    (86, "Short Techno Floor Lamp", ThingCategory.DECORATION),
    (2028, "Floor Lamp", ThingCategory.DECORATION),
    (87, "Spawn Spot", ThingCategory.DECORATION),
    (89, "Spawn Shooter", ThingCategory.DECORATION),
    (2035, "Exploding Barrel", ThingCategory.DECORATION),
]

THING_TYPES: dict[int, tuple[str, ThingCategory]] = {row[0]: (row[1], row[2]) for row in _TABLE}

# Thing type IDs that have no in-game visual representation (invisible game-mechanics
# markers such as deathmatch spawns, teleport destinations, and boss brain targets).
# The renderer skips these by default.
INVISIBLE_TYPES: frozenset[int] = frozenset(
    {
        0,  # Null/corrupt editor placeholder — not a real thing
        11,  # Deathmatch Start
        14,  # Teleport Landing
        87,  # Spawn Spot (boss brain target)
        89,  # Spawn Shooter
    }
)

# Maps thing type ID to the 4-char WAD sprite lump prefix (first frame = "A0" or "A1").
# Only Doom 1/2 things are listed; Heretic/Hexen entries are omitted (different WADs).
_SPRITE_PREFIXES: dict[int, str] = {
    # Player spawns
    1: "PLAY",
    2: "PLAY",
    3: "PLAY",
    4: "PLAY",
    # Monsters
    3004: "POSS",  # Zombieman
    9: "SPOS",  # Shotgun Guy
    65: "CPOS",  # Chaingunner
    3001: "TROO",  # Imp
    3002: "SARG",  # Demon
    58: "SARG",  # Spectre (invisible, uses same sprite)
    3003: "BOSS",  # Baron of Hell
    3005: "HEAD",  # Cacodemon
    3006: "SKUL",  # Lost Soul
    7: "SPID",  # Spider Mastermind
    16: "CYBR",  # Cyberdemon
    64: "VILE",  # Arch-Vile
    66: "SKEL",  # Revenant
    67: "FATT",  # Mancubus
    68: "BSPI",  # Arachnotron
    69: "BOS2",  # Hell Knight
    71: "PAIN",  # Pain Elemental
    72: "KEEN",  # Commander Keen
    84: "SSWV",  # Wolfenstein SS
    88: "BBRN",  # Boss Brain
    888: "DOGS",  # MBF Helper Dog
    # Keys
    5: "BKEY",
    6: "YKEY",
    13: "RKEY",
    38: "RSKU",
    39: "YSKU",
    40: "BSKU",
    # Weapons
    82: "SGN2",
    2001: "SHOT",
    2002: "MGUN",
    2003: "LAUN",
    2004: "PLAS",
    2005: "CSAW",
    2006: "BFUG",
    # Ammo
    2007: "CLIP",
    2008: "SHEL",
    2010: "ROCK",
    17: "CELL",
    8: "BPAK",
    2046: "BROK",
    2047: "CELP",
    2048: "AMMO",
    2049: "SBOX",
    # Health
    2011: "STIM",
    2012: "MEDI",
    2013: "SOUL",
    2014: "BON1",
    # Armor
    2015: "BON2",
    2018: "ARM1",
    2019: "ARM2",
    # Powerups
    83: "MEGA",
    2022: "PINV",
    2023: "PSTR",
    2024: "PINS",
    2025: "SUIT",
    2026: "PMAP",
    2045: "PVIS",
    # Dead decorations — same prefixes as the live entity; use death-frame suffix
    10: "PLAY",  # Bloody Mess
    12: "PLAY",  # Pool of Blood and Flesh
    15: "PLAY",  # Dead Player
    18: "POSS",  # Dead Zombieman
    19: "SPOS",  # Dead Shotgun Guy
    20: "TROO",  # Dead Imp
    21: "SARG",  # Dead Demon
    22: "HEAD",  # Dead Cacodemon
    23: "SKUL",  # Dead Lost Soul
    # Impaled bodies / skull poles (Doom 1 & 2)
    25: "POL1",  # Impaled Human
    26: "POL6",  # Twitching Impaled Human
    27: "POL4",  # Skull on a Pole
    28: "POL3",  # Five Skulls (Pile)
    29: "POL5",  # Pile of Skulls and Bones
    # Misc gore decorations
    41: "CEYE",  # Evil Eye
    42: "FSKU",  # Floating Skulls
    # Hanging corpses (Doom 2) — non-blocking
    49: "GOR1",  # Hanging body
    50: "GOR2",  # Hanging body (arms out)
    51: "GOR3",  # Hanging pair of legs
    52: "GOR4",  # Hanging victim (1-legged)
    53: "GOR5",  # Hanging leg
    # Hanging corpses (Doom 2) — blocking variants use same sprites
    59: "GOR1",
    60: "GOR3",
    61: "GOR5",
    62: "GOR2",
    63: "GOR4",
    # Burning barrel (Doom 2)
    70: "FCAN",
    # Hanging torsos (Doom 2) — HDB series (types 73-78)
    73: "HDB1",  # Hanging victim, guts removed
    74: "HDB2",  # Hanging victim, guts and brain removed
    75: "HDB3",  # Hanging torso, looking down
    76: "HDB4",  # Hanging torso, open skull
    77: "HDB5",  # Hanging torso, looking up
    78: "HDB6",  # Hanging torso, brain removed
    # Blood pools (Doom 2)
    24: "POL5",  # Pool of blood and flesh
    79: "POB1",  # Pool of blood
    80: "POB2",  # Pool of blood (small)
    81: "BRS1",  # Pool of brains
    # Explosive barrel (Doom 2)
    2035: "BAR1",
    # Static decorations — "A0" idle is correct
    34: "CAND",  # Candle
    35: "CBRA",  # Candelabra
    48: "ELEC",  # Techno Column
    30: "COL1",
    31: "COL2",
    32: "COL3",
    33: "COL4",
    36: "COL5",
    37: "COL6",
    43: "TRE1",
    54: "TRE2",
    44: "TBLU",
    45: "TGRN",
    46: "TRED",
    55: "SMBT",
    56: "SMGT",
    57: "SMRT",
    47: "SMIT",  # Stalagmite
    85: "TLMP",
    86: "TLP2",
    2028: "COLU",  # Floor lamp
}


# For dead-character decorations the last death frame ("N0") is the correct
# static pose.  Everything else uses the default idle rotation ("A0", "A1").
_SPRITE_SUFFIX_OVERRIDES: dict[int, tuple[str, ...]] = {
    10: ("N0",),  # Bloody Mess
    12: ("N0",),  # Pool of Blood and Flesh
    15: ("N0",),  # Dead Player
    18: ("N0",),  # Dead Zombieman
    19: ("N0",),  # Dead Shotgun Guy
    20: ("N0",),  # Dead Imp
    21: ("N0",),  # Dead Demon
    22: ("N0",),  # Dead Cacodemon
    23: ("N0",),  # Dead Lost Soul
}
_DEFAULT_SPRITE_SUFFIXES: tuple[str, ...] = ("A0", "A1")


def get_sprite_suffixes(type_id: int) -> tuple[str, ...]:
    """Return the sprite frame suffixes to try for *type_id* (most preferred first)."""
    return _SPRITE_SUFFIX_OVERRIDES.get(type_id, _DEFAULT_SPRITE_SUFFIXES)


def get_name(type_id: int) -> str:
    """Return the display name for a thing type, or 'Unknown (#id)'."""
    entry = THING_TYPES.get(type_id)
    return entry[0] if entry else f"Unknown (#{type_id})"


def get_category(type_id: int) -> ThingCategory:
    """Return the ThingCategory for a thing type, or UNKNOWN."""
    entry = THING_TYPES.get(type_id)
    return entry[1] if entry else ThingCategory.UNKNOWN


def get_sprite_prefix(type_id: int) -> str | None:
    """Return the 4-char WAD sprite lump prefix for *type_id*, or None if unknown."""
    return _SPRITE_PREFIXES.get(type_id)
