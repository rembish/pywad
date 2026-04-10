"""Doom thing type catalog — names and rendering categories for well-known type IDs.

Covers Doom 1, Ultimate Doom, and Doom 2 thing types.  Heretic and Hexen
use the same numeric space but different IDs; unknown IDs fall back to UNKNOWN.
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
    (11, "Deathmatch Start", ThingCategory.PLAYER),
    (14, "Teleport Landing", ThingCategory.PLAYER),
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
    (73, "Hanging Torso One Arm", ThingCategory.DECORATION),
    (74, "Hanging Torso No Brain", ThingCategory.DECORATION),
    (75, "Pool of Brain", ThingCategory.DECORATION),
    (76, "Burning Barrel", ThingCategory.DECORATION),
    (77, "Hanging Legs", ThingCategory.DECORATION),
    (78, "Hanging Torso Looking Up", ThingCategory.DECORATION),
    (79, "Pool of Blood Small", ThingCategory.DECORATION),
    (80, "Brain Stem", ThingCategory.DECORATION),
    (81, "Pile of Guts", ThingCategory.DECORATION),
    (85, "Tall Techno Floor Lamp", ThingCategory.DECORATION),
    (86, "Short Techno Floor Lamp", ThingCategory.DECORATION),
    (87, "Spawn Spot", ThingCategory.DECORATION),
    (89, "Spawn Shooter", ThingCategory.DECORATION),
    # ---- Heretic monsters (non-conflicting IDs only) ---------------------------
    (70, "Iron Lich", ThingCategory.MONSTER),
    (90, "Golem Boss", ThingCategory.MONSTER),
    (92, "Nitrogolem Boss", ThingCategory.MONSTER),
    (254, "D'Sparil (Serpent)", ThingCategory.MONSTER),
    (255, "D'Sparil (Wizard)", ThingCategory.MONSTER),
    # ---- Hexen monsters (non-conflicting IDs only) -----------------------------
    (107, "Centaur", ThingCategory.MONSTER),
    (115, "Centaur Leader", ThingCategory.MONSTER),
    (120, "Stalker", ThingCategory.MONSTER),
    (121, "Stalker Boss", ThingCategory.MONSTER),
    (124, "Slaughtaur", ThingCategory.MONSTER),
    (125, "Slaughtaur Leader", ThingCategory.MONSTER),
    (8020, "Fire Gargoyle", ThingCategory.MONSTER),
    (8060, "Dragon", ThingCategory.MONSTER),
    (8080, "Demon Mage (Heresiarch)", ThingCategory.MONSTER),
    (10000, "Dark Bishop", ThingCategory.MONSTER),
    (10060, "Serpent Rider", ThingCategory.MONSTER),
    (10080, "Death Wyvern", ThingCategory.MONSTER),
    (10225, "Stalker (green)", ThingCategory.MONSTER),
    (10226, "Stalker (guardian)", ThingCategory.MONSTER),
    # ---- Hexen weapons (non-conflicting IDs only) ------------------------------
    (8010, "Flechette", ThingCategory.WEAPON),
    # ---- Hexen armor (non-conflicting IDs) ------------------------------------
    (8000, "Amulet of Warding", ThingCategory.ARMOR),
    (8001, "Platinum Helm", ThingCategory.ARMOR),
    (8002, "Falcon Shield", ThingCategory.ARMOR),
    (8003, "Mesh Armor", ThingCategory.ARMOR),
    # ---- Hexen keys (non-conflicting IDs) -------------------------------------
    (8030, "Steel Key", ThingCategory.KEY),
    (8031, "Cave Key", ThingCategory.KEY),
    (8032, "Axe Key", ThingCategory.KEY),
    (8033, "Fire Key", ThingCategory.KEY),
    (8034, "Emerald Key", ThingCategory.KEY),
    (8035, "Dungeon Key", ThingCategory.KEY),
    (8036, "Silver Key", ThingCategory.KEY),
    (8037, "Rusted Key", ThingCategory.KEY),
    (8038, "Horn Key", ThingCategory.KEY),
    (8039, "Swamp Key", ThingCategory.KEY),
    (8040, "Castle Key", ThingCategory.KEY),
    # ---- Hexen powerups (non-conflicting IDs) ---------------------------------
    (10040, "Dark Servant Summon", ThingCategory.POWERUP),
    (10100, "Icon of the Defender", ThingCategory.POWERUP),
    (10110, "Boots of Speed", ThingCategory.POWERUP),
    (10120, "Krater of Might", ThingCategory.POWERUP),
]

THING_TYPES: dict[int, tuple[str, ThingCategory]] = {row[0]: (row[1], row[2]) for row in _TABLE}

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
    # Decorations
    10: "PLAY",  # Bloody Mess (dead player)
    34: "CAND",  # Candle
    35: "CBRA",  # Candelabra
    76: "FCAN",  # Burning Barrel
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
}


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
