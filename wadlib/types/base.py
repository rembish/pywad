"""Shared types and base class for per-game thing type modules."""

from __future__ import annotations

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


_DEFAULT_SPRITE_SUFFIXES: tuple[str, ...] = ("A0", "A1")


class GameModule:
    """Per-game thing type catalog — names, categories, and sprite data.

    Each game (Doom, Heretic, Hexen, Strife) instantiates one of these with
    its own data tables.  The dispatch layer in ``wadlib.types`` delegates
    lookups to the correct instance based on detected game type.
    """

    def __init__(
        self,
        *,
        thing_types: dict[int, tuple[str, ThingCategory]],
        invisible_types: frozenset[int],
        sprite_prefixes: dict[int, str],
        sprite_suffix_overrides: dict[int, tuple[str, ...]] | None = None,
    ) -> None:
        self.thing_types = thing_types
        self.invisible_types = invisible_types
        self.sprite_prefixes = sprite_prefixes
        self._suffix_overrides = sprite_suffix_overrides or {}

    def get_name(self, type_id: int) -> str:
        entry = self.thing_types.get(type_id)
        return entry[0] if entry else f"Unknown (#{type_id})"

    def get_category(self, type_id: int) -> ThingCategory:
        entry = self.thing_types.get(type_id)
        return entry[1] if entry else ThingCategory.UNKNOWN

    def get_sprite_prefix(self, type_id: int) -> str | None:
        return self.sprite_prefixes.get(type_id)

    def get_sprite_suffixes(self, type_id: int) -> tuple[str, ...]:
        return self._suffix_overrides.get(type_id, _DEFAULT_SPRITE_SUFFIXES)
