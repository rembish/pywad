"""Shared fixtures for pywad tests."""

from __future__ import annotations

import struct
from collections.abc import Generator
from pathlib import Path

import pytest

from pywad.wad import WadFile

WADS_DIR = Path(__file__).parent.parent / "wads"
DOOM1_WAD = WADS_DIR / "DOOM.WAD"
DOOM2_WAD = WADS_DIR / "DOOM2.WAD"


# ---------------------------------------------------------------------------
# Helpers for building minimal in-memory WADs
# ---------------------------------------------------------------------------

def _build_wad(wad_type: str, lumps: list[tuple[str, bytes]]) -> bytes:
    """Build a minimal IWAD/PWAD in memory from a list of (name, data) pairs."""
    num_lumps = len(lumps)
    # Header is 12 bytes; lump data follows immediately
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)

    header = struct.pack("<4sII", wad_type.encode(), num_lumps, dir_offset)

    # Build directory
    directory = b""
    offset = data_start
    for name, data in lumps:
        padded_name = name.encode().ljust(8, b"\x00")
        directory += struct.pack("<II8s", offset, len(data), padded_name)
        offset += len(data)

    return header + lump_data + directory


def _wad_from_bytes(data: bytes) -> WadFile:
    """Open a WadFile from raw bytes using a temp file-like object trick."""
    # WadFile requires a real fd, so write to a temp BytesIO wrapper via a
    # temporary file. Easier: just use a tmp_path fixture in the test, but
    # conftest helpers work by writing to /tmp.
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wad") as f:
        f.write(data)
        name = f.name
    return WadFile(name)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def doom1_wad() -> Generator[WadFile, None, None]:
    """Open DOOM.WAD for the entire test session."""
    pytest.importorskip("pywad")  # sanity
    if not DOOM1_WAD.exists():
        pytest.skip("DOOM.WAD not found in wads/")
    with WadFile(str(DOOM1_WAD)) as w:
        yield w


@pytest.fixture(scope="session")
def doom2_wad() -> Generator[WadFile, None, None]:
    """Open DOOM2.WAD for the entire test session."""
    if not DOOM2_WAD.exists():
        pytest.skip("DOOM2.WAD not found in wads/")
    with WadFile(str(DOOM2_WAD)) as w:
        yield w


@pytest.fixture
def minimal_iwad(tmp_path: Path) -> WadFile:
    """A minimal IWAD with a single E1M1 map marker and THINGS/VERTEXES/LINEDEFS."""
    # One Thing: (x=0, y=0, angle=0, type=1, flags=7) — 10 bytes
    thing_data = struct.pack("<hhHHH", 0, 0, 0, 1, 7)
    # Two Vertices: (0,0) and (64,0)
    vertex_data = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)
    # One LineDef: start=0, end=1, flags=1, special=0, tag=0, right=0, left=-1
    linedef_data = struct.pack("<HHHHHhh", 0, 1, 1, 0, 0, 0, -1)

    lumps: list[tuple[str, bytes]] = [
        ("E1M1", b""),
        ("THINGS", thing_data),
        ("VERTEXES", vertex_data),
        ("LINEDEFS", linedef_data),
    ]
    data = _build_wad("IWAD", lumps)
    wad_path = tmp_path / "test.wad"
    wad_path.write_bytes(data)
    return WadFile(str(wad_path))


@pytest.fixture
def minimal_pwad(tmp_path: Path) -> WadFile:
    """A minimal PWAD with a MAP01 map marker."""
    thing_data = struct.pack("<hhHHH", 10, 20, 90, 3004, 7)
    lumps: list[tuple[str, bytes]] = [
        ("MAP01", b""),
        ("THINGS", thing_data),
        ("VERTEXES", b""),
        ("LINEDEFS", b""),
    ]
    data = _build_wad("PWAD", lumps)
    wad_path = tmp_path / "patch.wad"
    wad_path.write_bytes(data)
    return WadFile(str(wad_path))
