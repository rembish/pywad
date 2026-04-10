"""Game-aware thing type dispatch.

Selects the correct per-game type table (Doom, Heretic, or Hexen) based on
WAD content, then delegates all type lookups to that table.

Usage::

    game = detect_game(wad)
    cat  = get_category(thing.type, game)
    pfx  = get_sprite_prefix(thing.type, game)

Game detection heuristics (in priority order):

1. Hexen  — things have action / arg0 / tid / z fields (Hexen THINGS format)
2. Heretic — WAD sprite namespace contains the ``IMPX`` prefix (Fire Gargoyle),
             which is unique to Heretic
3. Doom   — default
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from . import doom_types, heretic_types, hexen_types
from .doom_types import ThingCategory

if TYPE_CHECKING:
    from .wad import WadFile

__all__ = [
    "GameType",
    "ThingCategory",  # re-export for convenience
    "detect_game",
    "get_category",
    "get_invisible_types",
    "get_name",
    "get_sprite_prefix",
    "get_sprite_suffixes",
]


class GameType(Enum):
    DOOM = "doom"
    HERETIC = "heretic"
    HEXEN = "hexen"


_MODULES = {
    GameType.DOOM: doom_types,
    GameType.HERETIC: heretic_types,
    GameType.HEXEN: hexen_types,
}


def detect_game(wad: WadFile) -> GameType:
    """Inspect *wad* and return the most likely GameType.

    Uses two fast heuristics that don't require loading map data:
    - Hexen: things in any map have ``arg0`` (the Hexen THINGS lump format adds
      extra bytes per thing).
    - Heretic: the WAD sprite namespace contains the ``IMPX`` prefix, which
      does not appear in Doom or Hexen WADs.
    - Doom: default when neither marker is found.
    """
    # Hexen detection: check the first map that has things
    for m in wad.maps:
        if m.things:
            if hasattr(m.things[0], "arg0"):
                return GameType.HEXEN
            break  # Doom/Heretic format confirmed; no need to check further maps

    # Heretic detection: IMPX sprite exists only in Heretic
    if any(name.startswith("IMPX") for name in wad.sprites):
        return GameType.HERETIC

    return GameType.DOOM


# ---------------------------------------------------------------------------
# Public dispatch API — mirrors the per-module function signatures
# ---------------------------------------------------------------------------

def get_name(type_id: int, game: GameType = GameType.DOOM) -> str:
    return _MODULES[game].get_name(type_id)


def get_category(type_id: int, game: GameType = GameType.DOOM) -> ThingCategory:
    return _MODULES[game].get_category(type_id)


def get_sprite_prefix(type_id: int, game: GameType = GameType.DOOM) -> str | None:
    return _MODULES[game].get_sprite_prefix(type_id)


def get_sprite_suffixes(type_id: int, game: GameType = GameType.DOOM) -> tuple[str, ...]:
    return _MODULES[game].get_sprite_suffixes(type_id)


def get_invisible_types(game: GameType = GameType.DOOM) -> frozenset[int]:
    return _MODULES[game].INVISIBLE_TYPES
