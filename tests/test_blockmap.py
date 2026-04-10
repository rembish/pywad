"""Tests for REJECT and BLOCKMAP lumps."""

from wadlib.lumps.blockmap import BlockMap, Reject
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
