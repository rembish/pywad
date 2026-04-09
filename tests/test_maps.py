"""Tests for map entry detection and lump attachment."""

import pytest

from wadlib.lumps.map import Doom1MapEntry, Doom2MapEntry, MapEntry
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Map list basics
# ---------------------------------------------------------------------------


def test_doom1_has_maps(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.maps) > 0


def test_doom2_has_maps(doom2_wad: WadFile) -> None:
    assert len(doom2_wad.maps) > 0


def test_doom1_map_count(doom1_wad: WadFile) -> None:
    # Registered Doom has 27 maps (E1-E3); Ultimate Doom has 36 (E1-E4)
    assert len(doom1_wad.maps) in (27, 36)


def test_doom2_map_count(doom2_wad: WadFile) -> None:
    # Doom II has 32 maps (MAP01-MAP32)
    assert len(doom2_wad.maps) == 32


# ---------------------------------------------------------------------------
# Map entry types
# ---------------------------------------------------------------------------


def test_doom1_maps_are_doom1_entries(doom1_wad: WadFile) -> None:
    for m in doom1_wad.maps:
        assert isinstance(m, Doom1MapEntry)


def test_doom2_maps_are_doom2_entries(doom2_wad: WadFile) -> None:
    for m in doom2_wad.maps:
        assert isinstance(m, Doom2MapEntry)


def test_minimal_iwad_map_type(minimal_iwad: WadFile) -> None:
    assert isinstance(minimal_iwad.maps[0], Doom1MapEntry)


def test_minimal_pwad_map_type(minimal_pwad: WadFile) -> None:
    assert isinstance(minimal_pwad.maps[0], Doom2MapEntry)


# ---------------------------------------------------------------------------
# Map entry attributes
# ---------------------------------------------------------------------------


def test_doom1_map_episode(doom1_wad: WadFile) -> None:
    first = doom1_wad.maps[0]
    assert isinstance(first, Doom1MapEntry)
    assert first.episode == 1
    assert first.number == 1


def test_doom2_map_number(doom2_wad: WadFile) -> None:
    first = doom2_wad.maps[0]
    assert first.number == 1


def test_map_repr_doom1(doom1_wad: WadFile) -> None:
    r = repr(doom1_wad.maps[0])
    assert "Episode" in r


def test_map_repr_doom2(doom2_wad: WadFile) -> None:
    r = repr(doom2_wad.maps[0])
    assert "Map" in r


# ---------------------------------------------------------------------------
# MapEntry factory
# ---------------------------------------------------------------------------


def test_map_entry_factory_invalid_raises() -> None:
    class _FakeEntry:
        name = "INVALID"

    with pytest.raises(ValueError, match="Unknown map name format"):
        MapEntry(_FakeEntry())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Lump attachment
# ---------------------------------------------------------------------------


def test_doom1_maps_have_things(doom1_wad: WadFile) -> None:
    for m in doom1_wad.maps:
        assert m.things is not None


def test_doom1_maps_have_vertices(doom1_wad: WadFile) -> None:
    for m in doom1_wad.maps:
        assert m.vertices is not None


def test_doom1_maps_have_lines(doom1_wad: WadFile) -> None:
    for m in doom1_wad.maps:
        assert m.lines is not None


def test_minimal_iwad_things_attached(minimal_iwad: WadFile) -> None:
    m = minimal_iwad.maps[0]
    assert m.things is not None
    assert len(m.things) == 1


def test_minimal_iwad_vertices_attached(minimal_iwad: WadFile) -> None:
    m = minimal_iwad.maps[0]
    assert m.vertices is not None
    assert len(m.vertices) == 2


def test_minimal_iwad_linedefs_attached(minimal_iwad: WadFile) -> None:
    m = minimal_iwad.maps[0]
    assert m.lines is not None
    assert len(m.lines) == 1
