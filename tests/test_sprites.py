"""Tests for sprite lump enumeration."""

from wadlib.lumps.picture import Picture
from wadlib.wad import WadFile


def test_sprites_not_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.sprites) > 0


def test_sprites_values_are_picture(freedoom1_wad: WadFile) -> None:
    for pic in freedoom1_wad.sprites.values():
        assert isinstance(pic, Picture)


def test_get_sprite_returns_picture(freedoom1_wad: WadFile) -> None:
    name = next(iter(freedoom1_wad.sprites))
    pic = freedoom1_wad.get_sprite(name)
    assert isinstance(pic, Picture)


def test_get_sprite_case_insensitive(freedoom1_wad: WadFile) -> None:
    name = next(iter(freedoom1_wad.sprites))
    assert freedoom1_wad.get_sprite(name.lower()) is not None


def test_get_sprite_missing_returns_none(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_sprite("NOEXIST") is None
