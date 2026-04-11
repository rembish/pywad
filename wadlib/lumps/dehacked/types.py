"""Data classes for all DEHACKED block types."""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import MF_COUNTITEM, MF_COUNTKILL, STOCK_SPRITE_NAMES


@dataclass
class DehackedThing:
    """A Thing block from a DEHACKED patch."""

    index: int
    type_id: int | None = None
    name: str = ""
    bits: int = 0
    initial_frame: int | None = None
    hit_points: int | None = None
    speed: int | None = None
    width: int | None = None
    height: int | None = None
    mass: int | None = None
    missile_damage: int | None = None
    reaction_time: int | None = None
    pain_chance: int | None = None
    alert_sound: int | None = None
    attack_sound: int | None = None
    pain_sound: int | None = None
    death_sound: int | None = None
    action_sound: int | None = None
    props: dict[str, str] = field(default_factory=dict)

    @property
    def is_monster(self) -> bool:
        return bool(self.bits & MF_COUNTKILL)

    @property
    def is_item(self) -> bool:
        return bool(self.bits & MF_COUNTITEM)


@dataclass
class DehackedFrame:
    """A Frame/State block from a DEHACKED patch."""

    index: int
    name: str = ""
    sprite_number: int | None = None
    sprite_subnumber: int | None = None
    duration: int | None = None
    next_frame: int | None = None
    props: dict[str, str] = field(default_factory=dict)

    @property
    def sprite_name(self) -> str | None:
        """Resolve to a 4-char sprite prefix using the stock table, or None."""
        if self.sprite_number is None:
            return None
        if 0 <= self.sprite_number < len(STOCK_SPRITE_NAMES):
            return STOCK_SPRITE_NAMES[self.sprite_number]
        return None


@dataclass
class DehackedWeapon:
    """A Weapon block from a DEHACKED patch."""

    index: int
    name: str = ""
    ammo_type: int | None = None
    deselect_frame: int | None = None
    select_frame: int | None = None
    bobbing_frame: int | None = None
    shooting_frame: int | None = None
    firing_frame: int | None = None
    ammo_per_shot: int | None = None
    mbf21_bits: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedAmmo:
    """An Ammo block from a DEHACKED patch."""

    index: int
    name: str = ""
    max_ammo: int | None = None
    per_ammo: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedSound:
    """A Sound block from a DEHACKED patch."""

    index: int
    name: str = ""
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedMisc:
    """A Misc block from a DEHACKED patch (global game settings)."""

    index: int
    initial_health: int | None = None
    initial_bullets: int | None = None
    max_health: int | None = None
    max_armor: int | None = None
    green_armor_class: int | None = None
    blue_armor_class: int | None = None
    max_soulsphere: int | None = None
    soulsphere_health: int | None = None
    megasphere_health: int | None = None
    god_mode_health: int | None = None
    idfa_armor: int | None = None
    idfa_armor_class: int | None = None
    idkfa_armor: int | None = None
    idkfa_armor_class: int | None = None
    bfg_cells_per_shot: int | None = None
    monsters_infight: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedText:
    """A text replacement from a DEHACKED patch."""

    old_length: int
    new_length: int
    old_text: str
    new_text: str


@dataclass
class DehackedPatch:
    """Fully parsed DEHACKED patch with all block types."""

    doom_version: int | None = None
    patch_format: int | None = None
    all_things: dict[int, DehackedThing] = field(default_factory=dict)
    frames: dict[int, DehackedFrame] = field(default_factory=dict)
    weapons: dict[int, DehackedWeapon] = field(default_factory=dict)
    ammo: dict[int, DehackedAmmo] = field(default_factory=dict)
    sounds: dict[int, DehackedSound] = field(default_factory=dict)
    misc: dict[int, DehackedMisc] = field(default_factory=dict)
    texts: list[DehackedText] = field(default_factory=list)
    par_times: dict[str, int] = field(default_factory=dict)
    bex_strings: dict[str, str] = field(default_factory=dict)
    bex_codeptr: dict[int, str] = field(default_factory=dict)

    @property
    def things(self) -> dict[int, DehackedThing]:
        """Custom things only (those with an ID # = N DoomEd type)."""
        return {t.type_id: t for t in self.all_things.values() if t.type_id is not None}
