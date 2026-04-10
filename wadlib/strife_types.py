"""Strife thing type catalog — names, categories, and sprite prefixes.

Covers the Strife IWAD (STRIFE1.WAD) and SVE (Veteran Edition) thing types.
Strife uses the standard Doom THINGS lump format (no extra fields like Hexen).

Game detection: Strife WADs contain the ``AGRD`` sprite prefix (Acolyte Guard),
which does not appear in Doom, Heretic, or Hexen WADs.

Type ID reference: GZDoom wadsrc/static/mapinfo/strife.txt (DoomEdNums block),
cross-referenced with wadsrc/static/zscript/actors/strife/*.zs sprite declarations.
"""

from .doom_types import ThingCategory

# (type_id, display_name, category)
_TABLE: list[tuple[int, str, ThingCategory]] = [
    # ---- Player spawns ---------------------------------------------------------
    (1,   "Player 1 Start",            ThingCategory.PLAYER),
    (2,   "Player 2 Start",            ThingCategory.PLAYER),
    (3,   "Player 3 Start",            ThingCategory.PLAYER),
    (4,   "Player 4 Start",            ThingCategory.PLAYER),
    (5,   "Player 5 Start",            ThingCategory.PLAYER),
    (6,   "Player 6 Start",            ThingCategory.PLAYER),
    (7,   "Player 7 Start",            ThingCategory.PLAYER),
    (8,   "Player 8 Start",            ThingCategory.PLAYER),
    # Multiplayer / variant player starts
    (118, "Player Start (variant 1)",  ThingCategory.PLAYER),
    (119, "Player Start (variant 2)",  ThingCategory.PLAYER),
    (120, "Player Start (variant 3)",  ThingCategory.PLAYER),
    (121, "Player Start (variant 4)",  ThingCategory.PLAYER),
    (122, "Player Start (variant 5)",  ThingCategory.PLAYER),
    (123, "Player Start (variant 6)",  ThingCategory.PLAYER),
    (124, "Player Start (variant 7)",  ThingCategory.PLAYER),
    (125, "Player Start (variant 8)",  ThingCategory.PLAYER),
    (126, "Player Start (variant 9)",  ThingCategory.PLAYER),
    (127, "Player Start (variant 10)", ThingCategory.PLAYER),
    # ---- Monsters / enemies ----------------------------------------------------
    # Acolyte variants (all use AGRD sprite)
    (3002, "Acolyte (Tan)",            ThingCategory.MONSTER),
    (58,   "Acolyte (Shadow)",         ThingCategory.MONSTER),
    (142,  "Acolyte (Red)",            ThingCategory.MONSTER),
    (143,  "Acolyte (Rust)",           ThingCategory.MONSTER),
    (146,  "Acolyte (Gray)",           ThingCategory.MONSTER),
    (147,  "Acolyte (Dark Green)",     ThingCategory.MONSTER),
    (148,  "Acolyte (Gold)",           ThingCategory.MONSTER),
    (201,  "Acolyte-to-Be",            ThingCategory.MONSTER),
    (231,  "Acolyte (Blue)",           ThingCategory.MONSTER),
    (232,  "Acolyte (Light Green)",    ThingCategory.MONSTER),
    # Peasants (PEAS sprite — hostile civilians who may attack)
    (3004, "Peasant",                  ThingCategory.MONSTER),
    (65,   "Peasant (4)",              ThingCategory.MONSTER),
    (66,   "Peasant (7)",              ThingCategory.MONSTER),
    (67,   "Peasant (10)",             ThingCategory.MONSTER),
    (130,  "Peasant (2)",              ThingCategory.MONSTER),
    (131,  "Peasant (3)",              ThingCategory.MONSTER),
    (132,  "Peasant (5)",              ThingCategory.MONSTER),
    (133,  "Peasant (6)",              ThingCategory.MONSTER),
    (134,  "Peasant (8)",              ThingCategory.MONSTER),
    (135,  "Peasant (9)",              ThingCategory.MONSTER),
    (136,  "Peasant (11)",             ThingCategory.MONSTER),
    (137,  "Peasant (12)",             ThingCategory.MONSTER),
    (172,  "Peasant (13)",             ThingCategory.MONSTER),
    (173,  "Peasant (14)",             ThingCategory.MONSTER),
    (174,  "Peasant (15)",             ThingCategory.MONSTER),
    (175,  "Peasant (16)",             ThingCategory.MONSTER),
    (176,  "Peasant (17)",             ThingCategory.MONSTER),
    (177,  "Peasant (18)",             ThingCategory.MONSTER),
    (178,  "Peasant (19)",             ThingCategory.MONSTER),
    (179,  "Peasant (20)",             ThingCategory.MONSTER),
    (180,  "Peasant (21)",             ThingCategory.MONSTER),
    (181,  "Peasant (22)",             ThingCategory.MONSTER),
    # Rebels (HMN1 sprite — allied fighters turned enemy in some contexts)
    (9,    "Rebel",                    ThingCategory.MONSTER),
    (144,  "Rebel (2)",                ThingCategory.MONSTER),
    (145,  "Rebel (3)",                ThingCategory.MONSTER),
    (149,  "Rebel (4)",                ThingCategory.MONSTER),
    (150,  "Rebel (5)",                ThingCategory.MONSTER),
    (151,  "Rebel (6)",                ThingCategory.MONSTER),
    # Beggars (BEGR sprite)
    (141,  "Beggar",                   ThingCategory.MONSTER),
    (155,  "Beggar (2)",               ThingCategory.MONSTER),
    (156,  "Beggar (3)",               ThingCategory.MONSTER),
    (157,  "Beggar (4)",               ThingCategory.MONSTER),
    (158,  "Beggar (5)",               ThingCategory.MONSTER),
    # Robots & mechanicals
    (3001, "Reaver",                   ThingCategory.MONSTER),   # ROB1
    (3005, "Crusader",                 ThingCategory.MONSTER),   # ROB2
    (16,   "Inquisitor",               ThingCategory.MONSTER),   # ROB3
    (3006, "Sentinel",                 ThingCategory.MONSTER),   # SEWR
    (3003, "Templar",                  ThingCategory.MONSTER),   # PGRD
    (186,  "Stalker",                  ThingCategory.MONSTER),   # STLK
    (187,  "Bishop",                   ThingCategory.MONSTER),   # MLDR
    # Alien / spectral
    (129,  "Alien Spectre",            ThingCategory.MONSTER),   # ALN1
    (75,   "Alien Spectre (2)",        ThingCategory.MONSTER),   # ALN1
    (76,   "Alien Spectre (3)",        ThingCategory.MONSTER),   # ALN1
    (167,  "Alien Spectre (4)",        ThingCategory.MONSTER),   # ALN1
    (168,  "Alien Spectre (5)",        ThingCategory.MONSTER),   # ALN1
    (128,  "Entity (final boss)",      ThingCategory.MONSTER),   # MNAL
    # Boss / quest enemies
    (12,   "Loremaster",               ThingCategory.MONSTER),   # PRST
    (71,   "Programmer",               ThingCategory.MONSTER),   # PRGR
    (199,  "Oracle",                   ThingCategory.MONSTER),   # ORCL
    # Misc creatures
    (85,   "Rat Buddy",                ThingCategory.MONSTER),   # RATT
    (169,  "Zombie",                   ThingCategory.MONSTER),   # PEAS
    # ---- Gameplay markers (invisible — in INVISIBLE_TYPES) ---------------------
    (14,   "Teleport Landing",         ThingCategory.DECORATION),
    (23,   "Teleport Swirl",           ThingCategory.DECORATION),
    (25,   "Force Field Guard",        ThingCategory.DECORATION),  # invisible
    (170,  "Zombie Spawner",           ThingCategory.DECORATION),  # invisible
    (9001, "DM Spot (1)",              ThingCategory.DECORATION),  # invisible DM markers
    (9002, "DM Spot (2)",              ThingCategory.DECORATION),
    (9003, "DM Spot (3)",              ThingCategory.DECORATION),
    (9004, "DM Spot (4)",              ThingCategory.DECORATION),
    (9005, "DM Spot (5)",              ThingCategory.DECORATION),
    # ---- Quest NPCs (treated as decoration — friendly / non-enemy) -------------
    (64,   "Macil (Chapter 1)",        ThingCategory.DECORATION),  # LEAD
    (200,  "Macil (Chapter 4)",        ThingCategory.DECORATION),  # LEAD
    (72,   "Bar Keeper",               ThingCategory.DECORATION),  # MRST
    (73,   "Armorer",                  ThingCategory.DECORATION),  # MRST
    (74,   "Medic",                    ThingCategory.DECORATION),  # MRST
    (116,  "Weapon Smith",             ThingCategory.DECORATION),  # MRST
    (117,  "Surgery Crab",             ThingCategory.DECORATION),  # CRAB
    # ---- Weapons ---------------------------------------------------------------
    (2001, "Crossbow",                 ThingCategory.WEAPON),
    (2002, "Assault Rifle",            ThingCategory.WEAPON),
    (2006, "Assault Rifle (standing)", ThingCategory.WEAPON),
    (2003, "Mini Missile Launcher",    ThingCategory.WEAPON),
    (2004, "Mauler",                   ThingCategory.WEAPON),
    (2005, "Flame Thrower",            ThingCategory.WEAPON),
    (154,  "Grenade Launcher",         ThingCategory.WEAPON),
    # Sigil pieces (weapon / quest item)
    (77,   "Sigil (1 piece)",          ThingCategory.WEAPON),
    (78,   "Sigil (2 pieces)",         ThingCategory.WEAPON),
    (79,   "Sigil (3 pieces)",         ThingCategory.WEAPON),
    (80,   "Sigil (4 pieces)",         ThingCategory.WEAPON),
    (81,   "Sigil (5 pieces)",         ThingCategory.WEAPON),
    # ---- Ammo ------------------------------------------------------------------
    (11,   "Clip of Bullets",          ThingCategory.AMMO),   # Strife: 11 = ammo
    (2007, "Clip of Bullets",          ThingCategory.AMMO),
    (2048, "Box of Bullets",           ThingCategory.AMMO),
    (17,   "Energy Pack",              ThingCategory.AMMO),
    (2047, "Energy Pod",               ThingCategory.AMMO),
    (2010, "Mini Missiles",            ThingCategory.AMMO),
    (2046, "Crate of Missiles",        ThingCategory.AMMO),
    (152,  "HE Grenade Rounds",        ThingCategory.AMMO),
    (153,  "Phosphorus Grenade Rounds",ThingCategory.AMMO),
    (114,  "Electric Bolts",           ThingCategory.AMMO),
    (115,  "Poison Bolts",             ThingCategory.AMMO),
    (183,  "Ammo Satchel",             ThingCategory.AMMO),
    # ---- Health ----------------------------------------------------------------
    (2011, "Med Patch",                ThingCategory.HEALTH),
    (2012, "Medical Kit",              ThingCategory.HEALTH),
    (83,   "Surgery Kit",              ThingCategory.HEALTH),
    (2014, "Water Bottle",             ThingCategory.HEALTH),
    # ---- Armor -----------------------------------------------------------------
    (2018, "Leather Armor",            ThingCategory.ARMOR),
    (2019, "Metal Armor",              ThingCategory.ARMOR),
    # ---- Power-ups / special items ---------------------------------------------
    (2024, "Shadow Armor",             ThingCategory.POWERUP),
    (2025, "Environmental Suit",       ThingCategory.POWERUP),
    (2026, "Strife Map",               ThingCategory.POWERUP),
    (2027, "Scanner",                  ThingCategory.POWERUP),
    (2028, "Light Globe",              ThingCategory.POWERUP),
    (207,  "Targeter",                 ThingCategory.POWERUP),
    (206,  "Communicator",             ThingCategory.POWERUP),
    (90,   "Guard Uniform",            ThingCategory.POWERUP),
    (52,   "Officer's Uniform",        ThingCategory.POWERUP),
    (217,  "Rebel Boots",              ThingCategory.POWERUP),
    (218,  "Rebel Helmet",             ThingCategory.POWERUP),
    (219,  "Rebel Shirt",              ThingCategory.POWERUP),
    (116,  "Weapon Smith Training",    ThingCategory.POWERUP),
    # ---- Keys / quest items ----------------------------------------------------
    (38,   "Silver Key",               ThingCategory.KEY),
    (39,   "Brass Key",                ThingCategory.KEY),
    (40,   "Gold Key",                 ThingCategory.KEY),
    (61,   "Oracle Key",               ThingCategory.KEY),
    (86,   "Order Key",                ThingCategory.KEY),
    (166,  "Warehouse Key",            ThingCategory.KEY),
    (184,  "ID Badge",                 ThingCategory.KEY),
    (185,  "Passcard",                 ThingCategory.KEY),
    (192,  "Red Crystal Key",          ThingCategory.KEY),
    (193,  "Blue Crystal Key",         ThingCategory.KEY),
    (195,  "Chapel Key",               ThingCategory.KEY),
    (230,  "Base Key",                 ThingCategory.KEY),
    (233,  "Mauler Key",               ThingCategory.KEY),
    (234,  "Factory Key",              ThingCategory.KEY),
    (235,  "Mine Key",                 ThingCategory.KEY),
    (236,  "Core Key",                 ThingCategory.KEY),
    (13,   "ID Card",                  ThingCategory.KEY),
    # ---- Currency --------------------------------------------------------------
    (93,   "Coin",                     ThingCategory.AMMO),   # currency / trade item
    (138,  "Gold (10)",                ThingCategory.AMMO),
    (139,  "Gold (25)",                ThingCategory.AMMO),
    (140,  "Gold (50)",                ThingCategory.AMMO),
    # ---- Miscellaneous items ---------------------------------------------------
    (92,   "Power Crystal",            ThingCategory.POWERUP),
    (220,  "Power Coupling",           ThingCategory.POWERUP),
    (226,  "Broken Power Coupling",    ThingCategory.DECORATION),
    (59,   "Degning Ore",              ThingCategory.POWERUP),
    (228,  "Ammo Filler",              ThingCategory.AMMO),
    # ---- Decorations -----------------------------------------------------------
    # Dead characters
    (15,   "Dead Player",              ThingCategory.DECORATION),
    (18,   "Dead Peasant",             ThingCategory.DECORATION),
    (19,   "Dead Rebel",               ThingCategory.DECORATION),
    (20,   "Dead Reaver",              ThingCategory.DECORATION),
    (21,   "Dead Acolyte",             ThingCategory.DECORATION),
    (22,   "Dead Crusader",            ThingCategory.DECORATION),
    # Architecture / structural
    (33,   "Tree Stub",                ThingCategory.DECORATION),
    (34,   "Candle",                   ThingCategory.DECORATION),
    (35,   "Candelabra",               ThingCategory.DECORATION),
    (43,   "Outside Lamp",             ThingCategory.DECORATION),
    (44,   "Ruined Statue",            ThingCategory.DECORATION),
    (45,   "Piston",                   ThingCategory.DECORATION),
    (46,   "Pole Lantern",             ThingCategory.DECORATION),
    (47,   "Large Torch",              ThingCategory.DECORATION),
    (48,   "Techno Pillar",            ThingCategory.DECORATION),
    (50,   "Huge Torch",               ThingCategory.DECORATION),
    (51,   "Palm Tree",                ThingCategory.DECORATION),
    (53,   "Water Drip",               ThingCategory.DECORATION),
    (54,   "Aztec Pillar",             ThingCategory.DECORATION),
    (55,   "Aztec Pillar (damaged)",   ThingCategory.DECORATION),
    (56,   "Aztec Pillar (ruined)",    ThingCategory.DECORATION),
    (57,   "Huge Tech Pillar",         ThingCategory.DECORATION),
    (60,   "Short Bush",               ThingCategory.DECORATION),
    (62,   "Tall Bush",                ThingCategory.DECORATION),
    (63,   "Chimney Stack",            ThingCategory.DECORATION),
    (69,   "Barricade Column",         ThingCategory.DECORATION),
    (70,   "Burning Barrel",           ThingCategory.DECORATION),
    (82,   "Wooden Barrel",            ThingCategory.DECORATION),
    (94,   "Explosive Barrel",         ThingCategory.DECORATION),
    (95,   "Silver Fluorescent",       ThingCategory.DECORATION),
    (96,   "Brown Fluorescent",        ThingCategory.DECORATION),
    (97,   "Gold Fluorescent",         ThingCategory.DECORATION),
    (98,   "Large Stalactite",         ThingCategory.DECORATION),
    (99,   "Rock (1)",                 ThingCategory.DECORATION),
    (100,  "Rock (2)",                 ThingCategory.DECORATION),
    (101,  "Rock (3)",                 ThingCategory.DECORATION),
    (102,  "Rock (4)",                 ThingCategory.DECORATION),
    (103,  "Water Drop on Floor",      ThingCategory.DECORATION),
    (104,  "Waterfall Splash",         ThingCategory.DECORATION),
    (105,  "Burning Bowl",             ThingCategory.DECORATION),
    (106,  "Burning Brazier",          ThingCategory.DECORATION),
    (107,  "Small Torch (lit)",        ThingCategory.DECORATION),
    (108,  "Small Torch (unlit)",      ThingCategory.DECORATION),
    (109,  "Ceiling Chain",            ThingCategory.DECORATION),
    (110,  "Statue",                   ThingCategory.DECORATION),
    (111,  "Medium Torch",             ThingCategory.DECORATION),
    (112,  "Water Fountain",           ThingCategory.DECORATION),
    (113,  "Hearts in Tank",           ThingCategory.DECORATION),
    (159,  "Cave Pillar Top",          ThingCategory.DECORATION),
    (160,  "Large Stalagmite",         ThingCategory.DECORATION),
    (161,  "Small Stalactite",         ThingCategory.DECORATION),
    (162,  "Cave Pillar Bottom",       ThingCategory.DECORATION),
    (164,  "Mug",                      ThingCategory.DECORATION),
    (165,  "Pot",                      ThingCategory.DECORATION),
    (182,  "Computer",                 ThingCategory.DECORATION),
    (188,  "Pitcher",                  ThingCategory.DECORATION),
    (189,  "Stool",                    ThingCategory.DECORATION),
    (190,  "Metal Pot",                ThingCategory.DECORATION),
    (191,  "Tub",                      ThingCategory.DECORATION),
    (194,  "Anvil",                    ThingCategory.DECORATION),
    (196,  "Tech Lamp (silver)",       ThingCategory.DECORATION),
    (197,  "Tech Lamp (brass)",        ThingCategory.DECORATION),
    (198,  "Entity Pod",               ThingCategory.DECORATION),
    (202,  "Big Tree",                 ThingCategory.DECORATION),
    (203,  "Potted Tree",              ThingCategory.DECORATION),
    (204,  "Kneeling Guy",             ThingCategory.DECORATION),
    (205,  "Offering Chalice",         ThingCategory.DECORATION),
    (208,  "Target Practice",          ThingCategory.DECORATION),
    (209,  "Tank (1)",                 ThingCategory.DECORATION),
    (210,  "Tank (2)",                 ThingCategory.DECORATION),
    (211,  "Tank (3)",                 ThingCategory.DECORATION),
    (212,  "Sacrificed Guy",           ThingCategory.DECORATION),
    (213,  "Tank (4)",                 ThingCategory.DECORATION),
    (214,  "Tank (5)",                 ThingCategory.DECORATION),
    (215,  "Stick in Water",           ThingCategory.DECORATION),
    (216,  "Sigil Banner",             ThingCategory.DECORATION),
    (221,  "Alien Bubble Column",      ThingCategory.DECORATION),
    (222,  "Alien Floor Bubble",       ThingCategory.DECORATION),
    (223,  "Alien Ceiling Bubble",     ThingCategory.DECORATION),
    (224,  "Alien Asp Climber",        ThingCategory.DECORATION),
    (225,  "Alien Spider Light",       ThingCategory.DECORATION),
    (227,  "Alien Power Pillar",       ThingCategory.DECORATION),
    (229,  "Tank (6)",                 ThingCategory.DECORATION),
    # Rubble
    (29,   "Rubble (1)",               ThingCategory.DECORATION),
    (30,   "Rubble (2)",               ThingCategory.DECORATION),
    (31,   "Rubble (3)",               ThingCategory.DECORATION),
    (32,   "Rubble (4)",               ThingCategory.DECORATION),
    (36,   "Rubble (5)",               ThingCategory.DECORATION),
    (37,   "Rubble (6)",               ThingCategory.DECORATION),
    (41,   "Rubble (7)",               ThingCategory.DECORATION),
    (42,   "Rubble (8)",               ThingCategory.DECORATION),
    # Alien environment
    (198,  "Entity Pod",               ThingCategory.DECORATION),
    (26,   "Entity Nest",              ThingCategory.DECORATION),
    (27,   "Ceiling Turret",           ThingCategory.DECORATION),
    (10,   "Teleporter Beacon",        ThingCategory.DECORATION),
    (91,   "Severed Hand",             ThingCategory.DECORATION),
    (24,   "Cage Light",               ThingCategory.DECORATION),
    (28,   "Cage Light",               ThingCategory.DECORATION),
]

THING_TYPES: dict[int, tuple[str, ThingCategory]] = {row[0]: (row[1], row[2]) for row in _TABLE}

# Thing type IDs that have no visible sprite — invisible gameplay markers.
# Type 14 = Teleport Landing (same convention as Doom).
# Type 25 = ForceFieldGuard (uses TNT1 = null sprite, invisible force field).
# Type 170 = ZombieSpawner (invisible spawner; only its children are visible).
# Type 23 = TeleportSwirl (animated fog, barely visible — omitted for now).
INVISIBLE_TYPES: frozenset[int] = frozenset({
    14,   # Teleport Landing
    23,   # Teleport Swirl
    25,   # Force Field Guard (null sprite)
    170,  # Zombie Spawner (invisible)
    9001, 9002, 9003, 9004, 9005,  # DM-style spawn markers
})

_SPRITE_PREFIXES: dict[int, str] = {
    # Player starts
    1: "PLAY", 2: "PLAY", 3: "PLAY", 4: "PLAY",
    5: "PLAY", 6: "PLAY", 7: "PLAY", 8: "PLAY",
    118: "PLAY", 119: "PLAY", 120: "PLAY", 121: "PLAY",
    122: "PLAY", 123: "PLAY", 124: "PLAY", 125: "PLAY",
    126: "PLAY", 127: "PLAY",
    # Acolytes
    3002: "AGRD", 58: "AGRD", 142: "AGRD", 143: "AGRD",
    146: "AGRD", 147: "AGRD", 148: "AGRD", 201: "AGRD",
    231: "AGRD", 232: "AGRD",
    # Peasants
    3004: "PEAS", 65: "PEAS", 66: "PEAS", 67: "PEAS",
    130: "PEAS", 131: "PEAS", 132: "PEAS", 133: "PEAS",
    134: "PEAS", 135: "PEAS", 136: "PEAS", 137: "PEAS",
    172: "PEAS", 173: "PEAS", 174: "PEAS", 175: "PEAS",
    176: "PEAS", 177: "PEAS", 178: "PEAS", 179: "PEAS",
    180: "PEAS", 181: "PEAS",
    169: "PEAS",  # Zombie
    # Rebels
    9: "HMN1", 144: "HMN1", 145: "HMN1",
    149: "HMN1", 150: "HMN1", 151: "HMN1",
    # Beggars
    141: "BEGR", 155: "BEGR", 156: "BEGR", 157: "BEGR", 158: "BEGR",
    # Robots
    3001: "ROB1",  # Reaver
    3005: "ROB2",  # Crusader
    16:   "ROB3",  # Inquisitor
    3006: "SEWR",  # Sentinel
    3003: "PGRD",  # Templar
    186:  "STLK",  # Stalker (note: different from Hexen Stalker SSPT)
    187:  "MLDR",  # Bishop
    # Alien / spectral
    129: "ALN1", 75: "ALN1", 76: "ALN1", 167: "ALN1", 168: "ALN1",
    128: "MNAL",  # EntityBoss
    # Bosses
    12:  "PRST",   # Loremaster
    71:  "PRGR",   # Programmer
    199: "ORCL",   # Oracle
    85:  "RATT",   # Rat Buddy
    # Merchants / NPCs
    64:  "LEAD",   # Macil1
    200: "LEAD",   # Macil2
    72:  "MRST",   # Bar Keeper
    73:  "MRST",   # Armorer
    74:  "MRST",   # Medic
    116: "MRST",   # Weapon Smith
    117: "CRAB",   # Surgery Crab
    # Weapons
    2001: "CBOW",  # Crossbow
    2002: "RIFL",  # Assault Rifle
    2006: "RIFL",  # Assault Rifle (standing)
    2003: "MMIS",  # Mini Missile Launcher
    2004: "TRPD",  # Mauler
    2005: "FLAM",  # Flame Thrower
    154:  "GRND",  # Grenade Launcher
    # Sigil (use pickup sprite SIGL)
    77: "SIGL", 78: "SIGL", 79: "SIGL", 80: "SIGL", 81: "SIGL",
    # Ammo
    11:   "BLIT",  # Clip of Bullets (Strife type 11 = ammo, not DM start)
    2007: "BLIT",  # Clip of Bullets
    2048: "BBOX",  # Box of Bullets
    17:   "CPAC",  # Energy Pack
    2047: "BRY1",  # Energy Pod
    2010: "MSSL",  # Mini Missiles
    2046: "ROKT",  # Crate of Missiles
    152:  "GRN1",  # HE Grenade Rounds
    153:  "GRN2",  # Phosphorus Grenade Rounds
    114:  "XQRL",  # Electric Bolts
    115:  "PQRL",  # Poison Bolts
    183:  "BKPK",  # Ammo Satchel
    # Health
    2011: "STMP",  # Med Patch
    2012: "MDKT",  # Medical Kit
    83:   "FULL",  # Surgery Kit
    2014: "WATR",  # Water Bottle
    # Armor
    2018: "ARM1",  # Leather Armor (ARM1 used in Strife too)
    2019: "ARM2",  # Metal Armor
    # Power-ups
    2024: "SHD1",  # Shadow Armor
    2025: "MASK",  # Environmental Suit
    2026: "PMAP",  # Strife Map
    2027: "PMUP",  # Scanner
    2028: "LITE",  # Light Globe
    207:  "TARG",  # Targeter
    206:  "COMM",  # Communicator
    90:   "UNIF",  # Guard Uniform
    52:   "OFIC",  # Officer's Uniform
    # Keys
    38:  "KY2S",  # Silver Key
    39:  "KY3B",  # Brass Key
    40:  "KY1G",  # Gold Key
    61:  "ORAC",  # Oracle Key
    86:  "FUBR",  # Order Key
    166: "WARE",  # Warehouse Key
    184: "CRD1",  # ID Badge
    185: "TPAS",  # Passcard
    192: "RCRY",  # Red Crystal Key
    193: "BCRY",  # Blue Crystal Key
    195: "CHAP",  # Chapel Key
    230: "FUSL",  # Base Key
    233: "BLTK",  # Mauler Key
    234: "PROC",  # Factory Key
    235: "MINE",  # Mine Key
    236: "GOID",  # Core Key
    13:  "CRD2",  # ID Card
    # Currency
    93:  "COIN",
    138: "COIN",
    139: "COIN",
    140: "COIN",
    # Miscellaneous items
    92:  "ANKH",  # Power Crystal
    59:  "XPRK",  # Degning Ore
    220: "COUP",  # Power Coupling
    # Decorations
    15:  "PLAY",  # Dead Player
    18:  "PEAS",  # Dead Peasant
    19:  "HMN1",  # Dead Rebel
    20:  "ROB1",  # Dead Reaver
    21:  "AGRD",  # Dead Acolyte
    33:  "TRE1",  # Tree Stub
    34:  "CNDL",  # Candle
    43:  "LAMP",  # Outside Lamp
    44:  "DSTA",  # Ruined Statue
    45:  "PSTN",  # Piston
    46:  "LANT",  # Pole Lantern
    47:  "LMPC",  # Large Torch
    48:  "MONI",  # Techno Pillar
    50:  "LOGS",  # Huge Torch
    51:  "TREE",  # Palm Tree
    53:  "DRIP",  # Water Drip
    54:  "STEL",  # Aztec Pillar
    55:  "STLA",  # Aztec Pillar (damaged)
    56:  "STLE",  # Aztec Pillar (ruined)
    57:  "HUGE",  # Huge Tech Pillar
    60:  "BUSH",  # Short Bush
    62:  "BUSH",  # Tall Bush (reuse)
    63:  "STAK",  # Chimney Stack
    69:  "BARL",  # Barricade Column
    70:  "BARL",  # Burning Barrel
    82:  "BARW",  # Wooden Barrel
    94:  "BART",  # Explosive Barrel
    95:  "LITS",  # Silver Fluorescent
    96:  "LITB",  # Brown Fluorescent
    97:  "LITG",  # Gold Fluorescent
    98:  "STLG",  # Large Stalactite
    99:  "ROK1", 100: "ROK2", 101: "ROK3", 102: "ROK4",
    104: "SPLH",  # Waterfall Splash
    105: "BOWL",  # Burning Bowl
    106: "BRAZ",  # Burning Brazier
    107: "TRCH",  # Small Torch (lit)
    108: "TRCH",  # Small Torch (unlit)
    109: "CHAN",  # Ceiling Chain
    110: "STAT",  # Statue
    111: "LTRH",  # Medium Torch
    113: "HERT",  # Hearts in Tank
    164: "MUGG",  # Mug
    165: "POT1",  # Pot
    189: "STOL",  # Stool
    191: "TUB1",  # Tub
    194: "ANVL",  # Anvil
    198: "PODD",  # Entity Pod
    202: "TREE",  # Big Tree
    204: "NEAL",  # Kneeling Guy
    205: "RELC",  # Offering Chalice
    207: "TARG",  # Targeter
    209: "TNK1", 210: "TNK2", 211: "TNK3",
    213: "TNK4", 214: "TNK5", 229: "TNK6",
    212: "SACR",  # Sacrificed Guy
    216: "SBAN",  # Sigil Banner
    221: "BUBB",  # Alien Bubble Column
    222: "BUBF",  # Alien Floor Bubble
    223: "BUBC",  # Alien Ceiling Bubble
    224: "ASPR",  # Alien Asp Climber
    225: "SPDL",  # Alien Spider Light
    227: "APOW",  # Alien Power Pillar
    24:  "CAGE",  # Cage Light
    26:  "NEST",  # Entity Nest
    27:  "TURT",  # Ceiling Turret
    10:  "BEAC",  # Teleporter Beacon
    # Rubble
    29: "RUB1", 30: "RUB2", 31: "RUB3", 32: "RUB4",
    36: "RUB5", 37: "RUB6", 41: "RUB7", 42: "RUB8",
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
