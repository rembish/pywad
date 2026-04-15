"""Adversarial read-time tests for malformed WADs and hardened edge cases.

These tests verify that:
- Non-ASCII magic bytes raise WadFormatError, not UnicodeDecodeError
- Non-ASCII lump names raise InvalidDirectoryError, not UnicodeDecodeError
- Truncated files raise TruncatedWadError
- Out-of-range lump offsets raise InvalidDirectoryError
- WadFile.find_lump and WadArchive.read agree on duplicate lump precedence
  (last entry wins, matching Doom's W_CheckNumForName semantics)
- UdmfLump truthiness and repr are safe (no AssertionError from missing _row_format)
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from wadlib.archive import WadArchive
from wadlib.exceptions import (
    BadHeaderWadException,
    InvalidDirectoryError,
    TruncatedWadError,
    WadFormatError,
)
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pack_directory_entry(offset: int, size: int, name: bytes) -> bytes:
    padded = name.ljust(8, b"\x00")[:8]
    return struct.pack("<II8s", offset, size, padded)


def _build_wad_bytes(
    magic: bytes,
    lumps: list[tuple[bytes, bytes]],
) -> bytes:
    """Build a raw WAD from (name, data) pairs, using the given magic bytes."""
    num_lumps = len(lumps)
    lump_data = b"".join(data for _, data in lumps)
    dir_offset = 12 + len(lump_data)
    header = struct.pack("<4sII", magic, num_lumps, dir_offset)

    directory = b""
    offset = 12
    for name, data in lumps:
        directory += _pack_directory_entry(offset, len(data), name)
        offset += len(data)

    return header + lump_data + directory


def _write_raw(tmp_path: Path, name: str, data: bytes) -> str:
    p = tmp_path / name
    p.write_bytes(data)
    return str(p)


# ---------------------------------------------------------------------------
# Non-ASCII magic bytes
# ---------------------------------------------------------------------------


class TestNonAsciiMagic:
    def test_non_ascii_magic_raises_wad_format_error(self, tmp_path: Path) -> None:
        """A magic field with high bytes must raise WadFormatError, not UnicodeDecodeError."""
        raw = _build_wad_bytes(b"\xff\xfeAD", [(b"E1M1", b"")])
        path = _write_raw(tmp_path, "bad_magic.wad", raw)
        with pytest.raises(WadFormatError):
            WadFile(path)

    def test_non_ascii_magic_is_not_unicode_error(self, tmp_path: Path) -> None:
        raw = _build_wad_bytes(b"\x80WAD", [(b"E1M1", b"")])
        path = _write_raw(tmp_path, "bad_magic2.wad", raw)
        with pytest.raises(WadFormatError):
            WadFile(path)

    def test_bad_ascii_magic_word_raises(self, tmp_path: Path) -> None:
        """A well-formed ASCII magic that is not IWAD/PWAD still raises BadHeaderWadException."""
        raw = _build_wad_bytes(b"XWAD", [(b"E1M1", b"")])
        path = _write_raw(tmp_path, "xwad.wad", raw)
        with pytest.raises(BadHeaderWadException):
            WadFile(path)


# ---------------------------------------------------------------------------
# Non-ASCII lump names
# ---------------------------------------------------------------------------


class TestNonAsciiLumpNames:
    def test_non_ascii_lump_name_raises_invalid_directory(self, tmp_path: Path) -> None:
        """A lump name with high bytes must raise InvalidDirectoryError."""
        # Build a valid WAD with one lump whose name has a non-ASCII byte.
        num_lumps = 1
        lump_data = b"\x00" * 4
        dir_offset = 12 + len(lump_data)
        header = struct.pack("<4sII", b"PWAD", num_lumps, dir_offset)
        # Name with a non-ASCII byte: b"\xff\x41\x41\x41\x00\x00\x00\x00"
        bad_name_entry = struct.pack("<II8s", 12, 4, b"\xff\x41\x41\x41\x00\x00\x00\x00")
        raw = header + lump_data + bad_name_entry
        path = _write_raw(tmp_path, "bad_name.wad", raw)
        with pytest.raises(InvalidDirectoryError):
            wad = WadFile(path)
            _ = wad.directory  # trigger lazy directory parse

    def test_non_ascii_lump_name_is_not_unicode_error(self, tmp_path: Path) -> None:
        """InvalidDirectoryError, not UnicodeDecodeError, must be raised."""
        num_lumps = 1
        lump_data = b"data"
        dir_offset = 12 + len(lump_data)
        header = struct.pack("<4sII", b"PWAD", num_lumps, dir_offset)
        bad_entry = struct.pack("<II8s", 12, 4, b"\x80ELLO\x00\x00\x00")
        raw = header + lump_data + bad_entry
        path = _write_raw(tmp_path, "bad_name2.wad", raw)
        with pytest.raises(WadFormatError):
            wad = WadFile(path)
            _ = wad.directory


# ---------------------------------------------------------------------------
# Truncated WADs
# ---------------------------------------------------------------------------


class TestTruncatedWad:
    def test_too_short_for_header(self, tmp_path: Path) -> None:
        """A file shorter than 12 bytes raises TruncatedWadError."""
        path = _write_raw(tmp_path, "short.wad", b"IWAD")
        with pytest.raises(TruncatedWadError):
            WadFile(path)

    def test_exactly_11_bytes_raises(self, tmp_path: Path) -> None:
        path = _write_raw(tmp_path, "eleven.wad", b"\x00" * 11)
        with pytest.raises(TruncatedWadError):
            WadFile(path)

    def test_directory_past_eof(self, tmp_path: Path) -> None:
        """A directory offset beyond the file size raises WadFormatError."""
        # Point directory at offset 9999 but file is only 12 bytes.
        raw = struct.pack("<4sII", b"IWAD", 1, 9999)
        path = _write_raw(tmp_path, "dir_past_eof.wad", raw)
        with pytest.raises(WadFormatError):
            WadFile(path)


# ---------------------------------------------------------------------------
# Out-of-range lump offsets
# ---------------------------------------------------------------------------


class TestOutOfRangeLumps:
    def test_lump_offset_past_eof(self, tmp_path: Path) -> None:
        """A lump whose offset+size extends past the file raises InvalidDirectoryError."""
        lump_data = b"\x00" * 4
        dir_offset = 12 + len(lump_data)
        header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
        # Report a size that would reach past the file.
        bad_entry = struct.pack("<II8s", 12, 9999, b"TOOBIG\x00\x00")
        raw = header + lump_data + bad_entry
        path = _write_raw(tmp_path, "bad_offset.wad", raw)
        with pytest.raises(InvalidDirectoryError):
            wad = WadFile(path)
            _ = wad.directory


# ---------------------------------------------------------------------------
# Duplicate lump precedence — WadFile and WadArchive must agree
# ---------------------------------------------------------------------------


class TestDuplicateLumpPrecedence:
    def _wad_with_duplicates(self, tmp_path: Path) -> str:
        """Build a PWAD with two lumps both named 'DUP', different data."""
        lumps = [(b"DUP\x00\x00\x00\x00\x00", b"first"), (b"DUP\x00\x00\x00\x00\x00", b"last")]
        raw = _build_wad_bytes(b"PWAD", lumps)
        return _write_raw(tmp_path, "dup.wad", raw)

    def test_wad_file_returns_last_duplicate(self, tmp_path: Path) -> None:
        """WadFile.find_lump must return the last matching lump."""
        path = self._wad_with_duplicates(tmp_path)
        with WadFile(path) as wad:
            entry = wad.find_lump("DUP")
            assert entry is not None
            wad.fd.seek(entry.offset)
            assert wad.fd.read(entry.size) == b"last"

    def test_wad_archive_returns_last_duplicate(self, tmp_path: Path) -> None:
        """WadArchive.read must return the last matching lump (consistent with WadFile)."""
        path = self._wad_with_duplicates(tmp_path)
        with WadArchive(path) as wad:
            assert wad.read("DUP") == b"last"

    def test_wad_file_and_archive_agree_on_duplicate(self, tmp_path: Path) -> None:
        """Both lookup APIs must resolve to the same data for duplicate names."""
        path = self._wad_with_duplicates(tmp_path)

        with WadFile(path) as wad_file:
            entry = wad_file.find_lump("DUP")
            assert entry is not None
            wad_file.fd.seek(entry.offset)
            wf_data = wad_file.fd.read(entry.size)

        with WadArchive(path) as archive:
            wa_data = archive.read("DUP")

        assert wf_data == wa_data, f"WadFile got {wf_data!r} but WadArchive got {wa_data!r}"


# ---------------------------------------------------------------------------
# UdmfLump — truthiness and repr must not crash
# ---------------------------------------------------------------------------


class TestUdmfLumpSafety:
    def _build_udmf_wad(self, tmp_path: Path) -> str:
        """Build a minimal PWAD with a UDMF MAP01."""
        textmap = b'namespace = "zdoom";\nvertex { x = 0.0; y = 0.0; }\n'
        lumps = [
            (b"MAP01\x00\x00\x00", b""),
            (b"TEXTMAP\x00", textmap),
            (b"ENDMAP\x00\x00", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        return _write_raw(tmp_path, "udmf.wad", raw)

    def test_udmf_lump_attached(self, tmp_path: Path) -> None:
        """WadFile.maps should expose a non-None udmf field for UDMF maps."""
        path = self._build_udmf_wad(tmp_path)
        with WadFile(path) as wad:
            assert len(wad.maps) > 0
            m = wad.maps[0]
            assert m.udmf is not None

    def test_udmf_lump_truthiness_does_not_crash(self, tmp_path: Path) -> None:
        """`if map.udmf:` must not raise AssertionError."""
        path = self._build_udmf_wad(tmp_path)
        with WadFile(path) as wad:
            m = wad.maps[0]
            # Must not raise — previously crashed via __len__ -> _row_size assertion.
            result = bool(m.udmf)
            assert result is True

    def test_udmf_lump_repr_does_not_crash(self, tmp_path: Path) -> None:
        """`repr(map.udmf)` must not raise AssertionError."""
        path = self._build_udmf_wad(tmp_path)
        with WadFile(path) as wad:
            m = wad.maps[0]
            r = repr(m.udmf)
            assert "UdmfLump" in r

    def test_empty_udmf_lump_is_falsy(self, tmp_path: Path) -> None:
        """A UdmfLump with empty TEXTMAP data should be falsy."""
        # Build a WAD with TEXTMAP but zero bytes.
        lumps = [
            (b"MAP01\x00\x00\x00", b""),
            (b"TEXTMAP\x00", b""),  # zero-size TEXTMAP
            (b"ENDMAP\x00\x00", b""),
        ]
        raw = _build_wad_bytes(b"PWAD", lumps)
        path = _write_raw(tmp_path, "empty_udmf.wad", raw)
        with WadFile(path) as wad:
            m = wad.maps[0]
            # A zero-size lump should be falsy.
            assert not m.udmf
