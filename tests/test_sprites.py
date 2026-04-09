"""Tests for sprite lump enumeration."""

from wadlib.lumps.picture import Picture
from wadlib.wad import WadFile


def test_sprites_not_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.sprites) > 0


def test_sprites_values_are_picture(doom1_wad: WadFile) -> None:
    for pic in doom1_wad.sprites.values():
        assert isinstance(pic, Picture)


def test_get_sprite_returns_picture(doom1_wad: WadFile) -> None:
    name = next(iter(doom1_wad.sprites))
    pic = doom1_wad.get_sprite(name)
    assert isinstance(pic, Picture)


def test_get_sprite_case_insensitive(doom1_wad: WadFile) -> None:
    name = next(iter(doom1_wad.sprites))
    assert doom1_wad.get_sprite(name.lower()) is not None


def test_get_sprite_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_sprite("NOEXIST") is None
