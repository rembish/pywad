"""Tests for WAD header parsing."""

import struct
from pathlib import Path

import pytest

from pywad.enums import WadType
from pywad.exceptions import BadHeaderWadException
from pywad.wad import WadFile


def test_doom1_wad_type(doom1_wad: WadFile) -> None:
    assert doom1_wad.wad_type == WadType.IWAD


def test_doom2_wad_type(doom2_wad: WadFile) -> None:
    assert doom2_wad.wad_type == WadType.IWAD


def test_doom1_directory_size(doom1_wad: WadFile) -> None:
    # DOOM.WAD has hundreds of lumps
    assert doom1_wad.directory_size > 0


def test_doom2_directory_size(doom2_wad: WadFile) -> None:
    assert doom2_wad.directory_size > 0


def test_minimal_iwad_type(minimal_iwad: WadFile) -> None:
    assert minimal_iwad.wad_type == WadType.IWAD


def test_minimal_pwad_type(minimal_pwad: WadFile) -> None:
    assert minimal_pwad.wad_type == WadType.PWAD


def test_bad_magic_raises(tmp_path: Path) -> None:
    bad = struct.pack("<4sII", b"BADD", 0, 12)
    (tmp_path / "bad.wad").write_bytes(bad)
    with pytest.raises(BadHeaderWadException):
        WadFile(str(tmp_path / "bad.wad"))


def test_context_manager_closes(tmp_path: Path) -> None:
    import struct as s
    # build the tiniest valid IWAD
    data = s.pack("<4sII", b"IWAD", 0, 12)
    p = tmp_path / "tiny.wad"
    p.write_bytes(data)
    with WadFile(str(p)) as w:
        assert not w.fd.closed
    assert w.fd.closed
