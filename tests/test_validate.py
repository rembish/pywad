"""Tests for lump validation."""

from __future__ import annotations

import os
import tempfile

import pytest

from wadlib.archive import WadArchive
from wadlib.validate import (
    InvalidLumpError,
    Severity,
    validate_lump,
    validate_name,
    validate_wad,
)
from wadlib.writer import WadWriter

# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------


class TestValidateName:
    def test_valid_names(self) -> None:
        for name in ("PLAYPAL", "MAP01", "E1M1", "THINGS", "F_START", "A"):
            assert validate_name(name) == [], f"Expected no issues for {name!r}"

    def test_empty_name(self) -> None:
        issues = validate_name("")
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR
        assert "empty" in issues[0].message

    def test_too_long(self) -> None:
        issues = validate_name("TOOLONGNAME")
        assert any(i.severity == Severity.ERROR and "too long" in i.message for i in issues)

    def test_lowercase_warning(self) -> None:
        issues = validate_name("playpal")
        assert any(i.severity == Severity.WARNING and "lowercase" in i.message for i in issues)

    def test_invalid_chars(self) -> None:
        issues = validate_name("BAD NAME")  # space
        assert any(
            i.severity == Severity.ERROR and "invalid characters" in i.message for i in issues
        )

    def test_special_chars_allowed(self) -> None:
        # These are valid in WAD names
        assert validate_name("A-B_C") == []
        assert validate_name("X[1]") == []


# ---------------------------------------------------------------------------
# Lump data validation — map lumps
# ---------------------------------------------------------------------------


class TestValidateLumpMapData:
    def test_things_valid(self) -> None:
        data = b"\x00" * 30  # 3 things x 10 bytes
        issues = validate_lump("THINGS", data)
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_things_invalid_size(self) -> None:
        data = b"\x00" * 7  # not a multiple of 10
        issues = validate_lump("THINGS", data)
        assert any(i.severity == Severity.ERROR and "multiple of 10" in i.message for i in issues)

    def test_hexen_things_valid(self) -> None:
        data = b"\x00" * 60  # 3 things x 20 bytes
        issues = validate_lump("THINGS", data, hexen=True)
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_hexen_things_invalid(self) -> None:
        data = b"\x00" * 15  # not a multiple of 20
        issues = validate_lump("THINGS", data, hexen=True)
        assert any(i.severity == Severity.ERROR and "multiple of 20" in i.message for i in issues)

    def test_vertexes_valid(self) -> None:
        data = b"\x00" * 16  # 4 vertices x 4 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("VERTEXES", data))

    def test_vertexes_invalid(self) -> None:
        data = b"\x00" * 5
        issues = validate_lump("VERTEXES", data)
        assert any(i.severity == Severity.ERROR for i in issues)

    def test_linedefs_valid(self) -> None:
        data = b"\x00" * 28  # 2 linedefs x 14 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("LINEDEFS", data))

    def test_linedefs_invalid(self) -> None:
        data = b"\x00" * 15  # not a multiple of 14
        issues = validate_lump("LINEDEFS", data)
        assert any(i.severity == Severity.ERROR for i in issues)

    def test_hexen_linedefs_valid(self) -> None:
        data = b"\x00" * 32  # 2 x 16 bytes
        issues = validate_lump("LINEDEFS", data, hexen=True)
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_sidedefs_valid(self) -> None:
        data = b"\x00" * 60  # 2 sidedefs x 30 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("SIDEDEFS", data))

    def test_sectors_valid(self) -> None:
        data = b"\x00" * 52  # 2 sectors x 26 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("SECTORS", data))

    def test_segs_valid(self) -> None:
        data = b"\x00" * 24  # 2 segs x 12 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("SEGS", data))

    def test_nodes_valid(self) -> None:
        data = b"\x00" * 56  # 2 nodes x 28 bytes
        assert not any(i.severity == Severity.ERROR for i in validate_lump("NODES", data))


# ---------------------------------------------------------------------------
# Lump data validation — fixed-size lumps
# ---------------------------------------------------------------------------


class TestValidateFixedSize:
    def test_colormap_valid(self) -> None:
        data = b"\x00" * 8704
        assert not any(i.severity == Severity.ERROR for i in validate_lump("COLORMAP", data))

    def test_colormap_invalid(self) -> None:
        data = b"\x00" * 100
        issues = validate_lump("COLORMAP", data)
        assert any(i.severity == Severity.ERROR and "8704" in i.message for i in issues)

    def test_endoom_valid(self) -> None:
        data = b"\x00" * 4000
        assert not any(i.severity == Severity.ERROR for i in validate_lump("ENDOOM", data))

    def test_endoom_invalid(self) -> None:
        data = b"\x00" * 3999
        issues = validate_lump("ENDOOM", data)
        assert any(i.severity == Severity.ERROR and "4000" in i.message for i in issues)

    def test_playpal_valid(self) -> None:
        data = b"\x00" * (768 * 14)
        assert not any(i.severity == Severity.ERROR for i in validate_lump("PLAYPAL", data))

    def test_playpal_invalid(self) -> None:
        data = b"\x00" * 100
        issues = validate_lump("PLAYPAL", data)
        assert any(i.severity == Severity.ERROR and "multiple of 768" in i.message for i in issues)


# ---------------------------------------------------------------------------
# Flat and picture validation
# ---------------------------------------------------------------------------


class TestValidateFlat:
    def test_flat_valid(self) -> None:
        data = b"\x00" * 4096
        assert not any(
            i.severity == Severity.ERROR for i in validate_lump("FLOOR1", data, is_flat=True)
        )

    def test_flat_invalid_size(self) -> None:
        data = b"\x00" * 100
        issues = validate_lump("FLOOR1", data, is_flat=True)
        assert any(i.severity == Severity.ERROR and "4096" in i.message for i in issues)


class TestValidatePicture:
    def test_picture_too_small(self) -> None:
        data = b"\x00" * 4
        issues = validate_lump("TROOA1", data, is_picture=True)
        assert any(i.severity == Severity.ERROR and "too small" in i.message for i in issues)

    def test_picture_zero_dimension(self) -> None:
        # width=0, height=10, offsets=0,0
        data = b"\x00\x00\x0a\x00\x00\x00\x00\x00"
        issues = validate_lump("TROOA1", data, is_picture=True)
        assert any(i.severity == Severity.ERROR and "zero dimension" in i.message for i in issues)

    def test_picture_valid_header(self) -> None:
        # width=2, height=2, left=0, top=0, + 2 column offsets (8 bytes)
        import struct

        header = struct.pack("<HHhh", 2, 2, 0, 0)
        col_offsets = struct.pack("<II", 16, 16)
        # minimal column data: topdelta=0, length=2, pad, px, px, pad, 0xFF
        col_data = bytes([0, 2, 0, 0, 0, 0, 0xFF])
        data = header + col_offsets + col_data
        issues = validate_lump("TEST", data, is_picture=True)
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_picture_truncated_columns(self) -> None:
        # width=100 but only 8+4 bytes total (not enough for 100 column offsets)
        import struct

        header = struct.pack("<HHhh", 100, 10, 0, 0)
        data = header + b"\x00" * 4  # way too short for 100 * 4 = 400 byte offset table
        issues = validate_lump("TEST", data, is_picture=True)
        assert any(i.severity == Severity.ERROR and "column offsets" in i.message for i in issues)


# ---------------------------------------------------------------------------
# Empty data
# ---------------------------------------------------------------------------


class TestValidateEmptyData:
    def test_empty_is_always_valid(self) -> None:
        # Empty data is valid for markers
        assert not any(i.severity == Severity.ERROR for i in validate_lump("MAP01", b""))

    def test_unknown_lump_no_errors(self) -> None:
        # Unknown lump names with arbitrary data should not error
        data = b"\x42" * 100
        issues = validate_lump("CUSTOM", data)
        assert not any(i.severity == Severity.ERROR for i in issues)


# ---------------------------------------------------------------------------
# WAD structural validation
# ---------------------------------------------------------------------------


class TestValidateWad:
    def test_valid_wad(self) -> None:
        w = WadWriter()
        w.add_lump("PLAYPAL", b"\x00" * 768)
        w.add_marker("MAP01")
        w.add_lump("THINGS", b"\x00" * 10)
        w.add_lump("LINEDEFS", b"\x00" * 14)
        w.add_lump("SIDEDEFS", b"\x00" * 30)
        w.add_lump("VERTEXES", b"\x00" * 4)
        w.add_lump("SECTORS", b"\x00" * 26)
        issues = validate_wad(w)
        assert not any(i.severity == Severity.ERROR for i in issues)

    def test_unpaired_namespace_start(self) -> None:
        w = WadWriter()
        w.add_marker("F_START")
        w.add_lump("FLAT1", b"\x00" * 4096)
        # Missing F_END
        issues = validate_wad(w)
        assert any(i.severity == Severity.ERROR and "F_END" in i.message for i in issues)

    def test_unpaired_namespace_end(self) -> None:
        w = WadWriter()
        w.add_marker("S_END")
        # Missing S_START
        issues = validate_wad(w)
        assert any(i.severity == Severity.ERROR and "S_START" in i.message for i in issues)

    def test_reversed_namespace(self) -> None:
        w = WadWriter()
        w.add_marker("F_END")
        w.add_marker("F_START")
        issues = validate_wad(w)
        assert any(i.severity == Severity.ERROR and "appears after" in i.message for i in issues)

    def test_orphan_map_data(self) -> None:
        w = WadWriter()
        w.add_lump("THINGS", b"\x00" * 10)  # no map marker before it
        issues = validate_wad(w)
        assert any(
            i.severity == Severity.WARNING and "outside a map block" in i.message for i in issues
        )


# ---------------------------------------------------------------------------
# WadArchive integration
# ---------------------------------------------------------------------------


class TestArchiveValidation:
    def test_writestr_rejects_bad_name(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad, pytest.raises(InvalidLumpError):
                wad.writestr("TOOLONGNAME", b"x")
        finally:
            os.unlink(path)

    def test_writestr_rejects_bad_size(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with (
                WadArchive(path, "w") as wad,
                pytest.raises(InvalidLumpError, match="multiple of 10"),
            ):
                wad.writestr("THINGS", b"\x00" * 7)
        finally:
            os.unlink(path)

    def test_writestr_skip_validation(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                # This should NOT raise because validate=False
                wad.writestr("THINGS", b"\x00" * 7, validate=False)
                assert len(wad) == 1
        finally:
            os.unlink(path)

    def test_writestr_accepts_valid(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("THINGS", b"\x00" * 20)  # 2 valid things
                wad.writestr("PLAYPAL", b"\x00" * 768)
                wad.writestr("CUSTOM", b"anything goes")
        finally:
            os.unlink(path)

    def test_writestr_flat_validation(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                with pytest.raises(InvalidLumpError, match="4096"):
                    wad.writestr("FLOOR1", b"\x00" * 100, is_flat=True)
                # Correct size passes
                wad.writestr("FLOOR1", b"\x00" * 4096, is_flat=True)
        finally:
            os.unlink(path)

    def test_replace_validates(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("THINGS", b"\x00" * 10)

            with WadArchive(path, "a") as wad:
                with pytest.raises(InvalidLumpError):
                    wad.replace("THINGS", b"\x00" * 7)
                # Valid replacement works
                assert wad.replace("THINGS", b"\x00" * 20)
        finally:
            os.unlink(path)

    def test_writemarker_validates_name(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                with pytest.raises(InvalidLumpError):
                    wad.writemarker("BAD NAME!")
                wad.writemarker("MAP01")  # valid
        finally:
            os.unlink(path)
