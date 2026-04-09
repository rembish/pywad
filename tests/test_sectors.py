"""Tests for SECTORS lump."""

from struct import calcsize

from pywad.lumps.sectors import SECTOR_FORMAT, Sector
from pywad.wad import WadFile


def test_sector_format_size() -> None:
    assert calcsize(SECTOR_FORMAT) == 26


def test_sectors_attached(doom1_wad: WadFile) -> None:
    assert doom1_wad.maps[0].sectors is not None


def test_sectors_non_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.maps[0].sectors) > 0


def test_sector_is_sector(doom1_wad: WadFile) -> None:
    s = doom1_wad.maps[0].sectors[0]
    assert isinstance(s, Sector)


def test_sector_textures_are_strings(doom1_wad: WadFile) -> None:
    s = doom1_wad.maps[0].sectors[0]
    assert isinstance(s.floor_texture, str)
    assert isinstance(s.ceiling_texture, str)


def test_sector_light_level_in_range(doom1_wad: WadFile) -> None:
    for sec in doom1_wad.maps[0].sectors:
        assert 0 <= sec.light_level <= 255


def test_sectors_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.maps[0].sectors is not None
    assert len(doom2_wad.maps[0].sectors) > 0
