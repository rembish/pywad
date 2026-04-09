"""Tests for WadFile.get_lump() and WadFile.get_lumps()."""


from pywad.lumps.base import BaseLump
from pywad.wad import WadFile


def test_get_lump_returns_baselump(doom1_wad: WadFile) -> None:
    lump = doom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert isinstance(lump, BaseLump)


def test_get_lump_returns_none_for_missing(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_lump("DOESNOTEXIST") is None


def test_get_lump_name(doom1_wad: WadFile) -> None:
    lump = doom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert lump.name == "PLAYPAL"


def test_get_lump_has_data(doom1_wad: WadFile) -> None:
    lump = doom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert len(lump.raw()) > 0


def test_get_lumps_returns_list(doom1_wad: WadFile) -> None:
    lumps = doom1_wad.get_lumps("PLAYPAL")
    assert isinstance(lumps, list)
    assert len(lumps) >= 1


def test_get_lumps_missing_returns_empty(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_lumps("DOESNOTEXIST") == []


def test_get_lumps_all_are_baselump(doom1_wad: WadFile) -> None:
    for lump in doom1_wad.get_lumps("PLAYPAL"):
        assert isinstance(lump, BaseLump)
