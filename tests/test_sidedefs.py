"""Tests for SIDEDEFS lump."""

from wadlib.lumps.sidedefs import SideDef
from wadlib.wad import WadFile


def test_sidedefs_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].sidedefs is not None


def test_sidedefs_non_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.maps[0].sidedefs) > 0


def test_sidedef_is_sidedef(freedoom1_wad: WadFile) -> None:
    s = freedoom1_wad.maps[0].sidedefs[0]
    assert isinstance(s, SideDef)


def test_sidedef_textures_are_strings(freedoom1_wad: WadFile) -> None:
    s = freedoom1_wad.maps[0].sidedefs[0]
    assert isinstance(s.upper_texture, str)
    assert isinstance(s.lower_texture, str)
    assert isinstance(s.middle_texture, str)


def test_sidedef_sector_index_non_negative(freedoom1_wad: WadFile) -> None:
    for sd in freedoom1_wad.maps[0].sidedefs:
        assert sd.sector >= 0


def test_sidedefs_doom2(freedoom2_wad: WadFile) -> None:
    assert freedoom2_wad.maps[0].sidedefs is not None
    assert len(freedoom2_wad.maps[0].sidedefs) > 0


def test_sidedef_row_size() -> None:
    from struct import calcsize

    from wadlib.lumps.sidedefs import SIDEDEF_FORMAT

    assert calcsize(SIDEDEF_FORMAT) == 30
