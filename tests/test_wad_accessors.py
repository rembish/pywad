"""Tests for WadFile.get_lump(), get_lumps(), and find_lumps()."""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path

from wadlib.directory import DirectoryEntry
from wadlib.lumps.base import BaseLump
from wadlib.lumps.colormap import ColormapLump
from wadlib.lumps.playpal import PlayPal
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers — build multi-lump WADs for find_lumps tests
# ---------------------------------------------------------------------------


def _build_wad_raw(lumps: list[tuple[str, bytes]]) -> bytes:
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)
    header = struct.pack("<4sII", b"PWAD", len(lumps), dir_offset)
    directory = b""
    offset = data_start
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.encode().ljust(8, b"\x00"))
        offset += len(data)
    return header + lump_data + directory


def _open_wad_bytes(raw: bytes) -> WadFile:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wad") as f:
        f.write(raw)
        return WadFile(f.name)


def test_get_lump_returns_baselump(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert isinstance(lump, BaseLump)


def test_get_lump_dispatches_known_type(freedoom1_wad: WadFile) -> None:
    assert isinstance(freedoom1_wad.get_lump("PLAYPAL"), PlayPal)
    assert isinstance(freedoom1_wad.get_lump("COLORMAP"), ColormapLump)


def test_get_lump_unknown_name_falls_back_to_baselump(tmp_path: Path) -> None:
    raw = _build_wad_raw([("MYDATA", b"\x01\x02\x03")])
    wad_path = tmp_path / "unknown.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        lump = wad.get_lump("MYDATA")
        assert lump is not None
        assert type(lump) is BaseLump


def test_get_lumps_dispatches_known_type(freedoom1_wad: WadFile) -> None:
    lumps = freedoom1_wad.get_lumps("PLAYPAL")
    assert len(lumps) >= 1
    assert all(isinstance(lump, PlayPal) for lump in lumps)


def test_get_lump_returns_none_for_missing(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_lump("DOESNOTEXIST") is None


def test_get_lump_name(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert lump.name == "PLAYPAL"


def test_get_lump_has_data(freedoom1_wad: WadFile) -> None:
    lump = freedoom1_wad.get_lump("PLAYPAL")
    assert lump is not None
    assert len(lump.raw()) > 0


def test_get_lumps_returns_list(freedoom1_wad: WadFile) -> None:
    lumps = freedoom1_wad.get_lumps("PLAYPAL")
    assert isinstance(lumps, list)
    assert len(lumps) >= 1


def test_get_lumps_missing_returns_empty(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.get_lumps("DOESNOTEXIST") == []


def test_get_lumps_all_are_baselump(freedoom1_wad: WadFile) -> None:
    for lump in freedoom1_wad.get_lumps("PLAYPAL"):
        assert isinstance(lump, BaseLump)


# ---------------------------------------------------------------------------
# find_lumps — returns DirectoryEntry objects in priority order
# ---------------------------------------------------------------------------


def test_find_lumps_single_entry_returns_one_item(tmp_path: Path) -> None:
    raw = _build_wad_raw([("MYDATA", b"\x01\x02\x03")])
    wad_path = tmp_path / "test.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        result = wad.find_lumps("MYDATA")
    assert len(result) == 1
    assert isinstance(result[0], DirectoryEntry)


def test_find_lumps_missing_returns_empty(tmp_path: Path) -> None:
    raw = _build_wad_raw([("MYDATA", b"\x00")])
    wad_path = tmp_path / "test.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        assert wad.find_lumps("ABSENT") == []


def test_find_lumps_duplicate_returns_both_entries(tmp_path: Path) -> None:
    """A WAD with two lumps of the same name returns both, last-entry first."""
    raw = _build_wad_raw([("MYDATA", b"first"), ("MYDATA", b"second")])
    wad_path = tmp_path / "dup.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        result = wad.find_lumps("MYDATA")
        assert len(result) == 2
        # Last entry wins (highest priority first), so second bytes come first
        assert result[0].read_bytes() == b"second"
        assert result[1].read_bytes() == b"first"


def test_find_lumps_first_matches_find_lump(tmp_path: Path) -> None:
    """find_lumps(name)[0] must equal find_lump(name) when at least one entry exists."""
    raw = _build_wad_raw([("MYDATA", b"first"), ("MYDATA", b"second")])
    wad_path = tmp_path / "dup2.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        winner = wad.find_lump("MYDATA")
        all_entries = wad.find_lumps("MYDATA")
        assert winner is not None
        assert all_entries[0] is winner


def test_find_lumps_case_insensitive(tmp_path: Path) -> None:
    raw = _build_wad_raw([("MYDATA", b"\xff")])
    wad_path = tmp_path / "case.wad"
    wad_path.write_bytes(raw)
    with WadFile(str(wad_path)) as wad:
        assert len(wad.find_lumps("mydata")) == 1
        assert len(wad.find_lumps("MyData")) == 1
