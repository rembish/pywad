"""Tests for map entry detection and lump attachment."""

import struct
from pathlib import Path

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


# ---------------------------------------------------------------------------
# maps_in_order — WAD directory order vs sorted order
# ---------------------------------------------------------------------------


def _build_wad_bytes(magic: bytes, lumps: list[tuple[bytes, bytes]]) -> bytes:
    """Build a minimal WAD from (name, data) pairs."""
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = 12 + len(lump_data)
    header = struct.pack("<4sII", magic, len(lumps), dir_offset)
    directory = b""
    offset = 12
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.ljust(8, b"\x00")[:8])
        offset += len(data)
    return header + lump_data + directory


def _wad_from_bytes(tmp_path: Path, data: bytes) -> WadFile:
    p = tmp_path / "test.wad"
    p.write_bytes(data)
    return WadFile(str(p))


class TestMapsInOrder:
    """maps_in_order must return maps in WAD directory order, not sorted."""

    def test_maps_in_order_same_length_as_maps(self, tmp_path: Path) -> None:
        """maps and maps_in_order must contain the same number of entries."""
        # MAP03, MAP01, MAP02 — reverse of sorted order
        lumps = [
            (b"MAP03", b""),
            (b"MAP01", b""),
            (b"MAP02", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        with _wad_from_bytes(tmp_path, raw) as wad:
            assert len(wad.maps_in_order) == len(wad.maps) == 3

    def test_maps_in_order_preserves_directory_sequence(self, tmp_path: Path) -> None:
        """maps_in_order must return MAP03, MAP01, MAP02 for a WAD with that order."""
        lumps = [
            (b"MAP03", b""),
            (b"MAP01", b""),
            (b"MAP02", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        with _wad_from_bytes(tmp_path, raw) as wad:
            names = [str(m) for m in wad.maps_in_order]
            assert names == ["MAP03", "MAP01", "MAP02"]

    def test_maps_sorts_numerically(self, tmp_path: Path) -> None:
        """maps must return MAP01, MAP02, MAP03 regardless of WAD order."""
        lumps = [
            (b"MAP03", b""),
            (b"MAP01", b""),
            (b"MAP02", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        with _wad_from_bytes(tmp_path, raw) as wad:
            names = [str(m) for m in wad.maps]
            assert names == ["MAP01", "MAP02", "MAP03"]

    def test_maps_in_order_doom1_style(self, tmp_path: Path) -> None:
        """maps_in_order works for Doom1-style episode maps."""
        lumps = [
            (b"E2M1", b""),
            (b"E1M3", b""),
            (b"E1M1", b""),
        ]
        raw = _build_wad_bytes(b"IWAD", lumps)
        with _wad_from_bytes(tmp_path, raw) as wad:
            names = [str(m) for m in wad.maps_in_order]
            assert names == ["E2M1", "E1M3", "E1M1"]

    def test_maps_in_order_already_sorted_is_identical(self, tmp_path: Path) -> None:
        """When WAD order matches sorted order, both properties agree."""
        lumps = [
            (b"MAP01", b""),
            (b"MAP02", b""),
            (b"MAP03", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        with _wad_from_bytes(tmp_path, raw) as wad:
            assert [str(m) for m in wad.maps_in_order] == [str(m) for m in wad.maps]
