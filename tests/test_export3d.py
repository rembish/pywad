"""Tests for 3D OBJ mesh exporter."""

from __future__ import annotations

import os
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
# Module-scoped fixtures — expensive exports computed once, shared by all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _obj_map01() -> str:
    """OBJ string for freedoom2 MAP01 at default scale — computed once."""
    if not _has_wad(FREEDOOM2):
        pytest.skip("freedoom2.wad not available")
    with WadFile(FREEDOOM2) as wad:
        return cast(str, map_to_obj(wad.maps[0]))


@pytest.fixture(scope="module")
def _obj_map01_mtl() -> tuple[str, str]:
    """(OBJ, MTL) strings for freedoom2 MAP01 with materials — computed once."""
    if not _has_wad(FREEDOOM2):
        pytest.skip("freedoom2.wad not available")
    with WadFile(FREEDOOM2) as wad:
        return cast(tuple[str, str], map_to_obj(wad.maps[0], materials=True))


@pytest.fixture(scope="module")
def _map01_entry() -> BaseMapEntry:
    """MAP01 entry with all lump data buffered — WAD can close afterwards."""
    if not _has_wad(FREEDOOM2):
        pytest.skip("freedoom2.wad not available")
    with WadFile(FREEDOOM2) as wad:
        return wad.maps[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


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

    @pytest.mark.slow
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

    @pytest.mark.slow
    def test_multiple_maps(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            for m in wad.maps[:3]:
                obj = cast(str, map_to_obj(m))
                assert "v " in obj
                assert "f " in obj

    def test_obj_format_valid(self, _obj_map01: str) -> None:
        """Check that OBJ output follows basic format rules."""
        for line in _obj_map01.splitlines():
            if line.startswith("v "):
                parts = line.split()
                assert len(parts) == 4  # v x y z
                float(parts[1])
                float(parts[2])
                float(parts[3])
            elif line.startswith("f "):
                parts = line.split()
                assert len(parts) >= 4  # f v1 v2 v3 [v4]
                for p in parts[1:]:
                    idx = int(p.split("/")[0])
                    assert idx >= 1  # OBJ indices are 1-based

    def test_face_indices_in_range(self, _obj_map01: str) -> None:
        """All face vertex indices must reference valid vertices."""
        v_count = sum(1 for line in _obj_map01.splitlines() if line.startswith("v "))
        for line in _obj_map01.splitlines():
            if line.startswith("f "):
                for p in line.split()[1:]:
                    idx = int(p.split("/")[0])
                    assert 1 <= idx <= v_count, f"Index {idx} out of range (1..{v_count})"
