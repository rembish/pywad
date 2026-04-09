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
]

THING_TYPES: dict[int, tuple[str, ThingCategory]] = {row[0]: (row[1], row[2]) for row in _TABLE}


def get_name(type_id: int) -> str:
    """Return the display name for a thing type, or 'Unknown (#id)'."""
    entry = THING_TYPES.get(type_id)
    return entry[0] if entry else f"Unknown (#{type_id})"


def get_category(type_id: int) -> ThingCategory:
    """Return the ThingCategory for a thing type, or UNKNOWN."""
    entry = THING_TYPES.get(type_id)
    return entry[1] if entry else ThingCategory.UNKNOWN
