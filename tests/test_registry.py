"""Tests for wadlib.registry — DecoderRegistry and attach_map_lumps."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from wadlib.lumps.base import BaseLump
from wadlib.lumps.colormap import ColormapLump
from wadlib.lumps.playpal import PlayPal
from wadlib.registry import LUMP_REGISTRY, DecoderRegistry, attach_map_lumps

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
# Helpers
# ---------------------------------------------------------------------------


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
