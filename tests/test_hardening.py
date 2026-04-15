"""Adversarial read-time tests for malformed WADs and hardened edge cases.

These tests verify that:
- Non-ASCII magic bytes raise WadFormatError, not UnicodeDecodeError
- Non-ASCII lump names raise InvalidDirectoryError, not UnicodeDecodeError
- Corrupt picture/flat/playpal lumps raise CorruptLumpError, not AssertionError/EOFError
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
    CorruptLumpError,
    InvalidDirectoryError,
    TruncatedWadError,
    WadFormatError,
)
from wadlib.lumps.behavior import parse_behavior
from wadlib.lumps.flat import Flat
from wadlib.lumps.mus import Mus
from wadlib.lumps.picture import Picture
from wadlib.lumps.playpal import PlayPal
from wadlib.lumps.sound import DmxSound
from wadlib.lumps.textures import PNames, TextureList
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


# ---------------------------------------------------------------------------
# CorruptLumpError — picture, flat, and playpal parsers
# ---------------------------------------------------------------------------

_FAKE_PALETTE = [(0, 0, 0)] * 256  # black palette for decode calls


class TestCorruptLump:
    """Verify that malformed lump payloads raise CorruptLumpError."""

    # -- helpers --

    def _wad_with_lump(self, tmp_path: Path, name: str, data: bytes) -> str:
        """Build a single-lump PWAD and return its path."""
        raw = _build_wad_bytes(b"PWAD", [(name.encode().ljust(8, b"\x00")[:8], data)])
        return _write_raw(tmp_path, "corrupt.wad", raw)

    def _get_lump(self, path: str, cls: type, lump_name: str):  # type: ignore[no-untyped-def]
        """Open a WAD and return the named lump cast to *cls*."""
        with WadFile(path) as wad:
            entry = wad.find_lump(lump_name)
            assert entry is not None
            return cls(entry)

    # -- Picture --

    def test_picture_empty_lump_raises(self, tmp_path: Path) -> None:
        """An empty picture lump must raise CorruptLumpError, not AssertionError."""
        # Zero-size lumps have no DirectoryEntry data — use 1-byte stub instead
        path = self._wad_with_lump(tmp_path, "PATCH1", b"\x01")
        lump = self._get_lump(path, Picture, "PATCH1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    def test_picture_header_too_short_raises(self, tmp_path: Path) -> None:
        """A lump shorter than the 8-byte picture header raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "PATCH1", b"\x01\x00\x01")  # 3 bytes only
        lump = self._get_lump(path, Picture, "PATCH1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    def test_picture_column_offset_past_lump_raises(self, tmp_path: Path) -> None:
        """A column offset that points beyond the lump raises CorruptLumpError."""
        # Valid header: 1x1 picture, column offset 9999 (past end of this tiny lump)
        header = struct.pack("<HHhh", 1, 1, 0, 0)
        col_offset = struct.pack("<I", 9999)  # way past end
        data = header + col_offset + b"\xff"  # EOF marker byte (won't be reached)
        path = self._wad_with_lump(tmp_path, "PATCH1", data)
        lump = self._get_lump(path, Picture, "PATCH1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    def test_picture_truncated_column_data_raises(self, tmp_path: Path) -> None:
        """Post data that extends past the lump raises CorruptLumpError."""
        header = struct.pack("<HHhh", 1, 1, 0, 0)
        # Column offset points right after the offset table
        col_off = len(header) + 4
        col_offset = struct.pack("<I", col_off)
        # Topdelta=0, post_len=10 but no pixel data follows
        post = b"\x00\x0a\x00"  # topdelta=0, length=10, pre-pad — then nothing
        data = header + col_offset + post
        path = self._wad_with_lump(tmp_path, "PATCH1", data)
        lump = self._get_lump(path, Picture, "PATCH1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    def test_picture_post_past_image_height_raises(self, tmp_path: Path) -> None:
        """A post whose topdelta+row >= height must raise CorruptLumpError, not IndexError."""
        # 1x1 picture, but the single post starts at row 1 (past image height=1).
        header = struct.pack("<HHhh", 1, 1, 0, 0)  # width=1, height=1
        col_off = len(header) + 4  # column data starts right after offset table
        col_offset = struct.pack("<I", col_off)
        # topdelta=1, post_len=1, pre-pad, pixel=0, post-pad, terminator
        post = b"\x01\x01\x00\x00\x00\xff"
        data = header + col_offset + post
        path = self._wad_with_lump(tmp_path, "PATCH1", data)
        lump = self._get_lump(path, Picture, "PATCH1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    # -- Flat --

    def test_flat_too_short_raises(self, tmp_path: Path) -> None:
        """A flat shorter than 4096 bytes raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "FLAT1", b"\x00" * 100)
        lump = self._get_lump(path, Flat, "FLAT1")
        with pytest.raises(CorruptLumpError):
            lump.decode(_FAKE_PALETTE)

    # -- PlayPal --

    def test_playpal_too_short_raises(self, tmp_path: Path) -> None:
        """A PLAYPAL shorter than one full palette (768 bytes) raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "PLAYPAL", b"\x00" * 100)
        lump = self._get_lump(path, PlayPal, "PLAYPAL")
        with pytest.raises(CorruptLumpError):
            lump.get_palette(0)

    # -- PNames --

    def test_pnames_truncated_raises(self, tmp_path: Path) -> None:
        """A PNAMES with count=3 but only 2 entries raises CorruptLumpError."""
        data = struct.pack("<I", 3) + b"PATCH1\x00\x00" + b"PATCH2\x00\x00"
        path = self._wad_with_lump(tmp_path, "PNAMES", data)
        lump = self._get_lump(path, PNames, "PNAMES")
        with pytest.raises(CorruptLumpError):
            _ = lump.names

    def test_pnames_too_short_for_count_raises(self, tmp_path: Path) -> None:
        """A PNAMES shorter than 4 bytes (no room for count) raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "PNAMES", b"\x02\x00")
        lump = self._get_lump(path, PNames, "PNAMES")
        with pytest.raises(CorruptLumpError):
            _ = lump.names

    # -- TextureList --

    def test_texturelist_truncated_offsets_raises(self, tmp_path: Path) -> None:
        """A TEXTURE lump with count=2 but only one offset entry raises CorruptLumpError."""
        data = struct.pack("<I", 2) + struct.pack("<I", 12)  # claims 2 textures, provides 1 offset
        path = self._wad_with_lump(tmp_path, "TEXTURE1", data)
        lump = self._get_lump(path, TextureList, "TEXTURE1")
        with pytest.raises(CorruptLumpError):
            _ = lump.textures

    def test_texturelist_corrupt_texture_body_raises(self, tmp_path: Path) -> None:
        """A TEXTURE lump whose offset points to truncated header data raises CorruptLumpError."""
        # count=1, offset points at byte 8 (right after count+offset_table), but no body there
        data = struct.pack("<I", 1) + struct.pack("<I", 8)  # offset 8 → past end of 8-byte lump
        path = self._wad_with_lump(tmp_path, "TEXTURE1", data)
        lump = self._get_lump(path, TextureList, "TEXTURE1")
        with pytest.raises(CorruptLumpError):
            _ = lump.textures

    # -- Mus --

    def test_mus_too_short_raises(self, tmp_path: Path) -> None:
        """A MUS lump shorter than the 16-byte header raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "D_E1M1", b"MUS\x1a\x00\x00")
        lump = self._get_lump(path, Mus, "D_E1M1")
        with pytest.raises(CorruptLumpError):
            lump.to_midi()

    def test_mus_truncated_event_stream_raises(self, tmp_path: Path) -> None:
        """A MUS lump with valid header but truncated event stream raises CorruptLumpError."""
        score_start = struct.calcsize("<4sHHHHHH")  # 16 bytes
        score_len = 50  # claims 50 bytes of events
        header = struct.pack("<4sHHHHHH", b"MUS\x1a", score_len, score_start, 0, 0, 0, 0)
        # Only 1 byte of event data — claim a note-on (etype=1) with no note byte following
        data = header + b"\x10"  # 0x10 = last=0, etype=1, channel=0; note byte missing
        path = self._wad_with_lump(tmp_path, "D_E1M1", data)
        lump = self._get_lump(path, Mus, "D_E1M1")
        with pytest.raises(CorruptLumpError):
            lump.to_midi()

    def test_mus_bad_magic_raises(self, tmp_path: Path) -> None:
        """A MUS lump with wrong magic raises CorruptLumpError."""
        bad_header = struct.pack("<4sHHHHHH", b"MIDI", 0, 16, 0, 0, 0, 0)
        path = self._wad_with_lump(tmp_path, "D_E1M1", bad_header)
        lump = self._get_lump(path, Mus, "D_E1M1")
        with pytest.raises(CorruptLumpError):
            lump.to_midi()

    # -- DmxSound --

    def test_dmxsound_too_short_raises(self, tmp_path: Path) -> None:
        """A DMX sound lump shorter than 8 bytes raises CorruptLumpError."""
        path = self._wad_with_lump(tmp_path, "DSPISTOL", b"\x03\x00\x11\x2b")  # only 4 bytes
        lump = self._get_lump(path, DmxSound, "DSPISTOL")
        with pytest.raises(CorruptLumpError):
            lump.to_wav()

    # -- parse_behavior --

    def test_parse_behavior_too_short_raises(self, tmp_path: Path) -> None:
        """parse_behavior on data shorter than 8 bytes raises CorruptLumpError."""
        with pytest.raises(CorruptLumpError):
            parse_behavior(b"\x00\x00\x00")

    def test_parse_behavior_bad_magic_raises(self, tmp_path: Path) -> None:
        """parse_behavior on data with unknown magic raises CorruptLumpError."""
        with pytest.raises(CorruptLumpError):
            parse_behavior(b"XXXX\x00\x00\x00\x00")
