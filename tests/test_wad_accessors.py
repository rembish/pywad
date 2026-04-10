"""Tests for WadFile.get_lump() and WadFile.get_lumps()."""

from wadlib.lumps.base import BaseLump
from wadlib.wad import WadFile


def test_get_lump_returns_baselump(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert isinstance(lump, BaseLump)


def test_get_lump_returns_none_for_missing(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_lump("DOESNOTEXIST") is None


def test_get_lump_name(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert lump.name == "PLAYPAL"


def test_get_lump_has_data(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert len(lump.raw()) > 0


def test_get_lumps_returns_list(freedoom1_wad: WadFile) -> None:
    lumps = freedoom1_wad.get_lumps("PLAYPAL")
    assert isinstance(lumps, list)
    assert len(lumps) >= 1


def test_get_lumps_missing_returns_empty(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_lumps("DOESNOTEXIST") == []


def test_get_lumps_all_are_baselump(freedoom1_wad: WadFile) -> None:
    for lump in freedoom1_wad.get_lumps("PLAYPAL"):
        assert isinstance(lump, BaseLump)
