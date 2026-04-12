"""Game-aware thing type system.

Provides per-game thing type catalogs (names, categories, sprites) and
automatic game detection from WAD content.

Usage::

    from wadlib.types import detect_game, get_category, get_sprite_prefix

    game = detect_game(wad)
    cat  = get_category(thing.type, game)
    pfx  = get_sprite_prefix(thing.type, game)

Each game module (``doom``, ``heretic``, ``hexen``, ``strife``) is also
importable directly::

    from wadlib.types.doom import THING_TYPES, SPRITE_PREFIXES
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from . import doom, heretic, hexen, strife
from .base import GameModule, ThingCategory
from .dehacked import DehackedThing

if TYPE_CHECKING:
    from ..wad import WadFile

__all__ = [
    "DehackedThing",
    "GameType",
    "ThingCategory",
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
    STRIFE = "strife"


_MODULES: dict[GameType, GameModule] = {
    GameType.DOOM: doom.MODULE,
    GameType.HERETIC: heretic.MODULE,
    GameType.HEXEN: hexen.MODULE,
    GameType.STRIFE: strife.MODULE,
}


def detect_game(wad: WadFile) -> GameType:
    """Inspect *wad* and return the most likely GameType.

    Uses fast heuristics that don't require loading map data:
    - Hexen: things in any map have ``arg0`` (the Hexen THINGS lump format adds
      extra bytes per thing).
    - Strife: the WAD sprite namespace contains ``AGRD`` (Acolyte Guard), which
      is unique to Strife.
    - Heretic: the WAD sprite namespace contains the ``IMPX`` prefix, which
      does not appear in Doom, Hexen, or Strife WADs.
    - Doom: default when none of the above markers are found.
    """
    for m in wad.maps:
        if m.things:
            if hasattr(m.things[0], "arg0"):
                return GameType.HEXEN
            break

    if any(name.startswith("AGRD") for name in wad.sprites):
        return GameType.STRIFE

    if any(name.startswith("IMPX") for name in wad.sprites):
        return GameType.HERETIC

    return GameType.DOOM


# ---------------------------------------------------------------------------
# Public dispatch API
# ---------------------------------------------------------------------------

_DehOverlay = dict[int, DehackedThing] | None


def get_name(
    type_id: int,
    game: GameType = GameType.DOOM,
    deh: _DehOverlay = None,
) -> str:
    if deh and type_id in deh:
        name = deh[type_id].name
        return name if name else f"Unknown (#{type_id})"
    return _MODULES[game].get_name(type_id)


def get_category(
    type_id: int,
    game: GameType = GameType.DOOM,
    deh: _DehOverlay = None,
) -> ThingCategory:
    if deh and type_id in deh:
        thing = deh[type_id]
        if thing.is_monster:
            return ThingCategory.MONSTER
        if thing.is_item:
            return ThingCategory.POWERUP
        return ThingCategory.DECORATION
    return _MODULES[game].get_category(type_id)


def get_sprite_prefix(
    type_id: int,
    game: GameType = GameType.DOOM,
    _deh: _DehOverlay = None,
) -> str | None:
    return _MODULES[game].get_sprite_prefix(type_id)


def get_sprite_suffixes(
    type_id: int,
    game: GameType = GameType.DOOM,
    _deh: _DehOverlay = None,
) -> tuple[str, ...]:
    return _MODULES[game].get_sprite_suffixes(type_id)


def get_invisible_types(game: GameType = GameType.DOOM) -> frozenset[int]:
    return _MODULES[game].invisible_types
