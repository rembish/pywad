"""ZNODES lump — ZDoom/GZDoom extended BSP format (XNOD/ZNOD).

The ZNODES lump replaces NODES/SEGS/SSECTORS for maps compiled by ZDoom's
node builder.  Supports both uncompressed (magic ``XNOD``) and
zlib-compressed (magic ``ZNOD``) variants.

Layout (after magic and optional zlib decompression):
    uint32  original_vertex_count   -- vertices already in the VERTEXES lump
    uint32  extra_vertex_count
    (extra_vertex_count x 8 bytes)  -- int32 fixed-point 16.16 pairs (x, y)
    uint32  subsector_count
    (subsector_count x 4 bytes)     -- uint32 seg count per subsector (first_seg
                                       is derived as a running cumulative sum)
    uint32  seg_count
    (seg_count x 11 bytes)          -- <IIHB>: v1, v2, linedef, side
    uint32  node_count
    (node_count x 32 bytes)         -- <hhhhhhhhhhhhII>: partition + bboxes + children

Child index convention:
    ZNOD uses bit 31 (0x80000000) as the subsector flag; vanilla Doom uses
    bit 15 (0x8000).  :func:`_normalize_child` maps to the 0x8000 convention
    so the renderer's BSP walk requires no changes.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from struct import calcsize, unpack_from

from .base import BaseLump
from .nodes import SSECTOR_FLAG

_XNOD_MAGIC = b"XNOD"
_ZNOD_MAGIC = b"ZNOD"

_SEG_FORMAT = "<IIHB"  # v1 (uint32), v2 (uint32), linedef (uint16), side (uint8)
_SEG_SIZE = calcsize(_SEG_FORMAT)  # 11 bytes

_NODE_FORMAT = "<hhhhhhhhhhhhII"  # 12x int16 + 2x uint32
_NODE_SIZE = calcsize(_NODE_FORMAT)  # 32 bytes

_VERTEX_SIZE = 8  # two int32 fixed-point 16.16 values


class ZNodList[T]:
    """Lightweight list wrapper exposing the same ``.get()`` / iteration
    interface as :class:`~wadlib.lumps.base.BaseLump`-based lumps, without
    requiring a :class:`~wadlib.directory.DirectoryEntry`."""

    def __init__(self, items: list[T]) -> None:
        self._items = items

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> T:
        return self._items[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def get(self, index: int) -> T | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None


@dataclass
class ZNodVertex:
    x: int
    y: int


@dataclass
class ZNodSeg:
    start_vertex: int
    end_vertex: int
    linedef: int  # 0xFFFF = mini-seg (no real wall; used only as BSP divider)
    direction: int  # side: 0 = front, 1 = back


@dataclass
class ZNodSubSector:
    seg_count: int
    first_seg: int  # index into the ZNOD seg array


@dataclass
class ZNodNode:
    # Partition line
    x: int
    y: int
    dx: int
    dy: int
    # Right child bounding box
    right_top: int
    right_bottom: int
    right_left: int
    right_right: int
    # Left child bounding box
    left_top: int
    left_bottom: int
    left_left: int
    left_right: int
    # Child indices -- normalized to vanilla 0x8000 subsector-flag convention
    right_child: int
    left_child: int

    @property
    def right_is_subsector(self) -> bool:
        return bool(self.right_child & SSECTOR_FLAG)

    @property
    def left_is_subsector(self) -> bool:
        return bool(self.left_child & SSECTOR_FLAG)


@dataclass
class ZNodesParsed:
    """Structured result from :attr:`ZNodesLump.parsed`."""

    orig_vertex_count: int
    """Number of vertices already present in the map's VERTEXES lump."""

    extra_vertices: ZNodList[ZNodVertex]
    """Additional vertices appended by the ZDoom node builder (indices
    start at *orig_vertex_count* when combined with the original list)."""

    subsectors: ZNodList[ZNodSubSector]
    segs: ZNodList[ZNodSeg]
    nodes: ZNodList[ZNodNode]


def _normalize_child(raw: int) -> int:
    """Normalize a ZNOD 32-bit child index to the vanilla 16-bit convention.

    ZNOD uses bit 31 (``0x80000000``) as the subsector flag; vanilla Doom
    uses bit 15 (``0x8000``).  We map to the 0x8000 convention so the
    existing renderer BSP walk is reused unchanged.  Subsector indices are
    truncated to 15 bits -- valid for all practical maps (< 32 768 subsectors).
    """
    if raw & 0x80000000:
        return SSECTOR_FLAG | (raw & 0x7FFF)
    return raw & 0xFFFF


class ZNodesLump(BaseLump):
    """Parser for the ZNODES lump (XNOD/ZNOD extended BSP format)."""

    @cached_property
    def parsed(self) -> ZNodesParsed:  # pylint: disable=too-many-locals
        data = self.raw()
        if len(data) < 4:
            raise ValueError("ZNODES lump too short")
        magic = data[:4]
        if magic == _ZNOD_MAGIC:
            data = zlib.decompress(data[4:])
        elif magic == _XNOD_MAGIC:
            data = data[4:]
        else:
            raise ValueError(f"Unknown ZNODES magic: {magic!r}")

        offset = 0

        # ---- original + extra vertices ----------------------------------
        orig_count, extra_count = unpack_from("<II", data, offset)
        offset += 8
        extra_verts: list[ZNodVertex] = []
        for _ in range(extra_count):
            xfp, yfp = unpack_from("<ii", data, offset)
            extra_verts.append(ZNodVertex(round(xfp / 65536), round(yfp / 65536)))
            offset += _VERTEX_SIZE

        # ---- subsectors -------------------------------------------------
        (ssector_count,) = unpack_from("<I", data, offset)
        offset += 4
        subsectors: list[ZNodSubSector] = []
        first_seg = 0
        for _ in range(ssector_count):
            (seg_count,) = unpack_from("<I", data, offset)
            offset += 4
            subsectors.append(ZNodSubSector(seg_count, first_seg))
            first_seg += seg_count

        # ---- segs -------------------------------------------------------
        (seg_count,) = unpack_from("<I", data, offset)
        offset += 4
        segs: list[ZNodSeg] = []
        for _ in range(seg_count):
            v1, v2, linedef, side = unpack_from(_SEG_FORMAT, data, offset)
            offset += _SEG_SIZE
            segs.append(ZNodSeg(v1, v2, linedef, side))

        # ---- nodes ------------------------------------------------------
        (node_count,) = unpack_from("<I", data, offset)
        offset += 4
        nodes: list[ZNodNode] = []
        for _ in range(node_count):
            x, y, dx, dy, rt, rb, rl, rr, lt, lb, ll, lr, rc, lc = unpack_from(
                _NODE_FORMAT, data, offset
            )
            offset += _NODE_SIZE
            nodes.append(
                ZNodNode(
                    x,
                    y,
                    dx,
                    dy,
                    rt,
                    rb,
                    rl,
                    rr,
                    lt,
                    lb,
                    ll,
                    lr,
                    _normalize_child(rc),
                    _normalize_child(lc),
                )
            )

        return ZNodesParsed(
            orig_count,
            ZNodList(extra_verts),
            ZNodList(subsectors),
            ZNodList(segs),
            ZNodList(nodes),
        )
