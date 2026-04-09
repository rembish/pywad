"""Tests for the MAPINFO lump parser."""
from __future__ import annotations

from wadlib.lumps.mapinfo import MapInfoEntry, MapInfoLump
from wadlib.wad import WadFile


def test_hexen_has_mapinfo(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None


def test_hexen_mapinfo_type(hexen_wad: WadFile) -> None:
    assert isinstance(hexen_wad.mapinfo, MapInfoLump)


def test_maps_is_non_empty(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    assert len(hexen_wad.mapinfo.maps) > 0


def test_all_entries_are_mapinfoentry(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    for entry in hexen_wad.mapinfo.maps:
        assert isinstance(entry, MapInfoEntry)


def test_map1_title(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(1)
    assert entry is not None
    assert entry.title == "WINNOWING HALL"


def test_map1_cdtrack(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(1)
    assert entry is not None
    assert entry.cdtrack == 13


def test_map1_lightning(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(1)
    assert entry is not None
    assert entry.lightning is True


def test_map2_next(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(2)
    assert entry is not None
    assert entry.next == 3


def test_doom1_has_no_mapinfo(doom1_wad: WadFile) -> None:
    assert doom1_wad.mapinfo is None


def test_get_returns_correct_entry(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(1)
    assert entry is not None
    assert entry.map_num == 1


def test_get_unknown_map_returns_none(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    assert hexen_wad.mapinfo.get(999) is None
