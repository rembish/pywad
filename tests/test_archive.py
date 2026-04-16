"""Tests for the unified WadArchive interface."""

from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path

import pytest

from wadlib.archive import LumpInfo, WadArchive
from wadlib.enums import WadType
from wadlib.wad import WadFile
from wadlib.writer import WadWriter

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# LumpInfo
# ---------------------------------------------------------------------------


class TestLumpInfo:
    def test_creation(self) -> None:
        info = LumpInfo(name="PLAYPAL", size=10752, index=0)
        assert info.name == "PLAYPAL"
        assert info.size == 10752
        assert info.index == 0

    def test_repr(self) -> None:
        info = LumpInfo(name="TEST", size=42, index=1)
        assert "TEST" in repr(info)
        assert "42" in repr(info)

    def test_frozen(self) -> None:
        info = LumpInfo(name="X", size=0, index=0)
        with pytest.raises(AttributeError):
            info.name = "Y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# WadArchive — invalid modes
# ---------------------------------------------------------------------------


class TestArchiveModes:
    def test_invalid_mode(self) -> None:
        with pytest.raises(ValueError, match="Invalid mode"):
            WadArchive("dummy.wad", mode="x")  # type: ignore[arg-type]

    def test_repr_open(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                assert "mode='w'" in repr(wad)
        finally:
            os.unlink(path)

    def test_repr_closed(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            wad = WadArchive(path, "w")
            wad.close()
            assert "closed" in repr(wad)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# WadArchive — write mode
# ---------------------------------------------------------------------------


class TestWriteMode:
    def test_write_and_read_back(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                assert wad.mode == "w"
                assert wad.wad_type == WadType.PWAD
                wad.writestr("HELLO", b"world")
                wad.writemarker("MAP01")
                wad.writestr("THINGS", b"\x00" * 10)

            # Re-open in read mode
            with WadArchive(path, "r") as wad:
                assert wad.mode == "r"
                assert wad.wad_type == WadType.PWAD
                assert len(wad) == 3
                assert wad.namelist() == ["HELLO", "MAP01", "THINGS"]
                assert wad.read("HELLO") == b"world"
                assert wad.read("MAP01") == b""
                assert wad.read("THINGS") == b"\x00" * 10
        finally:
            os.unlink(path)

    def test_write_iwad(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w", wad_type=WadType.IWAD) as wad:
                wad.writestr("TEST", b"data")

            with WadArchive(path, "r") as wad:
                assert wad.wad_type == WadType.IWAD
        finally:
            os.unlink(path)

    def test_write_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".lmp", delete=False) as lmp:
            lmp.write(b"file_contents")
            lmp_path = lmp.name

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad_path = f.name

        try:
            with WadArchive(wad_path, "w") as wad:
                wad.write(lmp_path, arcname="FILELMP")

            with WadArchive(wad_path, "r") as wad:
                assert wad.read("FILELMP") == b"file_contents"
        finally:
            os.unlink(lmp_path)
            os.unlink(wad_path)

    def test_write_from_file_auto_name(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix=".lmp", prefix="TESTLMP_", delete=False, dir="/tmp"
        ) as lmp:
            lmp.write(b"auto")
            lmp_path = lmp.name

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad_path = f.name

        try:
            with WadArchive(wad_path, "w") as wad:
                wad.write(lmp_path)

            with WadArchive(wad_path, "r") as wad:
                names = wad.namelist()
                assert len(names) == 1
                assert wad.read(names[0]) == b"auto"
        finally:
            os.unlink(lmp_path)
            os.unlink(wad_path)

    def test_read_on_write_mode_raises(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                with pytest.raises(ValueError, match="read operation"):
                    wad.namelist()
                with pytest.raises(ValueError, match="read operation"):
                    wad.read("X")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# WadArchive — read mode
# ---------------------------------------------------------------------------


class TestReadMode:
    def _make_wad(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"aaa")
            wad.writemarker("MAP01")
            wad.writestr("THINGS", b"\x01" * 20)
            wad.writestr("BETA", b"bbb")
        return path

    def test_namelist(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                assert wad.namelist() == ["ALPHA", "MAP01", "THINGS", "BETA"]
        finally:
            os.unlink(path)

    def test_infolist(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                infos = wad.infolist()
                assert len(infos) == 4
                assert infos[0].name == "ALPHA"
                assert infos[0].size == 3
                assert infos[0].index == 0
                assert infos[1].name == "MAP01"
                assert infos[1].size == 0
        finally:
            os.unlink(path)

    def test_getinfo(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                info = wad.getinfo("ALPHA")
                assert info.name == "ALPHA"
                assert info.size == 3
        finally:
            os.unlink(path)

    def test_getinfo_missing(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad, pytest.raises(KeyError):
                wad.getinfo("MISSING")
        finally:
            os.unlink(path)

    def test_read(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                assert wad.read("ALPHA") == b"aaa"
                assert wad.read("BETA") == b"bbb"
        finally:
            os.unlink(path)

    def test_read_missing(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad, pytest.raises(KeyError):
                wad.read("MISSING")
        finally:
            os.unlink(path)

    def test_read_case_insensitive(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                assert wad.read("alpha") == b"aaa"
        finally:
            os.unlink(path)

    def test_contains(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                assert "ALPHA" in wad
                assert "alpha" in wad
                assert "MISSING" not in wad
        finally:
            os.unlink(path)

    def test_len(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                assert len(wad) == 4
        finally:
            os.unlink(path)

    def test_iteration(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                names = [info.name for info in wad]
                assert names == ["ALPHA", "MAP01", "THINGS", "BETA"]
        finally:
            os.unlink(path)

    def test_write_on_read_mode_raises(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path) as wad:
                with pytest.raises(ValueError, match="write operation"):
                    wad.writestr("X", b"x")
                with pytest.raises(ValueError, match="write operation"):
                    wad.writemarker("X")
                with pytest.raises(ValueError, match="write operation"):
                    wad.remove("ALPHA")
                with pytest.raises(ValueError, match="write operation"):
                    wad.replace("ALPHA", b"new")
        finally:
            os.unlink(path)

    def test_operations_on_closed_raises(self) -> None:
        path = self._make_wad()
        try:
            wad = WadArchive(path)
            wad.close()
            with pytest.raises(ValueError, match="closed"):
                wad.namelist()
            with pytest.raises(ValueError, match="closed"):
                wad.writestr("X", b"x")
        finally:
            os.unlink(path)

    def test_getinfo_duplicate_matches_read(self) -> None:
        """getinfo() must return the last duplicate lump, consistent with read()."""
        # Build a raw WAD with two DUP lumps of different sizes (3 and 5 bytes).
        lump1 = b"aaa"
        lump2 = b"bbbbb"
        lumps_data = lump1 + lump2
        dir_offset = 12 + len(lumps_data)
        header = struct.pack("<4sII", b"PWAD", 2, dir_offset)

        def _entry(offset: int, size: int, name: str) -> bytes:
            return struct.pack("<II8s", offset, size, name.encode().ljust(8, b"\x00")[:8])

        directory = _entry(12, len(lump1), "DUP") + _entry(12 + len(lump1), len(lump2), "DUP")
        raw = header + lumps_data + directory

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
            f.write(raw)
        try:
            with WadArchive(path) as wad:
                info = wad.getinfo("DUP")
                data = wad.read("DUP")
                # Both must agree: last entry wins (size=5, data=b"bbbbb")
                assert info.size == len(lump2)
                assert data == lump2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# WadArchive — append mode
# ---------------------------------------------------------------------------


class TestAppendMode:
    def _make_wad(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"original")
            wad.writestr("BETA", b"keep")
        return path

    def test_append_read_existing(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path, "a") as wad:
                assert wad.namelist() == ["ALPHA", "BETA"]
                assert wad.read("ALPHA") == b"original"
        finally:
            os.unlink(path)

    def test_append_add_lump(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path, "a") as wad:
                wad.writestr("GAMMA", b"new")

            with WadArchive(path, "r") as wad:
                assert "GAMMA" in wad
                assert wad.read("GAMMA") == b"new"
                assert wad.read("ALPHA") == b"original"
        finally:
            os.unlink(path)

    def test_append_replace_lump(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path, "a") as wad:
                assert wad.replace("ALPHA", b"modified")

            with WadArchive(path, "r") as wad:
                assert wad.read("ALPHA") == b"modified"
                assert wad.read("BETA") == b"keep"
        finally:
            os.unlink(path)

    def test_append_remove_lump(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path, "a") as wad:
                assert wad.remove("ALPHA")

            with WadArchive(path, "r") as wad:
                assert "ALPHA" not in wad
                assert wad.read("BETA") == b"keep"
        finally:
            os.unlink(path)

    def test_append_contains(self) -> None:
        path = self._make_wad()
        try:
            with WadArchive(path, "a") as wad:
                assert "ALPHA" in wad
                assert "MISSING" not in wad
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# WadArchive — extract
# ---------------------------------------------------------------------------


class TestExtract:
    def _make_wad(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"aaa")
            wad.writemarker("MAP01")
            wad.writestr("BETA", b"bbb")
        return path

    def test_extract_single(self) -> None:
        wad_path = self._make_wad()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with WadArchive(wad_path) as wad:
                    result = wad.extract("ALPHA", tmpdir)
                    assert os.path.isfile(result)
                    assert result.endswith("ALPHA.lmp")
                    with open(result, "rb") as f:
                        assert f.read() == b"aaa"
            finally:
                os.unlink(wad_path)

    def test_extractall(self) -> None:
        wad_path = self._make_wad()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with WadArchive(wad_path) as wad:
                    files = wad.extractall(tmpdir)
                    # MAP01 is a marker (size 0) — should be skipped
                    assert len(files) == 2
                    names = [os.path.basename(f) for f in files]
                    assert "ALPHA.lmp" in names
                    assert "BETA.lmp" in names
            finally:
                os.unlink(wad_path)


# ---------------------------------------------------------------------------
# WadArchive — real WAD round-trip
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealWadArchive:
    def test_read_real_wad(self) -> None:
        with WadArchive(FREEDOOM2) as wad:
            names = wad.namelist()
            assert len(names) > 100
            assert "PLAYPAL" in names
            playpal = wad.read("PLAYPAL")
            assert len(playpal) == 10752  # 14 palettes x 768

    def test_infolist_real_wad(self) -> None:
        with WadArchive(FREEDOOM2) as wad:
            infos = wad.infolist()
            playpal = next(i for i in infos if i.name == "PLAYPAL")
            assert playpal.size == 10752

    def test_iteration_real_wad(self) -> None:
        with WadArchive(FREEDOOM2) as wad:
            count = sum(1 for _ in wad)
            assert count == len(wad)

    def test_contains_real_wad(self) -> None:
        with WadArchive(FREEDOOM2) as wad:
            assert "PLAYPAL" in wad
            assert "NONEXISTENT_LUMP" not in wad

    def test_round_trip_real_wad(self) -> None:
        """Append mode round-trip: open, add a lump, verify both old and new."""
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            copy_path = f.name

        try:
            # First create a copy via append
            with WadArchive(FREEDOOM2) as src:
                orig_names = src.namelist()
                orig_playpal = src.read("PLAYPAL")

            # Use writer to make a copy, then append
            with WadFile(FREEDOOM2) as wf:
                w = WadWriter.from_wad(wf)
                w.save(copy_path)

            with WadArchive(copy_path, "a") as wad:
                wad.writestr("NEWLUMP", b"hello from archive")

            with WadArchive(copy_path, "r") as wad:
                assert wad.read("PLAYPAL") == orig_playpal
                assert wad.read("NEWLUMP") == b"hello from archive"
                assert len(wad) == len(orig_names) + 1
        finally:
            os.unlink(copy_path)


# ---------------------------------------------------------------------------
# WadArchive — exception safety and write-mode coverage
# ---------------------------------------------------------------------------


class TestExceptionSafety:
    def test_exit_with_exception_does_not_commit(self, tmp_path: Path) -> None:
        """An exception inside the with block must not write the file."""
        path = str(tmp_path / "test.wad")

        # Write a known file.
        with WadArchive(path, "w") as wad:
            wad.writestr("ORIG", b"original", validate=False)

        original_size = os.path.getsize(path)

        with pytest.raises(RuntimeError), WadArchive(path, "a") as wad:
            wad.writestr("NEW", b"new data", validate=False)
            raise RuntimeError("abort!")

        # File must not have grown.
        assert os.path.getsize(path) == original_size

    def test_exit_with_exception_read_mode(self, tmp_path: Path) -> None:
        """Exception in read mode does not crash __exit__."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("X", b"x", validate=False)

        with pytest.raises(KeyError), WadArchive(path, "r") as wad:
            _ = wad.read("MISSING")

    def test_wad_type_in_write_mode(self, tmp_path: Path) -> None:
        """wad_type property is accessible before save in write mode."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w", wad_type=WadType.PWAD) as wad:
            assert wad.wad_type == WadType.PWAD
            wad.writestr("X", b"x", validate=False)

    def test_infolist_in_append_mode(self, tmp_path: Path) -> None:
        """infolist() works in append mode (via writer path)."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"aaa", validate=False)

        with WadArchive(path, "a") as wad:
            wad.writestr("BETA", b"bbb", validate=False)
            infos = wad.infolist()
            assert len(infos) == 2
            assert infos[0].name == "ALPHA"
            assert infos[1].name == "BETA"

    def test_read_missing_in_append_mode(self, tmp_path: Path) -> None:
        """Reading a non-existent lump in append mode raises KeyError."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"aaa", validate=False)

        with WadArchive(path, "a") as wad, pytest.raises(KeyError):
            wad.read("MISSING")

    def test_contains_in_append_mode(self, tmp_path: Path) -> None:
        """__contains__ resolves via the writer in append mode."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"aaa", validate=False)

        with WadArchive(path, "a") as wad:
            wad.writestr("BETA", b"bbb", validate=False)
            assert "ALPHA" in wad
            assert "BETA" in wad
            assert "MISSING" not in wad

    def test_filename_property(self, tmp_path: Path) -> None:
        """filename property returns the path passed to the constructor."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("X", b"x", validate=False)
            assert wad.filename == path

    def test_double_close_is_safe(self, tmp_path: Path) -> None:
        """Calling close() twice must not raise."""
        path = str(tmp_path / "test.wad")
        wad = WadArchive(path, "w")
        wad.writestr("X", b"x", validate=False)
        wad.close()
        wad.close()  # covers the early-return branch in close()

    def test_contains_write_mode_returns_false(self, tmp_path: Path) -> None:
        """__contains__ on a write-only archive returns False instead of raising."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("X", b"x", validate=False)
            assert "X" not in wad  # write mode → _check_readable raises ValueError → except → False

    def test_write_and_writemarker_skip_validation(self, tmp_path: Path) -> None:
        """validate=False bypasses validation in write() and writemarker()."""
        src = str(tmp_path / "src.lmp")
        wad_path = str(tmp_path / "test.wad")
        Path(src).write_bytes(b"data")
        with WadArchive(wad_path, "w") as wad:
            wad.write(src, arcname="SRCFILE", validate=False)
            wad.writemarker("MAP01", validate=False)
        with WadArchive(wad_path) as wad:
            assert "SRCFILE" in wad
            assert "MAP01" in wad

    def test_replace_skip_validation(self, tmp_path: Path) -> None:
        """validate=False bypasses validation in replace()."""
        path = str(tmp_path / "test.wad")
        with WadArchive(path, "w") as wad:
            wad.writestr("ALPHA", b"original", validate=False)
        with WadArchive(path, "a") as wad:
            assert wad.replace("ALPHA", b"new", validate=False)
        with WadArchive(path) as wad:
            assert wad.read("ALPHA") == b"new"


# ---------------------------------------------------------------------------
# WadArchive — duplicate-lump semantics across modes
# ---------------------------------------------------------------------------


class TestDuplicateLumpSemantics:
    """Duplicate-lump resolution must be last-entry-wins in every mode."""

    def _make_dup_wad(self, tmp_path: Path) -> str:
        """Build a WAD containing two lumps both named DUP."""
        path = str(tmp_path / "dup.wad")
        writer = WadWriter(WadType.PWAD)
        writer.add_lump("DUP", b"first")
        writer.add_lump("DUP", b"second")
        writer.save(path)
        return path

    def test_read_mode_last_wins(self, tmp_path: Path) -> None:
        path = self._make_dup_wad(tmp_path)
        with WadArchive(path, "r") as wad:
            assert wad.read("DUP") == b"second"

    def test_append_mode_last_wins(self, tmp_path: Path) -> None:
        path = self._make_dup_wad(tmp_path)
        with WadArchive(path, "a") as wad:
            assert wad.read("DUP") == b"second"

    def test_read_and_append_modes_agree(self, tmp_path: Path) -> None:
        """read() must return the same bytes regardless of open mode."""
        path = self._make_dup_wad(tmp_path)
        with WadArchive(path, "r") as r_wad:
            from_read = r_wad.read("DUP")
        with WadArchive(path, "a") as a_wad:
            from_append = a_wad.read("DUP")
        assert from_read == from_append

    def test_getinfo_and_read_agree_in_append_mode(self, tmp_path: Path) -> None:
        """getinfo() and read() must point at the same entry in append mode."""
        path = self._make_dup_wad(tmp_path)
        with WadArchive(path, "a") as wad:
            info = wad.getinfo("DUP")
            data = wad.read("DUP")
        assert info.size == len(data)
        assert data == b"second"

    def test_append_mode_new_dup_last_wins(self, tmp_path: Path) -> None:
        """Writing a new DUP in append mode makes it the last-wins entry."""
        path = self._make_dup_wad(tmp_path)
        with WadArchive(path, "a") as wad:
            wad.writestr("DUP", b"third", validate=False)
        with WadArchive(path, "r") as wad:
            assert wad.read("DUP") == b"third"
