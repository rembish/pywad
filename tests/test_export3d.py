"""Tests for 3D OBJ mesh exporter."""

from __future__ import annotations

import os
import struct
import tempfile
from typing import cast

import pytest

from wadlib.export3d import map_to_obj
from wadlib.lumps.map import BaseMapEntry
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Minimal synthetic WAD — fast fixture for format-correctness tests
# ---------------------------------------------------------------------------


def _build_box_wad_bytes() -> bytes:
    """Build a minimal 1-sector box PWAD usable by map_to_obj.

    Includes SEGS + SSECTORS so that floor/ceiling polygons are also generated.
    """
    # THINGS: one Player-1 start at centre
    things = struct.pack("<hhHHH", 64, 64, 90, 1, 7)

    # VERTEXES: (0,0), (128,0), (128,128), (0,128)
    verts = b"".join(struct.pack("<hh", x, y) for x, y in [(0, 0), (128, 0), (128, 128), (0, 128)])

    # SIDEDEFS: 4, each pointing to sector 0 with a mid texture
    # sidedef: x_off(h), y_off(h), upper(8s), lower(8s), mid(8s), sector(H)
    mid_tex = b"STARTAN2"
    null_tex = b"-\x00\x00\x00\x00\x00\x00\x00"
    sidedefs = b""
    for _ in range(4):
        sidedefs += struct.pack("<hh", 0, 0) + null_tex + null_tex + mid_tex + struct.pack("<H", 0)

    # LINEDEFS: 4 single-sided walls
    linedefs = b""
    for i, (v1, v2) in enumerate([(0, 1), (1, 2), (2, 3), (3, 0)]):
        linedefs += struct.pack("<HHHHHhh", v1, v2, 1, 0, 0, i, -1)

    # SECTORS: 1 sector, floor=0, ceil=128
    flat = b"FLAT1\x00\x00\x00"
    sectors = struct.pack("<hh", 0, 128) + flat + flat + struct.pack("<HHH", 200, 0, 0)

    # SEGS: 4 segs (one per linedef) — format: <HHHHHh
    # start_v, end_v, angle, linedef, direction, offset
    segs = b""
    for i, (v1, v2) in enumerate([(0, 1), (1, 2), (2, 3), (3, 0)]):
        segs += struct.pack("<HHHHHh", v1, v2, 0, i, 0, 0)

    # SSECTORS: 1 subsector with all 4 segs — format: <HH (count, first_seg)
    ssectors = struct.pack("<HH", 4, 0)

    lumps: list[tuple[str, bytes]] = [
        ("MAP01", b""),
        ("THINGS", things),
        ("LINEDEFS", linedefs),
        ("SIDEDEFS", sidedefs),
        ("VERTEXES", verts),
        ("SEGS", segs),
        ("SSECTORS", ssectors),
        ("SECTORS", sectors),
    ]

    lump_data = b"".join(d for _, d in lumps)
    dir_offset = 12 + len(lump_data)
    header = struct.pack("<4sII", b"PWAD", len(lumps), dir_offset)
    directory = b""
    offset = 12
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.encode().ljust(8, b"\x00")[:8])
        offset += len(data)
    return header + lump_data + directory


@pytest.fixture(scope="module")
def _obj_minimal(tmp_path_factory: pytest.TempPathFactory) -> str:
    """OBJ string from a tiny synthetic box WAD — fast, no real WAD required."""
    tmp = tmp_path_factory.mktemp("box_wad")
    wad_path = str(tmp / "box.wad")
    (tmp / "box.wad").write_bytes(_build_box_wad_bytes())
    with WadFile(wad_path) as wad:
        if not wad.maps:
            return ""
        return cast(str, map_to_obj(wad.maps[0]))


@pytest.fixture(scope="module")
def _obj_minimal_mtl(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    """(OBJ, MTL) from the tiny synthetic box WAD — fast, covers materials path."""
    tmp = tmp_path_factory.mktemp("box_wad_mtl")
    wad_path = str(tmp / "box.wad")
    (tmp / "box.wad").write_bytes(_build_box_wad_bytes())
    with WadFile(wad_path) as wad:
        if not wad.maps:
            return "", ""
        return cast(tuple[str, str], map_to_obj(wad.maps[0], materials=True))


# ---------------------------------------------------------------------------
# Module-scoped fixtures for real-WAD tests (expensive)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _map01_exports() -> tuple[str, tuple[str, str], BaseMapEntry]:
    """All MAP01 export data computed in one WAD open — shared by all tests."""
    if not _has_wad(FREEDOOM2):
        pytest.skip("freedoom2.wad not available")
    with WadFile(FREEDOOM2) as wad:
        m = wad.maps[0]
        obj_plain = cast(str, map_to_obj(m))
        obj_mtl = cast(tuple[str, str], map_to_obj(m, materials=True))
        return obj_plain, obj_mtl, m


@pytest.fixture(scope="module")
def _obj_map01(_map01_exports: tuple[str, tuple[str, str], BaseMapEntry]) -> str:
    return _map01_exports[0]


@pytest.fixture(scope="module")
def _obj_map01_mtl(
    _map01_exports: tuple[str, tuple[str, str], BaseMapEntry],
) -> tuple[str, str]:
    return _map01_exports[1]


@pytest.fixture(scope="module")
def _map01_entry(
    _map01_exports: tuple[str, tuple[str, str], BaseMapEntry],
) -> BaseMapEntry:
    return _map01_exports[2]


# ---------------------------------------------------------------------------
# Tests — format correctness (fast, use minimal synthetic WAD)
# ---------------------------------------------------------------------------


def test_obj_has_vertices_and_faces(_obj_minimal: str) -> None:
    """Minimal box WAD must produce a non-empty OBJ with vertices and faces."""
    assert "\nv " in _obj_minimal
    assert "\nf " in _obj_minimal


def test_obj_format_valid(_obj_minimal: str) -> None:
    """OBJ output must follow basic vertex/face format rules."""
    for line in _obj_minimal.splitlines():
        if line.startswith("v "):
            parts = line.split()
            assert len(parts) == 4, f"Expected 'v x y z', got {line!r}"
            float(parts[1])
            float(parts[2])
            float(parts[3])
        elif line.startswith("f "):
            parts = line.split()
            assert len(parts) >= 4, f"Expected 'f v1 v2 v3 ...', got {line!r}"
            for p in parts[1:]:
                idx = int(p.split("/")[0])
                assert idx >= 1, f"OBJ index {idx} must be 1-based"


def test_face_indices_in_range(_obj_minimal: str) -> None:
    """All face vertex indices must reference defined vertices."""
    v_count = sum(1 for line in _obj_minimal.splitlines() if line.startswith("v "))
    for line in _obj_minimal.splitlines():
        if line.startswith("f "):
            for p in line.split()[1:]:
                idx = int(p.split("/")[0])
                assert 1 <= idx <= v_count, f"Index {idx} out of range (1..{v_count})"


def test_obj_materials_format(_obj_minimal_mtl: tuple[str, str]) -> None:
    """Materials mode returns (OBJ, MTL) tuple with expected keywords."""
    obj, mtl = _obj_minimal_mtl
    assert "mtllib" in obj
    assert "usemtl" in obj
    assert "newmtl" in mtl


# ---------------------------------------------------------------------------
# Tests — real WAD (slow — deselected by default, need freedoom2.wad)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestExport3d:
    def test_basic_export(self, _obj_map01: str) -> None:
        assert isinstance(_obj_map01, str)
        assert _obj_map01.startswith("#")
        assert "\nv " in _obj_map01
        assert "\nf " in _obj_map01

    def test_vertices_present(self, _obj_map01: str) -> None:
        v_lines = [line for line in _obj_map01.splitlines() if line.startswith("v ")]
        assert len(v_lines) > 100  # MAP01 has many vertices

    def test_faces_present(self, _obj_map01: str) -> None:
        f_lines = [line for line in _obj_map01.splitlines() if line.startswith("f ")]
        assert len(f_lines) > 50

    def test_scale_factor(self, _map01_entry: BaseMapEntry) -> None:
        obj1 = cast(str, map_to_obj(_map01_entry, scale=1.0))
        obj2 = cast(str, map_to_obj(_map01_entry, scale=0.01))
        v1 = next(line for line in obj1.splitlines() if line.startswith("v "))
        v2 = next(line for line in obj2.splitlines() if line.startswith("v "))
        val1 = float(v1.split()[1])
        val2 = float(v2.split()[1])
        assert abs(val2) < abs(val1) or val1 == 0.0

    def test_with_materials(self, _obj_map01_mtl: tuple[str, str]) -> None:
        obj, mtl = _obj_map01_mtl
        assert "mtllib" in obj
        assert "usemtl" in obj
        assert "newmtl" in mtl

    def test_save_to_file(self, _obj_map01: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".obj", mode="w", delete=False) as f:
            f.write(_obj_map01)
            path = f.name
        try:
            assert os.path.getsize(path) > 1000
        finally:
            os.unlink(path)

    def test_multiple_maps(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            for m in wad.maps[:3]:
                obj = cast(str, map_to_obj(m))
                assert "v " in obj
                assert "f " in obj
