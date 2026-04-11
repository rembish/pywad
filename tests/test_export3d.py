"""Tests for 3D OBJ mesh exporter."""

from __future__ import annotations

import os
import tempfile

import pytest

from wadlib.export3d import map_to_obj
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestExport3d:
    def test_basic_export(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            assert isinstance(obj, str)
            assert obj.startswith("#")
            assert "\nv " in obj
            assert "\nf " in obj

    def test_vertices_present(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            v_lines = [l for l in obj.splitlines() if l.startswith("v ")]
            assert len(v_lines) > 100  # MAP01 has many vertices

    def test_faces_present(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            f_lines = [l for l in obj.splitlines() if l.startswith("f ")]
            assert len(f_lines) > 50

    def test_scale_factor(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            obj1 = map_to_obj(wad.maps[0], scale=1.0)
            obj2 = map_to_obj(wad.maps[0], scale=0.01)
            # Scaled version should have smaller vertex values
            v1 = [l for l in obj1.splitlines() if l.startswith("v ")][0]
            v2 = [l for l in obj2.splitlines() if l.startswith("v ")][0]
            val1 = float(v1.split()[1])
            val2 = float(v2.split()[1])
            assert abs(val2) < abs(val1) or val1 == 0.0

    def test_with_materials(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            result = map_to_obj(wad.maps[0], materials=True)
            assert isinstance(result, tuple)
            obj, mtl = result
            assert "mtllib" in obj
            assert "usemtl" in obj
            assert "newmtl" in mtl

    def test_save_to_file(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            with tempfile.NamedTemporaryFile(suffix=".obj", mode="w", delete=False) as f:
                f.write(obj)
                path = f.name
            try:
                assert os.path.getsize(path) > 1000
            finally:
                os.unlink(path)

    def test_multiple_maps(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            for m in wad.maps[:3]:
                obj = map_to_obj(m)
                assert "v " in obj
                assert "f " in obj

    def test_obj_format_valid(self) -> None:
        """Check that OBJ output follows basic format rules."""
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            for line in obj.splitlines():
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

    def test_face_indices_in_range(self) -> None:
        """All face vertex indices must reference valid vertices."""
        with WadFile(FREEDOOM2) as wad:
            obj = map_to_obj(wad.maps[0])
            v_count = sum(1 for l in obj.splitlines() if l.startswith("v "))
            for line in obj.splitlines():
                if line.startswith("f "):
                    for p in line.split()[1:]:
                        idx = int(p.split("/")[0])
                        assert 1 <= idx <= v_count, f"Index {idx} out of range (1..{v_count})"
