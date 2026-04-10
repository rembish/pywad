"""Tests for SECTORS lump."""

from struct import calcsize

from wadlib.lumps.sectors import SECTOR_FORMAT, Sector
from wadlib.wad import WadFile


def test_sector_format_size() -> None:
    assert calcsize(SECTOR_FORMAT) == 26


def test_sectors_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].sectors is not None


def test_sectors_non_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.maps[0].sectors) > 0


def test_sector_is_sector(freedoom1_wad: WadFile) -> None:
    s = freedoom1_wad.maps[0].sectors[0]
    assert isinstance(s, Sector)


def test_sector_textures_are_strings(freedoom1_wad: WadFile) -> None:
    s = freedoom1_wad.maps[0].sectors[0]
    assert isinstance(s.floor_texture, str)
    assert isinstance(s.ceiling_texture, str)


def test_sector_light_level_in_range(freedoom1_wad: WadFile) -> None:
    for sec in freedoom1_wad.maps[0].sectors:
        assert 0 <= sec.light_level <= 255


def test_sectors_doom2(freedoom2_wad: WadFile) -> None:
    assert freedoom2_wad.maps[0].sectors is not None
    assert len(freedoom2_wad.maps[0].sectors) > 0
