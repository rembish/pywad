"""Tests for wadlib.registry — DecoderRegistry, attach_map_lumps, scan/assemble."""

from __future__ import annotations

import struct
import tempfile
from io import BytesIO
from pathlib import Path

from wadlib.directory import DirectoryEntry
from wadlib.lumps.base import BaseLump
from wadlib.lumps.colormap import ColormapLump
from wadlib.lumps.playpal import PlayPal
from wadlib.registry import (
    LUMP_REGISTRY,
    DecoderRegistry,
    assemble_maps,
    attach_map_lumps,
    scan_map_groups,
)

# ---------------------------------------------------------------------------
# DecoderRegistry — unit tests
# ---------------------------------------------------------------------------


class TestDecoderRegistry:
    def test_register_and_decode(self) -> None:
        reg = DecoderRegistry()
        reg.register("PLAYPAL", PlayPal)
        assert "PLAYPAL" in reg
        assert len(reg) == 1

    def test_names(self) -> None:
        reg = DecoderRegistry()
        reg.register("PLAYPAL", PlayPal)
        reg.register("COLORMAP", ColormapLump)
        assert set(reg.names()) == {"PLAYPAL", "COLORMAP"}

    def test_not_in(self) -> None:
        reg = DecoderRegistry()
        assert "MISSING" not in reg

    def test_decode_unknown_falls_back_to_baselump(self) -> None:
        reg = DecoderRegistry()
        # Build a minimal directory entry via a temp WAD
        wad_bytes = _build_single_lump_wad(b"UNKNOWN\x00", b"test")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                entry = wad.find_lump("UNKNOWN")
                assert entry is not None
                result = reg.decode("UNKNOWN", entry)
                assert isinstance(result, BaseLump)

    def test_decode_registered_constructor(self) -> None:
        reg = DecoderRegistry()
        reg.register("PLAYPAL", PlayPal)
        wad_bytes = _build_single_lump_wad(b"PLAYPAL\x00", b"\x00" * 768)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                entry = wad.find_lump("PLAYPAL")
                assert entry is not None
                result = reg.decode("PLAYPAL", entry)
                assert isinstance(result, PlayPal)

    def test_find_and_decode_missing_returns_none(self) -> None:
        reg = DecoderRegistry()
        wad_bytes = _build_single_lump_wad(b"DUMMY\x00\x00\x00", b"x")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                result = reg.find_and_decode("NOTHERE", wad)
                assert result is None

    def test_find_and_decode_found(self) -> None:
        reg = DecoderRegistry()
        reg.register("PLAYPAL", PlayPal)
        wad_bytes = _build_single_lump_wad(b"PLAYPAL\x00", b"\x00" * 768)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                result = reg.find_and_decode("PLAYPAL", wad)
                assert isinstance(result, PlayPal)

    def test_register_overwrites(self) -> None:
        reg = DecoderRegistry()
        reg.register("MYDATA", PlayPal)
        reg.register("MYDATA", ColormapLump)
        assert len(reg) == 1  # still one entry
        wad_bytes = _build_single_lump_wad(b"MYDATA\x00\x00", b"\x00" * 10)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                entry = wad.find_lump("MYDATA")
                assert entry is not None
                result = reg.decode("MYDATA", entry)
                assert isinstance(result, ColormapLump)


# ---------------------------------------------------------------------------
# LUMP_REGISTRY — built-in registry content
# ---------------------------------------------------------------------------


class TestLumpRegistry:
    def test_known_lumps_registered(self) -> None:
        expected = {
            "PLAYPAL",
            "COLORMAP",
            "PNAMES",
            "TEXTURE1",
            "TEXTURE2",
            "ENDOOM",
            "SNDINFO",
            "SNDSEQ",
            "MAPINFO",
            "ZMAPINFO",
            "LANGUAGE",
            "ANIMDEFS",
            "DECORATE",
            "DEHACKED",
        }
        for name in expected:
            assert name in LUMP_REGISTRY, f"{name} missing from LUMP_REGISTRY"

    def test_at_least_14_entries(self) -> None:
        assert len(LUMP_REGISTRY) >= 14

    def test_find_and_decode_playpal(self) -> None:
        wad_bytes = _build_single_lump_wad(b"PLAYPAL\x00", b"\x00" * 768)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test.wad"
            path.write_bytes(wad_bytes)
            from wadlib.wad import WadFile

            with WadFile(str(path)) as wad:
                result = LUMP_REGISTRY.find_and_decode("PLAYPAL", wad)
                assert isinstance(result, PlayPal)

    def test_public_api_export(self) -> None:
        """DecoderRegistry and LUMP_REGISTRY must be importable from top-level."""
        import wadlib

        assert hasattr(wadlib, "DecoderRegistry")
        assert hasattr(wadlib, "LUMP_REGISTRY")
        assert isinstance(wadlib.LUMP_REGISTRY, DecoderRegistry)


# ---------------------------------------------------------------------------
# attach_map_lumps — smoke test
# ---------------------------------------------------------------------------


class TestAttachMapLumps:
    def test_attach_map_lumps_is_importable(self) -> None:
        assert callable(attach_map_lumps)


# ---------------------------------------------------------------------------
# scan_map_groups / assemble_maps — unit tests
# ---------------------------------------------------------------------------


class TestScanMapGroups:
    def test_empty_directory(self) -> None:
        assert scan_map_groups([]) == []

    def test_no_markers(self) -> None:
        entries = [_fake_entry("PLAYPAL"), _fake_entry("COLORMAP")]
        assert scan_map_groups(entries) == []

    def test_single_doom1_marker_no_lumps(self) -> None:
        marker = _fake_entry("E1M1")
        groups = scan_map_groups([marker])
        assert len(groups) == 1
        m, lumps = groups[0]
        assert m.name == "E1M1"
        assert lumps == []

    def test_single_doom2_marker_no_lumps(self) -> None:
        marker = _fake_entry("MAP01")
        groups = scan_map_groups([marker])
        assert len(groups) == 1
        assert groups[0][0].name == "MAP01"

    def test_marker_with_valid_lump(self) -> None:
        entries = [_fake_entry("E1M1"), _fake_entry("THINGS")]
        groups = scan_map_groups(entries)
        assert len(groups) == 1
        m, lumps = groups[0]
        assert m.name == "E1M1"
        assert len(lumps) == 1
        assert lumps[0].name == "THINGS"

    def test_non_mapdata_lump_ignored(self) -> None:
        entries = [_fake_entry("E1M1"), _fake_entry("THINGS"), _fake_entry("PLAYPAL")]
        groups = scan_map_groups(entries)
        assert len(groups) == 1
        _, lumps = groups[0]
        # PLAYPAL is not a MapData name so it's ignored
        assert len(lumps) == 1
        assert lumps[0].name == "THINGS"

    def test_multiple_markers(self) -> None:
        entries = [
            _fake_entry("E1M1"),
            _fake_entry("THINGS"),
            _fake_entry("E1M2"),
            _fake_entry("VERTEXES"),
            _fake_entry("LINEDEFS"),
        ]
        groups = scan_map_groups(entries)
        assert len(groups) == 2
        assert groups[0][0].name == "E1M1"
        assert len(groups[0][1]) == 1
        assert groups[1][0].name == "E1M2"
        assert len(groups[1][1]) == 2

    def test_consecutive_markers_no_lumps(self) -> None:
        entries = [_fake_entry("MAP01"), _fake_entry("MAP02")]
        groups = scan_map_groups(entries)
        assert len(groups) == 2
        assert groups[0][1] == []
        assert groups[1][1] == []


class TestAssembleMaps:
    def test_empty_directories(self) -> None:
        seen, order = assemble_maps([])
        assert seen == {}
        assert order == []

    def test_empty_directory_list(self) -> None:
        seen, order = assemble_maps([[]])
        assert seen == {}
        assert order == []

    def test_single_map(self) -> None:
        directory = [_fake_entry("E1M1"), _fake_entry("THINGS")]
        seen, order = assemble_maps([directory])
        assert "E1M1" in seen
        assert order == ["E1M1"]

    def test_two_maps_in_one_directory(self) -> None:
        directory = [
            _fake_entry("E1M1"),
            _fake_entry("THINGS"),
            _fake_entry("MAP01"),
            _fake_entry("VERTEXES"),
        ]
        seen, order = assemble_maps([directory])
        assert set(order) == {"E1M1", "MAP01"}
        assert len(seen) == 2

    def test_pwad_overwrites_base(self) -> None:
        """Later directory (PWAD) wins for the same map name."""
        base_dir = [_fake_entry("E1M1"), _fake_entry("THINGS")]
        pwad_dir = [_fake_entry("E1M1"), _fake_entry("VERTEXES")]
        seen, order = assemble_maps([base_dir, pwad_dir])
        assert order == ["E1M1"]
        # The map entry from pwad_dir should win; it has VERTEXES, not THINGS
        map_entry = seen["E1M1"]
        assert map_entry.vertices is not None
        assert map_entry.things is None

    def test_pwad_adds_new_map(self) -> None:
        """PWAD can add a map not in the base."""
        base_dir = [_fake_entry("E1M1")]
        pwad_dir = [_fake_entry("E1M2")]
        _, order = assemble_maps([base_dir, pwad_dir])
        assert set(order) == {"E1M1", "E1M2"}

    def test_order_preserves_first_seen(self) -> None:
        """Map names appear in order of first encounter, not last write."""
        base_dir = [_fake_entry("MAP01"), _fake_entry("MAP02")]
        pwad_dir = [_fake_entry("MAP01")]
        _, order = assemble_maps([base_dir, pwad_dir])
        assert order.index("MAP01") < order.index("MAP02")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FW:
    """Minimal fake WadFile stub — only needs .fd for read_bytes()."""

    def __init__(self) -> None:
        self.fd = BytesIO(b"")


def _fake_entry(name: str) -> DirectoryEntry:
    """Build a zero-size DirectoryEntry with the given name, no real WAD needed."""
    return DirectoryEntry(_FW(), 0, 0, name)  # type: ignore[arg-type]


def _build_single_lump_wad(name: bytes, data: bytes) -> bytes:
    """Build a minimal PWAD with a single lump."""
    assert len(name) == 8, f"name must be exactly 8 bytes, got {len(name)}"
    header_size = 12
    data_offset = header_size
    dir_offset = data_offset + len(data)
    # header: magic(4) + num_lumps(4) + dir_offset(4)
    header = b"PWAD" + struct.pack("<II", 1, dir_offset)
    # directory entry: offset(4) + size(4) + name(8)
    dir_entry = struct.pack("<II", data_offset, len(data)) + name
    return header + data + dir_entry
