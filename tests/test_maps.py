"""Tests for map entry detection and lump attachment."""

import pytest

from wadlib.lumps.map import Doom1MapEntry, Doom2MapEntry, MapEntry
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Map list basics
# ---------------------------------------------------------------------------


def test_freedoom1_has_maps(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.maps) > 0


def test_freedoom2_has_maps(freedoom2_wad: WadFile) -> None:
    assert len(freedoom2_wad.maps) > 0


def test_freedoom1_map_count(freedoom1_wad: WadFile) -> None:
    # freedoom1 ships all 4 episodes: E1M1-E4M9 = 36 maps
    assert len(freedoom1_wad.maps) == 36


def test_freedoom2_map_count(freedoom2_wad: WadFile) -> None:
    # freedoom2 has MAP01-MAP32 = 32 maps
    assert len(freedoom2_wad.maps) == 32


# ---------------------------------------------------------------------------
# Map entry types
# ---------------------------------------------------------------------------


def test_freedoom1_maps_are_doom1_entries(freedoom1_wad: WadFile) -> None:
    for m in freedoom1_wad.maps:
        assert isinstance(m, Doom1MapEntry)


def test_freedoom2_maps_are_doom2_entries(freedoom2_wad: WadFile) -> None:
    for m in freedoom2_wad.maps:
        assert isinstance(m, Doom2MapEntry)


def test_minimal_iwad_map_type(minimal_iwad: WadFile) -> None:
    assert isinstance(minimal_iwad.maps[0], Doom1MapEntry)


def test_minimal_pwad_map_type(minimal_pwad: WadFile) -> None:
    assert isinstance(minimal_pwad.maps[0], Doom2MapEntry)


# ---------------------------------------------------------------------------
# Map entry attributes
# ---------------------------------------------------------------------------


def test_freedoom1_map_episode(freedoom1_wad: WadFile) -> None:
    first = freedoom1_wad.maps[0]
    assert isinstance(first, Doom1MapEntry)
    assert first.episode == 1
    assert first.number == 1


def test_freedoom2_map_number(freedoom2_wad: WadFile) -> None:
    first = freedoom2_wad.maps[0]
    assert first.number == 1


def test_map_repr_doom1(freedoom1_wad: WadFile) -> None:
    r = repr(freedoom1_wad.maps[0])
    assert "Episode" in r


def test_map_repr_doom2(freedoom2_wad: WadFile) -> None:
    r = repr(freedoom2_wad.maps[0])
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


def test_freedoom1_maps_have_things(freedoom1_wad: WadFile) -> None:
    for m in freedoom1_wad.maps:
        assert m.things is not None


def test_freedoom1_maps_have_vertices(freedoom1_wad: WadFile) -> None:
    for m in freedoom1_wad.maps:
        assert m.vertices is not None


def test_freedoom1_maps_have_lines(freedoom1_wad: WadFile) -> None:
    for m in freedoom1_wad.maps:
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
