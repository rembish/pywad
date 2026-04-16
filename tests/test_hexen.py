"""Tests for Hexen/Heretic format support."""

from struct import calcsize

from wadlib.lumps.hexen import HEXEN_LINEDEF_FORMAT, HEXEN_THING_FORMAT, HexenLineDef, HexenThing
from wadlib.lumps.things import Flags
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Struct sizes
# ---------------------------------------------------------------------------


def test_hexen_thing_format_size() -> None:
    assert calcsize(HEXEN_THING_FORMAT) == 20


def test_hexen_linedef_format_size() -> None:
    assert calcsize(HEXEN_LINEDEF_FORMAT) == 16


# ---------------------------------------------------------------------------
# Heretic — Doom-compatible, should parse exactly like Doom
# ---------------------------------------------------------------------------


def test_heretic_wad_type(blasphemer_wad: WadFile) -> None:
    from wadlib.enums import WadType

    assert blasphemer_wad.wad_type == WadType.IWAD


def test_heretic_has_maps(blasphemer_wad: WadFile) -> None:
    assert len(blasphemer_wad.maps) > 0


def test_heretic_map_count(blasphemer_wad: WadFile) -> None:
    # Heretic has 45 maps (E1-E5 with 9 each, plus secret levels)
    assert len(blasphemer_wad.maps) >= 45


def test_heretic_maps_have_things(blasphemer_wad: WadFile) -> None:
    m = blasphemer_wad.maps[0]
    assert m.things is not None
    assert len(m.things) > 0


def test_heretic_maps_have_sectors(blasphemer_wad: WadFile) -> None:
    assert blasphemer_wad.maps[0].sectors is not None


def test_heretic_no_hexen_things(blasphemer_wad: WadFile) -> None:
    # Heretic uses Doom-format things, NOT HexenThing
    from wadlib.lumps.things import Thing

    t = blasphemer_wad.maps[0].things[0]
    assert isinstance(t, Thing)
    assert not isinstance(t, HexenThing)


# ---------------------------------------------------------------------------
# Hexen WAD (real file)
# ---------------------------------------------------------------------------


def test_hexen_has_maps(hexen_wad: WadFile) -> None:
    assert len(hexen_wad.maps) > 0


def test_hexen_map_count(hexen_wad: WadFile) -> None:
    assert len(hexen_wad.maps) == 32


def test_hexen_things_are_hexen_things(hexen_wad: WadFile) -> None:
    t = hexen_wad.maps[0].things[0]
    assert isinstance(t, HexenThing)


def test_hexen_thing_has_tid(hexen_wad: WadFile) -> None:
    t = hexen_wad.maps[0].things[0]
    assert isinstance(t.tid, int)


def test_hexen_thing_has_z(hexen_wad: WadFile) -> None:
    t = hexen_wad.maps[0].things[0]
    assert isinstance(t.z, int)


def test_hexen_thing_flags_is_flags(hexen_wad: WadFile) -> None:
    t = hexen_wad.maps[0].things[0]
    assert isinstance(t.flags, Flags)


def test_hexen_linedefs_are_hexen_linedefs(hexen_wad: WadFile) -> None:
    line = hexen_wad.maps[0].lines[0]
    assert isinstance(line, HexenLineDef)


def test_hexen_linedef_has_args(hexen_wad: WadFile) -> None:
    line = hexen_wad.maps[0].lines[0]
    assert hasattr(line, "arg0")
    assert hasattr(line, "arg4")


def test_hexen_thing_count_is_sane(hexen_wad: WadFile) -> None:
    # Retail HEXEN.WAD MAP01: 346 things
    assert len(hexen_wad.maps[0].things) == 346


def test_hexen_linedef_count_is_sane(hexen_wad: WadFile) -> None:
    # Retail HEXEN.WAD MAP01: 1769 linedefs
    assert len(hexen_wad.maps[0].lines) == 1769


# ---------------------------------------------------------------------------
# Minimal in-memory Hexen WAD
# ---------------------------------------------------------------------------


def test_minimal_hexen_wad_things(minimal_hexen_wad: WadFile) -> None:
    things = minimal_hexen_wad.maps[0].things
    assert len(things) == 1
    assert isinstance(things[0], HexenThing)


def test_minimal_hexen_wad_linedefs(minimal_hexen_wad: WadFile) -> None:
    lines = minimal_hexen_wad.maps[0].lines
    assert len(lines) == 1
    assert isinstance(lines[0], HexenLineDef)


def test_minimal_hexen_thing_fields(minimal_hexen_wad: WadFile) -> None:
    t = minimal_hexen_wad.maps[0].things[0]
    assert t.tid == 0
    assert t.x == 0
    assert t.y == 0
    assert t.z == 0
    assert t.type == 1
