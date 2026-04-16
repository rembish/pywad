"""Phase 2 — unified map assembly over generic resources.

Tests cover:
- BaseMapEntry.origin default value
- WadFile.from_bytes() — in-memory WAD parsing
- Pk3Archive.maps — decomposed and embedded-WAD PK3 formats
- ResourceResolver.maps() — priority merging across sources
"""

from __future__ import annotations

import os
import struct
import tempfile
import zipfile

import pytest

from wadlib.lumps.map import MapEntry
from wadlib.pk3 import Pk3Archive
from wadlib.registry import attach_map_lumps, scan_map_groups
from wadlib.resolver import ResourceResolver
from wadlib.source import MemoryLumpSource
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wad_bytes(lumps: list[tuple[str, bytes]]) -> bytes:
    """Build a minimal PWAD in memory."""
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)
    header = struct.pack("<4sII", b"PWAD", len(lumps), dir_offset)
    directory = b""
    offset = data_start
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.encode().ljust(8, b"\x00"))
        offset += len(data)
    return header + lump_data + directory


def _wad_file(lumps: list[tuple[str, bytes]]) -> str:
    """Write a minimal PWAD to a temp file and return the path."""
    raw = _wad_bytes(lumps)
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def _pk3_file(entries: dict[str, bytes]) -> str:
    """Write a temporary pk3 and return the path."""
    with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


# ---------------------------------------------------------------------------
# BaseMapEntry.origin
# ---------------------------------------------------------------------------


class TestOriginAttribute:
    def test_origin_default_empty(self) -> None:
        src = MemoryLumpSource("MAP01", b"")
        entry = MapEntry(src)
        assert entry.origin == ""

    def test_origin_settable(self) -> None:
        src = MemoryLumpSource("E1M1", b"")
        entry = MapEntry(src)
        entry.origin = "DOOM.WAD"
        assert entry.origin == "DOOM.WAD"


# ---------------------------------------------------------------------------
# WadFile.from_bytes
# ---------------------------------------------------------------------------


class TestWadFromBytes:
    def test_basic_parsing(self) -> None:
        raw = _wad_bytes([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        wad = WadFile.from_bytes(raw)
        assert [e.name for e in wad.directory] == ["MAP01", "THINGS"]

    def test_maps_assembled(self) -> None:
        raw = _wad_bytes([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        wad = WadFile.from_bytes(raw)
        assert len(wad.maps) == 1
        assert wad.maps[0].name == "MAP01"

    def test_doom1_map_parsed(self) -> None:
        raw = _wad_bytes([("E1M1", b""), ("THINGS", b"\x00" * 10)])
        wad = WadFile.from_bytes(raw)
        assert wad.maps[0].name == "E1M1"

    def test_bad_magic_raises(self) -> None:
        from wadlib.exceptions import BadHeaderWadException

        bad = b"XXXX" + b"\x00" * 8
        with pytest.raises(BadHeaderWadException):
            WadFile.from_bytes(bad)

    def test_truncated_raises(self) -> None:
        from wadlib.exceptions import TruncatedWadError

        with pytest.raises(TruncatedWadError):
            WadFile.from_bytes(b"\x00" * 3)

    def test_no_pwads_by_default(self) -> None:
        raw = _wad_bytes([("MAP01", b"")])
        wad = WadFile.from_bytes(raw)
        assert wad._pwads == []


# ---------------------------------------------------------------------------
# scan_map_groups with MemoryLumpSource
# ---------------------------------------------------------------------------


class TestScanMapGroupsWithMemorySources:
    def test_groups_doom2_map(self) -> None:
        sources = [
            MemoryLumpSource("MAP01", b""),
            MemoryLumpSource("THINGS", b"\x00" * 10),
            MemoryLumpSource("VERTEXES", b"\x00" * 4),
        ]
        groups = scan_map_groups(sources)
        assert len(groups) == 1
        marker, lumps = groups[0]
        assert marker.name == "MAP01"
        assert [src.name for src in lumps] == ["THINGS", "VERTEXES"]

    def test_groups_two_maps(self) -> None:
        sources = [
            MemoryLumpSource("MAP01", b""),
            MemoryLumpSource("THINGS", b"\x00" * 10),
            MemoryLumpSource("MAP02", b""),
            MemoryLumpSource("THINGS", b"\x00" * 10),
        ]
        groups = scan_map_groups(sources)
        assert len(groups) == 2
        assert groups[0][0].name == "MAP01"
        assert groups[1][0].name == "MAP02"


# ---------------------------------------------------------------------------
# attach_map_lumps with MemoryLumpSource
# ---------------------------------------------------------------------------


class TestAttachMapLumpsWithMemorySources:
    def test_things_attached(self) -> None:
        marker = MemoryLumpSource("MAP01", b"")
        entry = MapEntry(marker)
        lump_sources = [MemoryLumpSource("THINGS", b"\x00" * 10)]
        attach_map_lumps(entry, lump_sources, hexen=False)
        assert entry.things is not None

    def test_hexen_behavior_flag(self) -> None:
        # BEHAVIOR lump triggers hexen=True parsing internally; just verify
        # no crash when it's assembled
        marker = MemoryLumpSource("MAP01", b"")
        entry = MapEntry(marker)
        behavior_data = b"ACS\x00" + b"\x00" * 12  # minimal ACS header
        lump_sources = [MemoryLumpSource("BEHAVIOR", behavior_data)]
        attach_map_lumps(entry, lump_sources, hexen=True)
        assert entry.behavior is not None


# ---------------------------------------------------------------------------
# Pk3Archive.maps — decomposed format
# ---------------------------------------------------------------------------


class TestPk3MapsDecomposed:
    def test_single_map(self) -> None:
        path = _pk3_file(
            {
                "maps/MAP01/THINGS.lmp": b"\x00" * 10,
                "maps/MAP01/VERTEXES.lmp": b"\x00" * 4,
            }
        )
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "MAP01" in maps
        finally:
            os.unlink(path)

    def test_two_maps(self) -> None:
        path = _pk3_file(
            {
                "maps/MAP01/THINGS.lmp": b"\x00" * 10,
                "maps/E1M1/THINGS.lmp": b"\x00" * 10,
            }
        )
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "MAP01" in maps
            assert "E1M1" in maps
        finally:
            os.unlink(path)

    def test_origin_set_decomposed(self) -> None:
        path = _pk3_file({"maps/MAP01/THINGS.lmp": b"\x00" * 10})
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "MAP01" in maps
            assert "MAP01" in maps["MAP01"].origin
            assert maps["MAP01"].origin.endswith("/maps/MAP01/")
        finally:
            os.unlink(path)

    def test_non_map_dirs_ignored(self) -> None:
        path = _pk3_file(
            {
                "maps/MAP01/THINGS.lmp": b"\x00" * 10,
                "sounds/DSPISTOL.wav": b"\x00" * 20,
            }
        )
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert list(maps.keys()) == ["MAP01"]
        finally:
            os.unlink(path)

    def test_invalid_map_name_ignored(self) -> None:
        path = _pk3_file(
            {
                "maps/NOTAMAP/THINGS.lmp": b"\x00" * 10,
                "maps/MAP01/THINGS.lmp": b"\x00" * 10,
            }
        )
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            # NOTAMAP doesn't match ExMx / MAPxx patterns
            assert "NOTAMAP" not in maps
            assert "MAP01" in maps
        finally:
            os.unlink(path)

    def test_empty_archive_returns_empty(self) -> None:
        path = _pk3_file({})
        try:
            with Pk3Archive(path) as pk3:
                assert pk3.maps == {}
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Pk3Archive.maps — embedded WAD format
# ---------------------------------------------------------------------------


class TestPk3MapsEmbeddedWad:
    def test_embedded_wad_parsed(self) -> None:
        raw = _wad_bytes([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        path = _pk3_file({"maps/MAP01.wad": raw})
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "MAP01" in maps
        finally:
            os.unlink(path)

    def test_origin_set_embedded(self) -> None:
        raw = _wad_bytes([("E1M1", b""), ("THINGS", b"\x00" * 10)])
        path = _pk3_file({"maps/E1M1.wad": raw})
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "E1M1" in maps
            assert "maps/E1M1.wad" in maps["E1M1"].origin
        finally:
            os.unlink(path)

    def test_embedded_takes_precedence_over_decomposed(self) -> None:
        """When both formats exist for the same map, the embedded WAD wins."""
        raw = _wad_bytes([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        path = _pk3_file(
            {
                "maps/MAP01.wad": raw,
                "maps/MAP01/THINGS.lmp": b"\x00" * 10,
            }
        )
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            assert "MAP01" in maps
            # origin should point to the embedded WAD, not the decomposed dir
            assert maps["MAP01"].origin.endswith(".wad")
        finally:
            os.unlink(path)

    def test_corrupt_embedded_wad_skipped(self) -> None:
        """A corrupt embedded WAD does not crash; it is silently skipped."""
        path = _pk3_file({"maps/MAP01.wad": b"GARBAGE"})
        try:
            with Pk3Archive(path) as pk3:
                maps = pk3.maps
            # Corrupt WAD is skipped; result is empty (or has decomposed fallback)
            assert "MAP01" not in maps
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# ResourceResolver.maps()
# ---------------------------------------------------------------------------


class TestResourceResolverMaps:
    def test_single_wad_source(self) -> None:
        path = _wad_file([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        try:
            with WadFile(path) as wad:
                resolver = ResourceResolver(wad)
                maps = resolver.maps()
            assert "MAP01" in maps
        finally:
            os.unlink(path)

    def test_origin_set_for_wad_source(self) -> None:
        path = _wad_file([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        try:
            with WadFile(path) as wad:
                maps = ResourceResolver(wad).maps()
            assert maps["MAP01"].origin == path
        finally:
            os.unlink(path)

    def test_single_pk3_source(self) -> None:
        path = _pk3_file({"maps/MAP01/THINGS.lmp": b"\x00" * 10})
        try:
            with Pk3Archive(path) as pk3:
                maps = ResourceResolver(pk3).maps()
            assert "MAP01" in maps
        finally:
            os.unlink(path)

    def test_pk3_higher_priority_wins(self) -> None:
        """PK3 (first source = higher priority) overrides WAD's MAP01."""
        wad_path = _wad_file([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        pk3_path = _pk3_file({"maps/MAP01/THINGS.lmp": b"\x00" * 10})
        try:
            with WadFile(wad_path) as wad, Pk3Archive(pk3_path) as pk3:
                # pk3 is first → higher priority
                maps = ResourceResolver(pk3, wad).maps()
            assert "MAP01" in maps
            assert "pk3" in maps["MAP01"].origin or maps["MAP01"].origin.endswith("/")
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)

    def test_wad_higher_priority_wins(self) -> None:
        """WAD (first source = higher priority) overrides PK3's MAP01."""
        wad_path = _wad_file([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        pk3_path = _pk3_file({"maps/MAP01/THINGS.lmp": b"\x00" * 10})
        try:
            with WadFile(wad_path) as wad, Pk3Archive(pk3_path) as pk3:
                # wad is first → higher priority
                maps = ResourceResolver(wad, pk3).maps()
            assert "MAP01" in maps
            assert maps["MAP01"].origin == wad_path
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)

    def test_maps_merged_across_sources(self) -> None:
        """Maps from different sources that don't collide all appear."""
        wad_path = _wad_file([("MAP01", b""), ("THINGS", b"\x00" * 10)])
        pk3_path = _pk3_file({"maps/MAP02/THINGS.lmp": b"\x00" * 10})
        try:
            with WadFile(wad_path) as wad, Pk3Archive(pk3_path) as pk3:
                maps = ResourceResolver(wad, pk3).maps()
            assert "MAP01" in maps
            assert "MAP02" in maps
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)

    def test_empty_resolver_returns_empty(self) -> None:
        resolver = ResourceResolver()
        assert resolver.maps() == {}
