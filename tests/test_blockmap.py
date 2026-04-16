"""Tests for REJECT and BLOCKMAP lumps."""

import struct

import pytest

from wadlib.exceptions import CorruptLumpError
from wadlib.lumps.blockmap import BlockMap, Reject, build_blockmap
from wadlib.source import MemoryLumpSource
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------


def test_reject_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].reject is not None


def test_reject_is_reject(freedoom1_wad: WadFile) -> None:
    assert isinstance(freedoom1_wad.maps[0].reject, Reject)


def test_reject_data_is_bytes(freedoom1_wad: WadFile) -> None:
    r = freedoom1_wad.maps[0].reject
    assert isinstance(r.data, bytes)
    assert len(r.data) > 0


def test_reject_size_matches_sectors(freedoom1_wad: WadFile) -> None:
    import math

    m = freedoom1_wad.maps[0]
    n = len(m.sectors)
    expected_bytes = math.ceil(n * n / 8)
    assert len(m.reject.data) == expected_bytes


def test_reject_can_see_returns_bool(freedoom1_wad: WadFile) -> None:
    m = freedoom1_wad.maps[0]
    n = len(m.sectors)
    result = m.reject.can_see(0, 0, n)
    assert isinstance(result, bool)


def test_reject_repr(freedoom1_wad: WadFile) -> None:
    assert "Reject" in repr(freedoom1_wad.maps[0].reject)


# ---------------------------------------------------------------------------
# BLOCKMAP
# ---------------------------------------------------------------------------


def test_blockmap_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].blockmap is not None


def test_blockmap_is_blockmap(freedoom1_wad: WadFile) -> None:
    assert isinstance(freedoom1_wad.maps[0].blockmap, BlockMap)


def test_blockmap_positive_dimensions(freedoom1_wad: WadFile) -> None:
    bm = freedoom1_wad.maps[0].blockmap
    assert bm.columns > 0
    assert bm.rows > 0


def test_blockmap_block_count(freedoom1_wad: WadFile) -> None:
    bm = freedoom1_wad.maps[0].blockmap
    assert bm.block_count == bm.columns * bm.rows


def test_blockmap_offsets_count(freedoom1_wad: WadFile) -> None:
    bm = freedoom1_wad.maps[0].blockmap
    assert len(bm.offsets) == bm.block_count


def test_blockmap_repr(freedoom1_wad: WadFile) -> None:
    assert "BlockMap" in repr(freedoom1_wad.maps[0].blockmap)


def test_blockmap_doom2(freedoom2_wad: WadFile) -> None:
    bm = freedoom2_wad.maps[0].blockmap
    assert bm is not None
    assert bm.block_count > 0


# ---------------------------------------------------------------------------
# BLOCKMAP builder
# ---------------------------------------------------------------------------


def test_build_blockmap_empty() -> None:
    data = build_blockmap([], [])
    assert len(data) == 8  # just the header


def test_build_blockmap_simple_square() -> None:
    verts = [(0, 0), (256, 0), (256, 256), (0, 256)]
    lines = [(0, 1), (1, 2), (2, 3), (3, 0)]
    data = build_blockmap(verts, lines)
    # Should parse back as a valid blockmap
    import struct

    _ox, _oy, cols, rows = struct.unpack("<hhHH", data[:8])
    assert cols > 0
    assert rows > 0
    assert cols * rows > 0


def test_build_blockmap_parseable() -> None:
    """Built blockmap should be parseable by the BlockMap class."""
    from io import BytesIO

    verts = [(0, 0), (512, 0), (512, 512), (0, 512)]
    lines = [(0, 1), (1, 2), (2, 3), (3, 0)]
    raw = build_blockmap(verts, lines)

    class _FW:
        def __init__(self, d: bytes) -> None:
            self.fd = BytesIO(d)

    from wadlib.directory import DirectoryEntry

    entry = DirectoryEntry(_FW(raw), 0, len(raw), "BLOCKMAP")  # type: ignore[arg-type]
    bm = BlockMap(entry)
    assert bm.columns > 0
    assert bm.rows > 0
    assert bm.block_count == bm.columns * bm.rows
    assert len(bm.offsets) == bm.block_count


def test_build_blockmap_covers_lines() -> None:
    """Every linedef should appear in at least one block."""
    verts = [(0, 0), (1000, 0), (1000, 1000)]
    lines = [(0, 1), (1, 2), (2, 0)]
    raw = build_blockmap(verts, lines)
    # The raw data should reference linedef indices 0, 1, 2
    # somewhere in the blocklists (after the offset table)
    import struct

    _, _, cols, rows = struct.unpack("<hhHH", raw[:8])
    # Skip header + offsets to get blocklists
    blocklist_start = 8 + cols * rows * 2
    blocklist_data = raw[blocklist_start:]
    # Should contain at least indices 0, 1, 2 as 16-bit values
    found: set[int] = set()
    for i in range(0, len(blocklist_data) - 1, 2):
        val = struct.unpack("<H", blocklist_data[i : i + 2])[0]
        if val < 3:  # linedef index
            found.add(val)
    assert found == {0, 1, 2}


# ---------------------------------------------------------------------------
# BLOCKMAP truncation hardening
# ---------------------------------------------------------------------------


def test_blockmap_truncated_offset_table_raises_corrupt() -> None:
    """A valid 8-byte header followed by a truncated offset table must raise
    CorruptLumpError rather than leaking struct.error."""
    # Header: origin=(0,0), cols=4, rows=4 → 16 blocks → needs 32 bytes of offsets.
    # Provide only 4 bytes of offsets — deliberately truncated.
    header = struct.pack("<hhHH", 0, 0, 4, 4)
    truncated_data = header + b"\x00" * 4  # only 4 bytes of a 32-byte table

    src = MemoryLumpSource("BLOCKMAP", truncated_data)
    with pytest.raises(CorruptLumpError, match="truncated"):
        BlockMap(src)


def test_blockmap_exact_offset_table_ok() -> None:
    """A header whose offset table is exactly the right size must parse cleanly."""
    # 2 blocks → 2 x 2 = 4 bytes of offsets.
    header = struct.pack("<hhHH", 0, 0, 1, 2)
    offsets = struct.pack("<HH", 10, 11)  # dummy offsets
    raw = header + offsets

    src = MemoryLumpSource("BLOCKMAP", raw)
    bm = BlockMap(src)
    assert bm.columns == 1
    assert bm.rows == 2
    assert len(bm.offsets) == 2
