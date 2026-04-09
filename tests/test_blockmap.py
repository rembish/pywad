"""Tests for REJECT and BLOCKMAP lumps."""

from pywad.lumps.blockmap import BlockMap, Reject
from pywad.wad import WadFile

# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------

def test_reject_attached(doom1_wad: WadFile) -> None:
    assert doom1_wad.maps[0].reject is not None


def test_reject_is_reject(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.maps[0].reject, Reject)


def test_reject_data_is_bytes(doom1_wad: WadFile) -> None:
    r = doom1_wad.maps[0].reject
    assert isinstance(r.data, bytes)
    assert len(r.data) > 0


def test_reject_size_matches_sectors(doom1_wad: WadFile) -> None:
    import math
    m = doom1_wad.maps[0]
    n = len(m.sectors)
    expected_bytes = math.ceil(n * n / 8)
    assert len(m.reject.data) == expected_bytes


def test_reject_can_see_returns_bool(doom1_wad: WadFile) -> None:
    m = doom1_wad.maps[0]
    n = len(m.sectors)
    result = m.reject.can_see(0, 0, n)
    assert isinstance(result, bool)


def test_reject_repr(doom1_wad: WadFile) -> None:
    assert "Reject" in repr(doom1_wad.maps[0].reject)


# ---------------------------------------------------------------------------
# BLOCKMAP
# ---------------------------------------------------------------------------

def test_blockmap_attached(doom1_wad: WadFile) -> None:
    assert doom1_wad.maps[0].blockmap is not None


def test_blockmap_is_blockmap(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.maps[0].blockmap, BlockMap)


def test_blockmap_positive_dimensions(doom1_wad: WadFile) -> None:
    bm = doom1_wad.maps[0].blockmap
    assert bm.columns > 0
    assert bm.rows > 0


def test_blockmap_block_count(doom1_wad: WadFile) -> None:
    bm = doom1_wad.maps[0].blockmap
    assert bm.block_count == bm.columns * bm.rows


def test_blockmap_offsets_count(doom1_wad: WadFile) -> None:
    bm = doom1_wad.maps[0].blockmap
    assert len(bm.offsets) == bm.block_count


def test_blockmap_repr(doom1_wad: WadFile) -> None:
    assert "BlockMap" in repr(doom1_wad.maps[0].blockmap)


def test_blockmap_doom2(doom2_wad: WadFile) -> None:
    bm = doom2_wad.maps[0].blockmap
    assert bm is not None
    assert bm.block_count > 0
