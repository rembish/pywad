"""Boom/MBF/MBF21 extended linedef and sector definitions.

Boom introduced *generalized* linedef types: special_type values in the range
``0x2F80``-``0x7FFF`` encode action parameters (trigger, speed, target) in
bit-fields rather than using a lookup table.

This module provides:

- :class:`GeneralizedCategory` — which category of action (floor, ceiling, …)
- :class:`GeneralizedTrigger` — what activates the linedef
- :class:`GeneralizedSpeed` — movement speed
- :class:`GeneralizedLinedef` — decoded result
- :func:`decode_generalized` — convert a raw ``special_type`` into the above
- :data:`DOOM_SECTOR_SPECIALS` — human-readable names for sector special numbers

Reference: Boom 1.3 source, ``p_spec.c`` ``EV_DoGenFloor`` et al., and the
Boom GENERALIZED linedef reference at:
<https://doomwiki.org/wiki/Generalized_linedefs>

MBF21 linedef flag additions are documented as :data:`MBF21_LINEDEF_FLAGS`.

Usage::

    from wadlib.lumps.boom import decode_generalized

    gen = decode_generalized(line.special_type)   # GeneralizedLinedef | None
    if gen:
        print(gen.category, gen.trigger)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

# ---------------------------------------------------------------------------
# Category ranges
# ---------------------------------------------------------------------------


class GeneralizedCategory(IntEnum):
    """Top-level category of a Boom generalized linedef action.

    Each value is the *inclusive lower bound* of the category's range.
    The next category's lower bound is the exclusive upper bound.
    """

    CRUSHER = 0x2F80
    STAIR = 0x3000
    LIFT = 0x3400
    LOCKED_DOOR = 0x3800
    DOOR = 0x3C00
    CEILING = 0x4000
    FLOOR = 0x6000


# Ordered list for range detection (highest first so we match the right bucket)
_CATEGORY_THRESHOLDS: list[tuple[int, GeneralizedCategory]] = sorted(
    [(cat.value, cat) for cat in GeneralizedCategory],
    reverse=True,
)


# ---------------------------------------------------------------------------
# Trigger types (bits 0-2)
# ---------------------------------------------------------------------------


class GeneralizedTrigger(IntEnum):
    """What activates a generalized linedef (bits 0-2 of ``special_type``)."""

    W1 = 0  # Walk-through, once
    WR = 1  # Walk-through, repeatable
    S1 = 2  # Switch (use), once
    SR = 3  # Switch (use), repeatable
    G1 = 4  # Gunfire (impact), once
    GR = 5  # Gunfire (impact), repeatable
    P1 = 6  # Push (use from any angle), once
    PR = 7  # Push (use from any angle), repeatable


# ---------------------------------------------------------------------------
# Speed (bits 3-4)
# ---------------------------------------------------------------------------


class GeneralizedSpeed(IntEnum):
    """Movement speed of the triggered surface (bits 3-4 of ``special_type``)."""

    SLOW = 0
    NORMAL = 1
    FAST = 2
    TURBO = 3


# ---------------------------------------------------------------------------
# Decoded result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GeneralizedLinedef:
    """Decoded representation of a Boom generalized linedef special.

    Attributes:
        category:  Which family of actions this linedef belongs to.
        trigger:   What kind of player/monster interaction activates it.
        speed:     Movement speed (for floor/ceiling/door/lift actions).
        subtype:   Raw value of bits 5 and above — category-specific sub-fields
                   (target height, change model, crush flag, etc.).
                   Callers who need the fine-grained breakdown can extract bits
                   from this field using the Boom source or DoomWiki reference.
    """

    category: GeneralizedCategory
    trigger: GeneralizedTrigger
    speed: GeneralizedSpeed
    subtype: int  # bits 5+, category-specific


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------


def decode_generalized(special_type: int) -> GeneralizedLinedef | None:
    """Decode a Boom generalized linedef special type.

    Returns a :class:`GeneralizedLinedef` when ``special_type >= 0x2F80``,
    otherwise returns ``None`` (vanilla or Hexen linedef).

    Args:
        special_type: The raw ``special_type`` field from a ``LineDefinition``.
    """
    if special_type < 0x2F80:
        return None

    # Determine category
    category: GeneralizedCategory | None = None
    for threshold, cat in _CATEGORY_THRESHOLDS:
        if special_type >= threshold:
            category = cat
            break

    if category is None:
        return None  # out of known range

    trigger = GeneralizedTrigger(special_type & 0x07)
    speed = GeneralizedSpeed((special_type >> 3) & 0x03)
    subtype = special_type >> 5

    return GeneralizedLinedef(
        category=category,
        trigger=trigger,
        speed=speed,
        subtype=subtype,
    )


# ---------------------------------------------------------------------------
# Sector special names
# ---------------------------------------------------------------------------

#: Human-readable names for vanilla Doom / Boom sector specials.
#: Values 0-17 are standard Doom; 32+ use Boom's bit-field encoding.
DOOM_SECTOR_SPECIALS: dict[int, str] = {
    0: "Normal",
    1: "Blink (random)",
    2: "Blink (0.5 s)",
    3: "Blink (1 s)",
    4: "Blink (0.5 s) + 20% damage",
    5: "10% damage + end level",
    7: "5% damage",
    8: "Oscillating light",
    9: "Secret",
    10: "Close door in 30 s",
    11: "20% damage + end level",
    12: "Blink (sync, 0.5 s)",
    13: "Blink (sync, 1 s)",
    14: "Open door in 300 s",
    16: "20% damage",
    17: "Fire flicker",
}


# ---------------------------------------------------------------------------
# MBF21 linedef flag additions
# ---------------------------------------------------------------------------

#: New linedef flag bits introduced by MBF21.
#: Bits 0-8 are standard Doom; bit 9 = PASSUSE in Boom.
#: MBF21 repurposes / extends bits 9-11.
MBF21_LINEDEF_FLAGS: dict[int, str] = {
    0x0200: "BLOCKLANDMONSTERS",  # bit 9 — block non-flying monsters
    0x0400: "BLOCKPLAYERS",  # bit 10 — block players
    0x0800: "BLOCKALL",  # bit 11 — block all actors
}
