"""Heretic thing type catalog — names and rendering categories.

Type IDs are INCOMPATIBLE with Doom: e.g. type 5 = Fire Gargoyle (Heretic)
but type 5 = Blue Keycard (Doom).  Never mix with doom_types tables.

# TODO: support DECORATE/ZScript lumps so GZDoom PWADs can define new types.
"""

from .doom_types import ThingCategory

_TABLE: list[tuple[int, str, ThingCategory]] = [
    # ---- Player spawns --------------------------------------------------------
    (1, "Player 1 Start", ThingCategory.PLAYER),
    (2, "Player 2 Start", ThingCategory.PLAYER),
    (3, "Player 3 Start", ThingCategory.PLAYER),
    (4, "Player 4 Start", ThingCategory.PLAYER),
    # ---- Monsters -------------------------------------------------------------
    (5, "Fire Gargoyle", ThingCategory.MONSTER),
    (6, "Iron Lich", ThingCategory.MONSTER),
    (7, "D'Sparil (on Chaos Serpent)", ThingCategory.MONSTER),
    (9, "Maulotaur", ThingCategory.MONSTER),
    (15, "Disciple of D'Sparil", ThingCategory.MONSTER),
    (45, "Nitrogolem", ThingCategory.MONSTER),
    (46, "Nitrogolem Ghost", ThingCategory.MONSTER),
    (64, "Undead Warrior", ThingCategory.MONSTER),
    (65, "Undead Warrior Ghost", ThingCategory.MONSTER),
    (66, "Gargoyle", ThingCategory.MONSTER),
    (68, "Golem", ThingCategory.MONSTER),
    (69, "Golem Ghost", ThingCategory.MONSTER),
    (70, "Weredragon", ThingCategory.MONSTER),
    (90, "Sabreclaw", ThingCategory.MONSTER),
    (92, "Ophidian", ThingCategory.MONSTER),
    # ---- Weapons --------------------------------------------------------------
    (53, "Dragon Claw", ThingCategory.WEAPON),
    (2001, "Ethereal Crossbow", ThingCategory.WEAPON),
    (2002, "Firemace", ThingCategory.WEAPON),
    (2003, "Phoenix Rod", ThingCategory.WEAPON),
    (2004, "Hellstaff", ThingCategory.WEAPON),
    (2005, "Gauntlets of the Necromancer", ThingCategory.WEAPON),
    # ---- Ammunition -----------------------------------------------------------
    (10, "Wand Crystal", ThingCategory.AMMO),
    (12, "Crystal Geode", ThingCategory.AMMO),
    (13, "Mace Spheres", ThingCategory.AMMO),
    (16, "Pile of Mace Spheres", ThingCategory.AMMO),
    (18, "Ethereal Arrows", ThingCategory.AMMO),
    (19, "Quiver of Ethereal Arrows", ThingCategory.AMMO),
    (20, "Lesser Runes", ThingCategory.AMMO),
    (21, "Greater Runes", ThingCategory.AMMO),
    (22, "Flame Orb", ThingCategory.AMMO),
    (23, "Inferno Orb", ThingCategory.AMMO),
    (54, "Claw Orb", ThingCategory.AMMO),
    (55, "Energy Orb", ThingCategory.AMMO),
    # ---- Health ---------------------------------------------------------------
    (81, "Crystal Vial", ThingCategory.HEALTH),
    (82, "Quartz Flask", ThingCategory.HEALTH),
    # ---- Armor ----------------------------------------------------------------
    (31, "Enchanted Shield", ThingCategory.ARMOR),
    (85, "Silver Shield", ThingCategory.ARMOR),
    # ---- Keys -----------------------------------------------------------------
    (73, "Green Key", ThingCategory.KEY),
    (79, "Blue Key", ThingCategory.KEY),
    (80, "Yellow Key", ThingCategory.KEY),
    # ---- Powerups -------------------------------------------------------------
    (8, "Bag of Holding", ThingCategory.POWERUP),
    (30, "Morph Ovum", ThingCategory.POWERUP),
    (32, "Mystic Urn", ThingCategory.POWERUP),
    (33, "Torch", ThingCategory.POWERUP),
    (34, "Time Bomb of the Ancients", ThingCategory.POWERUP),
    (35, "Map Scroll", ThingCategory.POWERUP),
    (36, "Chaos Device", ThingCategory.POWERUP),
    (75, "Shadowsphere", ThingCategory.POWERUP),
    (83, "Wings of Wrath", ThingCategory.POWERUP),
    (84, "Ring of Invincibility", ThingCategory.POWERUP),
    (86, "Tome of Power", ThingCategory.POWERUP),
    # ---- Decorations ----------------------------------------------------------
    (17, "Hanging Skull (long rope)", ThingCategory.DECORATION),
    (24, "Hanging Skull (medium rope)", ThingCategory.DECORATION),
    (25, "Hanging Skull (short rope)", ThingCategory.DECORATION),
    (26, "Hanging Skull (shortest rope)", ThingCategory.DECORATION),
    (27, "Serpent Torch", ThingCategory.DECORATION),
    (28, "Chandelier", ThingCategory.DECORATION),
    (29, "Short Grey Pillar", ThingCategory.DECORATION),
    (37, "Small Stalagmite", ThingCategory.DECORATION),
    (38, "Large Stalagmite", ThingCategory.DECORATION),
    (39, "Small Stalactite", ThingCategory.DECORATION),
    (40, "Large Stalactite", ThingCategory.DECORATION),
    (44, "Barrel", ThingCategory.DECORATION),
    (47, "Tall Brown Pillar", ThingCategory.DECORATION),
    (48, "Moss (2 strings)", ThingCategory.DECORATION),
    (49, "Moss (1 string)", ThingCategory.DECORATION),
    (50, "Wall Torch", ThingCategory.DECORATION),
    (51, "Hanging Corpse", ThingCategory.DECORATION),
    (52, "Teleport Glitter", ThingCategory.DECORATION),
    (74, "Teleport Glitter", ThingCategory.DECORATION),
    (76, "Fire Brazier", ThingCategory.DECORATION),
    (87, "Volcano", ThingCategory.DECORATION),
    (94, "Key Gizmo (blue)", ThingCategory.DECORATION),
    (95, "Key Gizmo (green)", ThingCategory.DECORATION),
    (96, "Key Gizmo (yellow)", ThingCategory.DECORATION),
    (2035, "Pod", ThingCategory.DECORATION),
    # ---- Invisible markers (no in-game visual) --------------------------------
    (11, "Deathmatch Start", ThingCategory.DECORATION),
    (14, "Teleport Landing", ThingCategory.DECORATION),
    (41, "Waterfall Sound", ThingCategory.DECORATION),
    (42, "Wind Sound", ThingCategory.DECORATION),
    (43, "Pod Generator", ThingCategory.DECORATION),
    (56, "D'Sparil Teleport Spot", ThingCategory.DECORATION),
    (1200, "Ambient: Scream", ThingCategory.DECORATION),
    (1201, "Ambient: Squish", ThingCategory.DECORATION),
    (1202, "Ambient: Drops", ThingCategory.DECORATION),
    (1203, "Ambient: Footsteps (slow)", ThingCategory.DECORATION),
    (1204, "Ambient: Heartbeat", ThingCategory.DECORATION),
    (1205, "Ambient: Bells", ThingCategory.DECORATION),
    (1206, "Ambient: Growl", ThingCategory.DECORATION),
    (1207, "Ambient: Magic", ThingCategory.DECORATION),
    (1208, "Ambient: Laughter", ThingCategory.DECORATION),
    (1209, "Ambient: Footsteps (fast)", ThingCategory.DECORATION),
]

THING_TYPES: dict[int, tuple[str, ThingCategory]] = {row[0]: (row[1], row[2]) for row in _TABLE}

INVISIBLE_TYPES: frozenset[int] = frozenset({
    11,   # Deathmatch Start
    14,   # Teleport Landing
    41,   # Waterfall ambient emitter
    42,   # Wind ambient emitter
    43,   # Pod generator spawner
    56,   # D'Sparil teleport spot
    1200, 1201, 1202, 1203, 1204,  # Ambient sounds
    1205, 1206, 1207, 1208, 1209,
})

_SPRITE_PREFIXES: dict[int, str] = {
    # Player spawns
    1: "PLAY", 2: "PLAY", 3: "PLAY", 4: "PLAY",
    # Monsters
    5: "IMPX",   # Fire Gargoyle
    6: "HEAD",   # Iron Lich
    7: "SRCR",   # D'Sparil (Chaos Serpent form)
    9: "MNTR",   # Maulotaur
    15: "WZRD",  # Disciple of D'Sparil
    45: "MUMM",  # Nitrogolem
    46: "MUMM",  # Nitrogolem Ghost
    64: "KNIG",  # Undead Warrior
    65: "KNIG",  # Undead Warrior Ghost
    66: "IMPX",  # Gargoyle
    68: "MUMM",  # Golem
    69: "MUMM",  # Golem Ghost
    70: "BEAS",  # Weredragon
    90: "CLNK",  # Sabreclaw
    92: "SNKE",  # Ophidian
    # Weapons
    53: "WBLS",
    2001: "WBOW",
    2002: "WMCE",
    2003: "WPHX",
    2004: "WSKL",
    2005: "WGNT",
    # Ammo
    10: "AMG1",
    12: "AMG2",
    13: "AMM1",
    16: "AMM2",
    18: "AMC1",
    19: "AMC2",
    20: "AMS1",
    21: "AMS2",
    22: "AMP1",
    23: "AMP2",
    54: "AMB1",
    55: "AMB2",
    # Health
    81: "PTN1",
    82: "PTN2",
    # Armor
    31: "SHD2",
    85: "SHLD",
    # Keys
    73: "AKYY",
    79: "BKYY",
    80: "CKYY",
    # Powerups
    8: "BAGH",
    30: "EGGC",
    32: "SPHL",
    33: "TRCH",
    34: "FBMB",
    35: "SPMP",
    36: "ATLP",
    75: "INVS",
    83: "SOAR",
    84: "INVU",
    86: "PWBK",
    # Decorations
    17: "SKH1",
    24: "SKH2",
    25: "SKH3",
    26: "SKH4",
    27: "SRTC",
    28: "CHDL",
    29: "SMPL",
    37: "STGS",
    38: "STGL",
    39: "STCS",
    40: "STCL",
    44: "BARL",
    47: "BRPL",
    48: "MOS1",
    49: "MOS2",
    50: "WTRH",
    51: "HCOR",
    52: "TGLT",
    74: "TGLT",
    76: "KFR1",
    87: "VLCO",
    94: "KGZ1",
    95: "KGZ1",
    96: "KGZ1",
    2035: "PPOD",
}

_DEFAULT_SPRITE_SUFFIXES: tuple[str, ...] = ("A0", "A1")


def get_sprite_suffixes(type_id: int) -> tuple[str, ...]:
    return _DEFAULT_SPRITE_SUFFIXES


def get_name(type_id: int) -> str:
    entry = THING_TYPES.get(type_id)
    return entry[0] if entry else f"Unknown (#{type_id})"


def get_category(type_id: int) -> ThingCategory:
    entry = THING_TYPES.get(type_id)
    return entry[1] if entry else ThingCategory.UNKNOWN


def get_sprite_prefix(type_id: int) -> str | None:
    return _SPRITE_PREFIXES.get(type_id)
