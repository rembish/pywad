"""Tests for SIDEDEFS lump."""

from wadlib.lumps.sidedefs import SideDef
from wadlib.wad import WadFile


def test_sidedefs_attached(doom1_wad: WadFile) -> None:
    assert doom1_wad.maps[0].sidedefs is not None


def test_sidedefs_non_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.maps[0].sidedefs) > 0


def test_sidedef_is_sidedef(doom1_wad: WadFile) -> None:
    s = doom1_wad.maps[0].sidedefs[0]
    assert isinstance(s, SideDef)


def test_sidedef_textures_are_strings(doom1_wad: WadFile) -> None:
    s = doom1_wad.maps[0].sidedefs[0]
    assert isinstance(s.upper_texture, str)
    assert isinstance(s.lower_texture, str)
    assert isinstance(s.middle_texture, str)


def test_sidedef_sector_index_non_negative(doom1_wad: WadFile) -> None:
    for sd in doom1_wad.maps[0].sidedefs:
        assert sd.sector >= 0


def test_sidedefs_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.maps[0].sidedefs is not None
    assert len(doom2_wad.maps[0].sidedefs) > 0


def test_sidedef_row_size() -> None:
    from struct import calcsize

    from wadlib.lumps.sidedefs import SIDEDEF_FORMAT

    assert calcsize(SIDEDEF_FORMAT) == 30
