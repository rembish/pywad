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

from . import doom_types, heretic_types, hexen_types, strife_types
from .doom_types import ThingCategory
from .lumps.dehacked import DehackedThing

if TYPE_CHECKING:
    from .wad import WadFile

__all__ = [
    "DehackedThing",
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
    STRIFE = "strife"


_MODULES = {
    GameType.DOOM: doom_types,
    GameType.HERETIC: heretic_types,
    GameType.HEXEN: hexen_types,
    GameType.STRIFE: strife_types,
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
    # Hexen detection: check the first map that has things
    for m in wad.maps:
        if m.things:
            if hasattr(m.things[0], "arg0"):
                return GameType.HEXEN
            break  # Doom/Heretic/Strife format confirmed; no need to check further maps

    # Strife detection: AGRD sprite (Acolyte Guard) is unique to Strife
    if any(name.startswith("AGRD") for name in wad.sprites):
        return GameType.STRIFE

    # Heretic detection: IMPX sprite exists only in Heretic
    if any(name.startswith("IMPX") for name in wad.sprites):
        return GameType.HERETIC

    return GameType.DOOM


# ---------------------------------------------------------------------------
# Public dispatch API — mirrors the per-module function signatures
# ---------------------------------------------------------------------------

# Optional DEHACKED overlay: dict[type_id, DehackedThing] from wad.dehacked.things
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
    deh: _DehOverlay = None,
) -> str | None:
    # DEHACKED doesn't give us a 4-letter sprite name without full frame-table
    # cross-reference; fall through to the standard table so we at least get
    # the sprite for redefined stock types.
    return _MODULES[game].get_sprite_prefix(type_id)


def get_sprite_suffixes(
    type_id: int,
    game: GameType = GameType.DOOM,
    deh: _DehOverlay = None,
) -> tuple[str, ...]:
    return _MODULES[game].get_sprite_suffixes(type_id)


def get_invisible_types(game: GameType = GameType.DOOM) -> frozenset[int]:
    return _MODULES[game].INVISIBLE_TYPES
