"""Tests for the ZMAPINFO lump parser (ZDoom format)."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.zmapinfo import ZMapInfoEntry, serialize_zmapinfo
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# serialize_zmapinfo — unit tests, no WAD needed
# ---------------------------------------------------------------------------


def test_serialize_zmapinfo_direct_title() -> None:
    e = ZMapInfoEntry(map_name="MAP01", title="ENTRYWAY")
    text = serialize_zmapinfo([e])
    assert 'map MAP01 "ENTRYWAY"' in text
    assert "{" in text
    assert "}" in text


def test_serialize_zmapinfo_lookup_title() -> None:
    e = ZMapInfoEntry(map_name="E5M1", title="", title_lookup="HUSTR_E5M1")
    text = serialize_zmapinfo([e])
    assert 'map E5M1 lookup "HUSTR_E5M1"' in text


def test_serialize_zmapinfo_all_fields() -> None:
    e = ZMapInfoEntry(
        map_name="MAP02",
        title="UNDERHALLS",
        levelnum=2,
        next="MAP03",
        secretnext="MAP35",
        sky1="SKY1",
        music="D_RUNNIN",
        titlepatch="CWILV01",
        cluster=1,
        par=90,
    )
    text = serialize_zmapinfo([e])
    assert "levelnum = 2" in text
    assert 'next = "MAP03"' in text
    assert 'secretnext = "MAP35"' in text
    assert 'sky1 = "SKY1"' in text
    assert 'music = "D_RUNNIN"' in text
    assert 'titlepatch = "CWILV01"' in text
    assert "cluster = 1" in text
    assert "par = 90" in text


def test_serialize_zmapinfo_multiple() -> None:
    entries = [
        ZMapInfoEntry(map_name="MAP01", title="ENTRYWAY"),
        ZMapInfoEntry(map_name="MAP02", title="UNDERHALLS"),
    ]
    text = serialize_zmapinfo(entries)
    assert "MAP01" in text
    assert "MAP02" in text


# ---------------------------------------------------------------------------
# ZMapInfoLump.maps — synthetic WAD tests
# ---------------------------------------------------------------------------


def _make_zmapinfo_wad(text: str) -> str:
    data = text.encode("latin-1")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"ZMAPINFO")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


_BASIC_ZMAPINFO = """\
map MAP01 "ENTRYWAY"
{
    levelnum = 1
    next = "MAP02"
    secretnext = "MAP35"
    sky1 = "SKY1"
    music = "D_RUNNIN"
    titlepatch = "CWILV00"
    cluster = 1
    par = 30
}
"""


def test_zmapinfo_parses_basic_entry() -> None:
    path = _make_zmapinfo_wad(_BASIC_ZMAPINFO)
    with WadFile(path) as wad:
        assert wad.zmapinfo is not None
        entries = wad.zmapinfo.maps
        assert len(entries) == 1
        e = entries[0]
        assert e.map_name == "MAP01"
        assert e.title == "ENTRYWAY"
        assert e.levelnum == 1
        assert e.next == "MAP02"
        assert e.secretnext == "MAP35"
        assert e.sky1 == "SKY1"
        assert e.music == "D_RUNNIN"
        assert e.titlepatch == "CWILV00"
        assert e.cluster == 1
        assert e.par == 30


def test_zmapinfo_parses_lookup_title() -> None:
    text = 'map E5M1 lookup "HUSTR_E5M1"\n{\n    levelnum = 33\n}\n'
    path = _make_zmapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.zmapinfo is not None
        e = wad.zmapinfo.maps[0]
        assert e.title_lookup == "HUSTR_E5M1"
        assert e.levelnum == 33


def test_zmapinfo_resolved_title_direct() -> None:
    e = ZMapInfoEntry(map_name="MAP01", title="ENTRYWAY")
    assert e.resolved_title() == "ENTRYWAY"


def test_zmapinfo_resolved_title_with_lookup() -> None:
    e = ZMapInfoEntry(map_name="MAP01", title="", title_lookup="HUSTR_1")
    lang = {"HUSTR_1": "ENTRYWAY"}
    assert e.resolved_title(lang) == "ENTRYWAY"


def test_zmapinfo_resolved_title_lookup_missing_key() -> None:
    e = ZMapInfoEntry(map_name="MAP01", title="fallback", title_lookup="MISSING_KEY")
    assert e.resolved_title({}) == "fallback"


def test_zmapinfo_skips_non_map_blocks() -> None:
    text = 'gameinfo\n{\n    titlepage = "TITLE"\n}\n' + _BASIC_ZMAPINFO
    path = _make_zmapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.zmapinfo is not None
        assert len(wad.zmapinfo.maps) == 1


def test_zmapinfo_strips_comments() -> None:
    text = (
        '// header comment\nmap MAP01 "ENTRYWAY" // inline\n{\n    /* block */\n    par = 30\n}\n'
    )
    path = _make_zmapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.zmapinfo is not None
        e = wad.zmapinfo.maps[0]
        assert e.par == 30


def test_zmapinfo_multiple_maps() -> None:
    text = (
        'map MAP01 "ENTRYWAY"\n{\n    levelnum = 1\n}\n'
        'map MAP02 "UNDERHALLS"\n{\n    levelnum = 2\n}\n'
    )
    path = _make_zmapinfo_wad(text)
    with WadFile(path) as wad:
        assert wad.zmapinfo is not None
        assert len(wad.zmapinfo.maps) == 2
