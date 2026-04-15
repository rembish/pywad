"""Tests for Boom generalized linedef decoder and sector specials."""

from __future__ import annotations

import pytest

from wadlib.lumps.boom import (
    DOOM_SECTOR_SPECIALS,
    MBF21_LINEDEF_FLAGS,
    GeneralizedCategory,
    GeneralizedLinedef,
    GeneralizedSpeed,
    GeneralizedTrigger,
    decode_generalized,
)
from wadlib.lumps.lines import LineDefinition
from wadlib.lumps.sectors import Sector

# ---------------------------------------------------------------------------
# decode_generalized — None for vanilla specials
# ---------------------------------------------------------------------------


def test_vanilla_special_returns_none() -> None:
    assert decode_generalized(0) is None


def test_vanilla_door_open_returns_none() -> None:
    assert decode_generalized(1) is None


def test_upper_vanilla_bound_returns_none() -> None:
    assert decode_generalized(0x2F7F) is None


# ---------------------------------------------------------------------------
# decode_generalized — category detection
# ---------------------------------------------------------------------------


def test_crusher_category() -> None:
    gen = decode_generalized(0x2F80)
    assert gen is not None
    assert gen.category == GeneralizedCategory.CRUSHER


def test_stair_category() -> None:
    gen = decode_generalized(0x3000)
    assert gen is not None
    assert gen.category == GeneralizedCategory.STAIR


def test_lift_category() -> None:
    gen = decode_generalized(0x3400)
    assert gen is not None
    assert gen.category == GeneralizedCategory.LIFT


def test_locked_door_category() -> None:
    gen = decode_generalized(0x3800)
    assert gen is not None
    assert gen.category == GeneralizedCategory.LOCKED_DOOR


def test_door_category() -> None:
    gen = decode_generalized(0x3C00)
    assert gen is not None
    assert gen.category == GeneralizedCategory.DOOR


def test_ceiling_category() -> None:
    gen = decode_generalized(0x4000)
    assert gen is not None
    assert gen.category == GeneralizedCategory.CEILING


def test_floor_category() -> None:
    gen = decode_generalized(0x6000)
    assert gen is not None
    assert gen.category == GeneralizedCategory.FLOOR


def test_floor_category_upper_range() -> None:
    gen = decode_generalized(0x7FFF)
    assert gen is not None
    assert gen.category == GeneralizedCategory.FLOOR


# ---------------------------------------------------------------------------
# decode_generalized — trigger decoding (bits 0-2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "trigger_bits, expected",
    [
        (0, GeneralizedTrigger.W1),
        (1, GeneralizedTrigger.WR),
        (2, GeneralizedTrigger.S1),
        (3, GeneralizedTrigger.SR),
        (4, GeneralizedTrigger.G1),
        (5, GeneralizedTrigger.GR),
        (6, GeneralizedTrigger.P1),
        (7, GeneralizedTrigger.PR),
    ],
)
def test_trigger_decoding(trigger_bits: int, expected: GeneralizedTrigger) -> None:
    # Use floor category base (0x6000) + trigger bits
    special = 0x6000 | trigger_bits
    gen = decode_generalized(special)
    assert gen is not None
    assert gen.trigger == expected


# ---------------------------------------------------------------------------
# decode_generalized — speed decoding (bits 3-4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "speed_bits, expected",
    [
        (0 << 3, GeneralizedSpeed.SLOW),
        (1 << 3, GeneralizedSpeed.NORMAL),
        (2 << 3, GeneralizedSpeed.FAST),
        (3 << 3, GeneralizedSpeed.TURBO),
    ],
)
def test_speed_decoding(speed_bits: int, expected: GeneralizedSpeed) -> None:
    special = 0x6000 | speed_bits
    gen = decode_generalized(special)
    assert gen is not None
    assert gen.speed == expected


# ---------------------------------------------------------------------------
# decode_generalized — combined trigger + speed
# ---------------------------------------------------------------------------


def test_combined_trigger_speed() -> None:
    # W1 (0) + FAST (2<<3 = 0x10) = 0x10 | 0 = 0x10; floor base 0x6000
    special = 0x6000 | (2 << 3) | 0  # FAST + W1
    gen = decode_generalized(special)
    assert gen is not None
    assert gen.trigger == GeneralizedTrigger.W1
    assert gen.speed == GeneralizedSpeed.FAST


def test_sr_turbo_floor() -> None:
    # SR (3) + TURBO (3<<3=0x18) = 0x1B; floor = 0x6000
    special = 0x6000 | (3 << 3) | 3
    gen = decode_generalized(special)
    assert gen is not None
    assert gen.trigger == GeneralizedTrigger.SR
    assert gen.speed == GeneralizedSpeed.TURBO


# ---------------------------------------------------------------------------
# decode_generalized — subtype field (bits 5+)
# ---------------------------------------------------------------------------


def test_subtype_field_is_bits_5_and_above() -> None:
    # special = 0x6000 | 0b11100000 = 0x6000 | 0xE0
    # bits 5-6-7 = 0b111, bits 0-4 = 0
    special = 0x6000 | 0xE0
    gen = decode_generalized(special)
    assert gen is not None
    assert gen.subtype == ((0x6000 | 0xE0) >> 5)


def test_subtype_excludes_trigger_and_speed() -> None:
    special = 0x6000 | 0xFF  # all low bits set
    gen = decode_generalized(special)
    assert gen is not None
    # trigger = bits 0-2 = 7 (PR), speed = bits 3-4 = 3 (TURBO)
    # subtype = (0x6000 | 0xFF) >> 5
    assert gen.trigger == GeneralizedTrigger.PR
    assert gen.speed == GeneralizedSpeed.TURBO
    assert gen.subtype == (special >> 5)


# ---------------------------------------------------------------------------
# decode_generalized — return type
# ---------------------------------------------------------------------------


def test_returns_generalized_linedef_instance() -> None:
    gen = decode_generalized(0x6000)
    assert isinstance(gen, GeneralizedLinedef)


def test_generalized_linedef_is_frozen() -> None:
    gen = decode_generalized(0x6000)
    assert gen is not None
    with pytest.raises(AttributeError):
        gen.category = GeneralizedCategory.FLOOR  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LineDefinition.generalized property
# ---------------------------------------------------------------------------


def _make_linedef(special_type: int) -> LineDefinition:
    return LineDefinition(
        start_vertex=0,
        finish_vertex=1,
        flags=0,
        special_type=special_type,
        sector_tag=0,
        right_sidedef=0,
        left_sidedef=-1,
    )


def test_linedef_generalized_none_for_vanilla() -> None:
    line = _make_linedef(0)
    assert line.generalized is None


def test_linedef_generalized_returns_decoded() -> None:
    line = _make_linedef(0x6000)
    gen = line.generalized
    assert gen is not None
    assert gen.category == GeneralizedCategory.FLOOR


def test_linedef_generalized_trigger_decoded() -> None:
    line = _make_linedef(0x6001)  # WR trigger
    gen = line.generalized
    assert gen is not None
    assert gen.trigger == GeneralizedTrigger.WR


# ---------------------------------------------------------------------------
# DOOM_SECTOR_SPECIALS
# ---------------------------------------------------------------------------


def test_sector_special_0_is_normal() -> None:
    assert DOOM_SECTOR_SPECIALS[0] == "Normal"


def test_sector_special_9_is_secret() -> None:
    assert DOOM_SECTOR_SPECIALS[9] == "Secret"


def test_sector_special_5_has_end_level() -> None:
    assert "end level" in DOOM_SECTOR_SPECIALS[5].lower()


def test_sector_special_dict_covers_all_vanilla() -> None:
    vanilla_ids = {0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17}
    assert vanilla_ids.issubset(DOOM_SECTOR_SPECIALS.keys())


# ---------------------------------------------------------------------------
# Sector.special_name property
# ---------------------------------------------------------------------------


def _make_sector(special: int) -> Sector:
    return Sector(
        floor_height=0,
        ceiling_height=128,
        floor_texture="FLOOR4_8",
        ceiling_texture="CEIL3_5",
        light_level=160,
        special=special,
        tag=0,
    )


def test_sector_special_name_normal() -> None:
    assert _make_sector(0).special_name == "Normal"


def test_sector_special_name_secret() -> None:
    assert _make_sector(9).special_name == "Secret"


def test_sector_special_name_unknown() -> None:
    # 99 is not a defined special
    name = _make_sector(99).special_name
    assert "99" in name


# ---------------------------------------------------------------------------
# MBF21_LINEDEF_FLAGS
# ---------------------------------------------------------------------------


def test_mbf21_flags_has_three_entries() -> None:
    assert len(MBF21_LINEDEF_FLAGS) == 3


def test_mbf21_blocklandmonsters_bit() -> None:
    assert 0x0200 in MBF21_LINEDEF_FLAGS
    assert "BLOCK" in MBF21_LINEDEF_FLAGS[0x0200].upper()
