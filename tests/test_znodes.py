"""Tests for ZNODES lump (ZDoom extended BSP format)."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from wadlib.lumps.nodes import SSECTOR_FLAG
from wadlib.lumps.znodes import (
    ZNodesLump,
    ZNodList,
    _normalize_child,
)
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WADS_DIR = Path(__file__).parent.parent / "wads"


def _build_xnod_payload() -> bytes:
    """Construct a minimal XNOD payload (no magic prefix)."""
    # original_vertex_count=2, extra_vertex_count=1
    orig_extra = struct.pack("<II", 2, 1)
    # extra vertex: fixed-point 16.16 → x=65536 → 1, y=131072 → 2
    extra_vert = struct.pack("<ii", 65536, 131072)
    # 1 subsector with 2 segs
    ssectors = struct.pack("<II", 1, 2)  # count=1, then seg_count=2
    # 2 segs: one real (linedef 0), one mini-seg (linedef 0xFFFF)
    seg_count = struct.pack("<I", 2)
    seg0 = struct.pack("<IIHB", 0, 1, 0, 0)  # real seg
    seg1 = struct.pack("<IIHB", 1, 2, 0xFFFF, 0)  # mini-seg
    # 1 node; right_child = 0x80000000 (subsector 0), left_child = 0
    node_count = struct.pack("<I", 1)
    node0 = struct.pack("<hhhhhhhhhhhhII", 0, 0, 64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x80000000, 0)
    return orig_extra + extra_vert + ssectors + seg_count + seg0 + seg1 + node_count + node0


def _make_znodes_lump(compressed: bool, tmp_path: Path) -> ZNodesLump:
    """Write a minimal XNOD or ZNOD lump to a temp file and return a ZNodesLump."""
    payload = _build_xnod_payload()
    data = b"ZNOD" + zlib.compress(payload) if compressed else b"XNOD" + payload

    # Wrap in a minimal WAD so ZNodesLump (a BaseLump) can be constructed.
    from tests.conftest import _build_wad  # local helper

    wad_bytes = _build_wad("IWAD", [("ZNODES", data)])
    wad_path = tmp_path / "znodes_test.wad"
    wad_path.write_bytes(wad_bytes)

    wad = WadFile(str(wad_path))
    entry = wad.directory[0]  # the only lump
    lump = ZNodesLump(entry)
    return lump


# ---------------------------------------------------------------------------
# _normalize_child
# ---------------------------------------------------------------------------


def test_normalize_child_subsector_flag() -> None:
    raw = 0x80000005
    result = _normalize_child(raw)
    assert result & SSECTOR_FLAG
    assert (result & ~SSECTOR_FLAG) == 5


def test_normalize_child_node_index() -> None:
    assert _normalize_child(42) == 42


def test_normalize_child_zero_is_node() -> None:
    assert _normalize_child(0) == 0


# ---------------------------------------------------------------------------
# ZNodList
# ---------------------------------------------------------------------------


def test_znodlist_len_and_get() -> None:
    lst: ZNodList[int] = ZNodList([10, 20, 30])
    assert len(lst) == 3
    assert lst.get(0) == 10
    assert lst.get(2) == 30
    assert lst.get(3) is None


def test_znodlist_iter() -> None:
    lst: ZNodList[int] = ZNodList([1, 2, 3])
    assert list(lst) == [1, 2, 3]


def test_znodlist_bool() -> None:
    assert ZNodList([1])
    assert not ZNodList([])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ZNodesLump.parsed — XNOD (uncompressed)
# ---------------------------------------------------------------------------


def test_znodes_xnod_orig_vertex_count(tmp_path: Path) -> None:
    lump = _make_znodes_lump(compressed=False, tmp_path=tmp_path)
    assert lump.parsed.orig_vertex_count == 2


def test_znodes_xnod_extra_vertices(tmp_path: Path) -> None:
    p = _make_znodes_lump(compressed=False, tmp_path=tmp_path).parsed
    assert len(p.extra_vertices) == 1
    v = p.extra_vertices.get(0)
    assert v is not None
    assert v.x == 1
    assert v.y == 2


def test_znodes_xnod_subsectors(tmp_path: Path) -> None:
    p = _make_znodes_lump(compressed=False, tmp_path=tmp_path).parsed
    assert len(p.subsectors) == 1
    ss = p.subsectors.get(0)
    assert ss is not None
    assert ss.seg_count == 2
    assert ss.first_seg == 0


def test_znodes_xnod_segs(tmp_path: Path) -> None:
    p = _make_znodes_lump(compressed=False, tmp_path=tmp_path).parsed
    assert len(p.segs) == 2
    real = p.segs.get(0)
    assert real is not None
    assert real.linedef == 0
    mini = p.segs.get(1)
    assert mini is not None
    assert mini.linedef == 0xFFFF


def test_znodes_xnod_nodes(tmp_path: Path) -> None:
    p = _make_znodes_lump(compressed=False, tmp_path=tmp_path).parsed
    assert len(p.nodes) == 1
    n = p.nodes.get(0)
    assert n is not None
    assert n.dx == 64
    assert n.right_child & SSECTOR_FLAG
    assert (n.right_child & ~SSECTOR_FLAG) == 0  # subsector 0
    assert n.right_is_subsector
    assert not n.left_is_subsector


# ---------------------------------------------------------------------------
# ZNodesLump.parsed — ZNOD (zlib-compressed)
# ---------------------------------------------------------------------------


def test_znodes_znod_parses_same_as_xnod(tmp_path: Path) -> None:
    xnod = _make_znodes_lump(compressed=False, tmp_path=tmp_path).parsed
    znod_tmp = tmp_path / "znod"
    znod_tmp.mkdir()
    znod = _make_znodes_lump(compressed=True, tmp_path=znod_tmp).parsed

    assert xnod.orig_vertex_count == znod.orig_vertex_count
    assert len(xnod.extra_vertices) == len(znod.extra_vertices)
    assert len(xnod.segs) == len(znod.segs)
    assert len(xnod.nodes) == len(znod.nodes)


# ---------------------------------------------------------------------------
# Integration: ZNODES attaches correctly to a map entry
# ---------------------------------------------------------------------------


def test_attach_znodes_sets_bsp_lumps(tmp_path: Path) -> None:
    """A map with a ZNODES lump should have nodes, segs, and ssectors attached."""
    from tests.conftest import _build_wad

    payload = _build_xnod_payload()
    data = b"XNOD" + payload

    vertex_data = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)  # 2 original verts
    thing_data = struct.pack("<hhHHH", 0, 0, 0, 1, 7)

    lumps: list[tuple[str, bytes]] = [
        ("E1M1", b""),
        ("THINGS", thing_data),
        ("VERTEXES", vertex_data),
        ("LINEDEFS", b""),
        ("SIDEDEFS", b""),
        ("SECTORS", b""),
        ("ZNODES", data),
    ]
    wad_bytes = _build_wad("IWAD", lumps)
    wad_path = tmp_path / "map_with_znodes.wad"
    wad_path.write_bytes(wad_bytes)

    with WadFile(str(wad_path)) as wad:
        m = wad.maps[0]
        assert m.nodes is not None
        assert m.segs is not None
        assert m.ssectors is not None
        # Vertices should now include the original 2 plus 1 extra = 3 total
        assert m.vertices is not None
        assert len(m.vertices) == 3


# ---------------------------------------------------------------------------
# Format sanity
# ---------------------------------------------------------------------------


def test_seg_format_size() -> None:
    from struct import calcsize

    from wadlib.lumps.znodes import _NODE_FORMAT, _SEG_FORMAT

    assert calcsize(_SEG_FORMAT) == 11
    assert calcsize(_NODE_FORMAT) == 32
