"""Tests for the MAPINFO lump parser."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.mapinfo import MapInfoEntry, MapInfoLump, serialize_mapinfo
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# serialize_mapinfo — unit tests, no WAD needed
# ---------------------------------------------------------------------------


def test_serialize_mapinfo_basic() -> None:
    e = MapInfoEntry(map_num=1, title="WINNOWING HALL", cdtrack=13, lightning=True)
    text = serialize_mapinfo([e])
    assert 'map 1 "WINNOWING HALL"' in text
    assert "cdtrack 13" in text
    assert "lightning" in text


def test_serialize_mapinfo_all_fields() -> None:
    e = MapInfoEntry(
        map_num=2,
        title="SEVEN PORTALS",
        warptrans=2,
        next=3,
        cluster=1,
        sky1="SKY1",
        sky2="SKY2",
        cdtrack=5,
        lightning=False,
        doublesky=True,
        fadetable="COLORMAP",
    )
    text = serialize_mapinfo([e])
    assert "warptrans 2" in text
    assert "next 3" in text
    assert "cluster 1" in text
    assert 'sky1 "SKY1" 0' in text
    assert 'sky2 "SKY2" 0' in text
    assert "doublesky" in text
    assert 'fadetable "COLORMAP"' in text


def test_serialize_mapinfo_multiple() -> None:
    entries = [
        MapInfoEntry(map_num=1, title="FIRST"),
        MapInfoEntry(map_num=2, title="SECOND"),
    ]
    text = serialize_mapinfo(entries)
    assert 'map 1 "FIRST"' in text
    assert 'map 2 "SECOND"' in text


# ---------------------------------------------------------------------------
# MapInfoLump.maps — synthetic WAD tests
# ---------------------------------------------------------------------------


def _make_mapinfo_wad(mapinfo_text: str) -> str:
    data = mapinfo_text.encode("latin-1")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"MAPINFO\x00")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def test_mapinfo_parses_basic_entry() -> None:
    path = _make_mapinfo_wad('map 1 "WINNOWING HALL"\ncdtrack 13\nlightning\n')
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        entries = wad.mapinfo.maps
        assert len(entries) == 1
        e = entries[0]
        assert e.map_num == 1
        assert e.title == "WINNOWING HALL"
        assert e.cdtrack == 13
        assert e.lightning is True


def test_mapinfo_parses_all_properties() -> None:
    # Hexen MAPINFO uses bare token names for sky/fadetable (no quotes)
    text = (
        'map 2 "SEVEN PORTALS"\n'
        "warptrans 2\nnext 3\ncluster 1\n"
        "sky1 SKY1\nsky2 SKY2\n"
        "cdtrack 5\ndoublesky\n"
        "fadetable COLORMAP\n"
    )
    path = _make_mapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        e = wad.mapinfo.maps[0]
        assert e.warptrans == 2
        assert e.next == 3
        assert e.cluster == 1
        assert e.sky1 == "SKY1"
        assert e.sky2 == "SKY2"
        assert e.doublesky is True
        assert e.fadetable == "COLORMAP"


def test_mapinfo_skips_comments_and_globals() -> None:
    text = 'clusterdef 1\n; this is a comment\n\nmap 1 "HALL"\n'
    path = _make_mapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        entries = wad.mapinfo.maps
        assert len(entries) == 1


def test_mapinfo_multiple_maps() -> None:
    text = 'map 1 "FIRST"\nmap 2 "SECOND"\ncdtrack 3\n'
    path = _make_mapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        entries = wad.mapinfo.maps
        assert len(entries) == 2
        assert entries[0].map_num == 1
        assert entries[1].map_num == 2
        assert entries[1].cdtrack == 3


def test_mapinfo_get_returns_correct_entry() -> None:
    path = _make_mapinfo_wad('map 5 "FIFTH"\ncdtrack 7\n')
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        e = wad.mapinfo.get(5)
        assert e is not None
        assert e.title == "FIFTH"


def test_mapinfo_get_missing_returns_none() -> None:
    path = _make_mapinfo_wad('map 1 "FIRST"\n')
    with WadFile(path) as wad:
        assert wad.mapinfo is not None
        assert wad.mapinfo.get(99) is None


# ---------------------------------------------------------------------------
# Real-WAD tests (require HEXEN.WAD)
# ---------------------------------------------------------------------------


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


def test_doom1_has_no_mapinfo(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.mapinfo is None


def test_get_returns_correct_entry(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    entry = hexen_wad.mapinfo.get(1)
    assert entry is not None
    assert entry.map_num == 1


def test_get_unknown_map_returns_none(hexen_wad: WadFile) -> None:
    assert hexen_wad.mapinfo is not None
    assert hexen_wad.mapinfo.get(999) is None
