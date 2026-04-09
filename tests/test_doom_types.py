"""Tests for the Doom thing type catalog."""

from wadlib.doom_types import ThingCategory, get_category, get_name


def test_player_start_category() -> None:
    assert get_category(1) == ThingCategory.PLAYER


def test_monster_category() -> None:
    assert get_category(3004) == ThingCategory.MONSTER  # Zombieman
    assert get_category(3001) == ThingCategory.MONSTER  # Imp
    assert get_category(16) == ThingCategory.MONSTER  # Cyberdemon


def test_weapon_category() -> None:
    assert get_category(2001) == ThingCategory.WEAPON  # Shotgun
    assert get_category(2006) == ThingCategory.WEAPON  # BFG


def test_ammo_category() -> None:
    assert get_category(2007) == ThingCategory.AMMO  # Clip


def test_health_category() -> None:
    assert get_category(2011) == ThingCategory.HEALTH  # Stimpack
    assert get_category(2012) == ThingCategory.HEALTH  # Medikit


def test_armor_category() -> None:
    assert get_category(2018) == ThingCategory.ARMOR  # Green armor


def test_key_category() -> None:
    assert get_category(5) == ThingCategory.KEY  # Blue keycard
    assert get_category(38) == ThingCategory.KEY  # Red skull key


def test_powerup_category() -> None:
    assert get_category(2023) == ThingCategory.POWERUP  # Berserk


def test_decoration_category() -> None:
    assert get_category(10) == ThingCategory.DECORATION  # Bloody mess


def test_unknown_category() -> None:
    assert get_category(9999) == ThingCategory.UNKNOWN


def test_get_name_known() -> None:
    assert get_name(1) == "Player 1 Start"
    assert get_name(3001) == "Imp"


def test_get_name_unknown() -> None:
    name = get_name(9999)
    assert "9999" in name
    assert "Unknown" in name


def test_thing_category_values_are_strings() -> None:
    for cat in ThingCategory:
        assert isinstance(cat.value, str)
