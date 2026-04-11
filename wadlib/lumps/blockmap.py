"""REJECT and BLOCKMAP lump readers.

REJECT is a sector-visibility bitfield: bit [i*n+j] is set when monsters
in sector i cannot see sector j.

BLOCKMAP is a spatial index used by the engine for collision detection.
Its header contains the origin, column/row counts, and a flat array of
offsets into a variable-length list of linedefs per block.
"""

from __future__ import annotations

from struct import calcsize, pack, unpack
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..directory import DirectoryEntry

BLOCKMAP_HEADER_FORMAT = "<hhHH"


class Reject:
    """Raw bitfield mapping sector-to-sector visibility."""

    def __init__(self, entry: DirectoryEntry) -> None:
        entry.owner.fd.seek(entry.offset)
        self._data: bytes = entry.owner.fd.read(entry.size)

    @classmethod
    def from_bytes(cls, data: bytes) -> Reject:
        """Create a Reject table from raw bytes (no WAD entry required)."""
        obj = object.__new__(cls)
        obj._data = data
        return obj

    @classmethod
    def build(cls, num_sectors: int, rejected: set[tuple[int, int]] | None = None) -> Reject:
        """Build a REJECT table for *num_sectors*.

        *rejected* is a set of ``(from_sector, to_sector)`` pairs that should
        be marked as rejected (cannot see each other).  If ``None``, all pairs
        are visible (empty reject table).
        """
        total_bits = num_sectors * num_sectors
        total_bytes = (total_bits + 7) // 8
        data = bytearray(total_bytes)
        if rejected:
            for from_s, to_s in rejected:
                bit_index = from_s * num_sectors + to_s
                byte_index, bit_offset = divmod(bit_index, 8)
                if byte_index < total_bytes:
                    data[byte_index] |= 1 << bit_offset
        obj = object.__new__(cls)
        obj._data = bytes(data)
        return obj

    @property
    def data(self) -> bytes:
        return self._data

    def to_bytes(self) -> bytes:
        return self._data

    def can_see(self, from_sector: int, to_sector: int, num_sectors: int) -> bool:
        """Return True if *from_sector* CAN potentially see *to_sector*.

        A set bit means the engine skips the sight check (rejected).
        An unset bit means sight is possible.
        """
        bit_index = from_sector * num_sectors + to_sector
        byte_index, bit_offset = divmod(bit_index, 8)
        if byte_index >= len(self._data):
            return True
        return not bool(self._data[byte_index] & (1 << bit_offset))

    def __repr__(self) -> str:
        return f"<Reject {len(self._data)} bytes>"


class BlockMap:
    """Spatial acceleration structure for linedef collision queries."""

    def __init__(self, entry: DirectoryEntry) -> None:
        fd = entry.owner.fd
        hdr_size = calcsize(BLOCKMAP_HEADER_FORMAT)
        fd.seek(entry.offset)
        raw_all = fd.read(entry.size)
        ox, oy, cols, rows = unpack(BLOCKMAP_HEADER_FORMAT, raw_all[:hdr_size])
        self._origin_x: int = int(ox)
        self._origin_y: int = int(oy)
        self._columns: int = int(cols)
        self._rows: int = int(rows)
        num_blocks = self._columns * self._rows
        self._offsets: list[int] = [
            int(v) for v in unpack(f"<{num_blocks}H", raw_all[hdr_size : hdr_size + num_blocks * 2])
        ]
        # Keep the raw tail (blocklists) for round-trip fidelity
        self._raw: bytes = raw_all

    @classmethod
    def from_raw(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        origin_x: int,
        origin_y: int,
        columns: int,
        rows: int,
        offsets: list[int],
        raw: bytes,
    ) -> BlockMap:
        """Create a BlockMap from pre-computed components."""
        obj = object.__new__(cls)
        obj._origin_x = origin_x
        obj._origin_y = origin_y
        obj._columns = columns
        obj._rows = rows
        obj._offsets = offsets
        obj._raw = raw
        return obj

    @property
    def origin_x(self) -> int:
        return self._origin_x

    @property
    def origin_y(self) -> int:
        return self._origin_y

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def offsets(self) -> list[int]:
        return self._offsets

    @property
    def block_count(self) -> int:
        return self._columns * self._rows

    def to_bytes(self) -> bytes:
        """Serialize the blockmap back to raw bytes."""
        return self._raw

    def __repr__(self) -> str:
        return f"<BlockMap {self._columns}x{self._rows} origin=({self._origin_x},{self._origin_y})>"


# ---------------------------------------------------------------------------
# BLOCKMAP builder
# ---------------------------------------------------------------------------

_BLOCK_SIZE = 128  # each block covers a 128x128 map unit square


def build_blockmap(
    vertices: list[tuple[int, int]],
    linedefs: list[tuple[int, int]],
) -> bytes:
    """Generate a BLOCKMAP lump from map geometry.

    Parameters:
        vertices:  List of ``(x, y)`` vertex coordinates.
        linedefs:  List of ``(start_vertex, end_vertex)`` index pairs.

    Returns:
        Raw bytes for the BLOCKMAP lump.

    The blockmap is a spatial index: the map is divided into a grid of
    128x128-unit blocks, and each block lists which linedefs intersect it.
    The Doom engine uses this for fast collision detection.

    Example::

        from wadlib.lumps.blockmap import build_blockmap

        verts = [(0, 0), (256, 0), (256, 256), (0, 256)]
        lines = [(0, 1), (1, 2), (2, 3), (3, 0)]
        blockmap_bytes = build_blockmap(verts, lines)
    """
    if not vertices:
        # Empty map — minimal blockmap
        return pack(BLOCKMAP_HEADER_FORMAT, 0, 0, 0, 0)

    # Compute bounds
    min_x = min(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_x = max(v[0] for v in vertices)
    max_y = max(v[1] for v in vertices)

    # Origin is rounded down to block boundary
    origin_x = (min_x // _BLOCK_SIZE) * _BLOCK_SIZE - _BLOCK_SIZE
    origin_y = (min_y // _BLOCK_SIZE) * _BLOCK_SIZE - _BLOCK_SIZE

    columns = (max_x - origin_x) // _BLOCK_SIZE + 2
    rows = (max_y - origin_y) // _BLOCK_SIZE + 2

    # Build per-block linedef lists using Bresenham-style line rasterisation
    num_blocks = columns * rows
    blocks: list[list[int]] = [[] for _ in range(num_blocks)]

    for line_idx, (sv, ev) in enumerate(linedefs):
        if sv >= len(vertices) or ev >= len(vertices):
            continue
        x1, y1 = vertices[sv]
        x2, y2 = vertices[ev]

        # Find all blocks this line segment touches
        bx1 = (min(x1, x2) - origin_x) // _BLOCK_SIZE
        by1 = (min(y1, y2) - origin_y) // _BLOCK_SIZE
        bx2 = (max(x1, x2) - origin_x) // _BLOCK_SIZE
        by2 = (max(y1, y2) - origin_y) // _BLOCK_SIZE

        # Clamp to grid bounds
        bx1 = max(0, min(bx1, columns - 1))
        by1 = max(0, min(by1, rows - 1))
        bx2 = max(0, min(bx2, columns - 1))
        by2 = max(0, min(by2, rows - 1))

        for by in range(by1, by2 + 1):
            for bx in range(bx1, bx2 + 1):
                block_idx = by * columns + bx
                if block_idx < num_blocks:
                    blocks[block_idx].append(line_idx)

    # Serialize: header + offset table + blocklists
    hdr_size = calcsize(BLOCKMAP_HEADER_FORMAT)
    # Offsets are in 16-bit words from start of lump
    offset_table_words = hdr_size // 2 + num_blocks  # header words + offset entries

    # Build blocklists and compute offsets
    blocklists = bytearray()
    offsets: list[int] = []

    for block in blocks:
        # Offset in 16-bit words from start of lump
        current_word_offset = offset_table_words + len(blocklists) // 2
        offsets.append(current_word_offset)
        # Blocklist: 0x0000 marker + linedef indices + 0xFFFF terminator
        blocklists += pack("<H", 0x0000)
        for line_idx in block:
            blocklists += pack("<H", line_idx)
        blocklists += pack("<H", 0xFFFF)

    # Assemble
    header = pack(BLOCKMAP_HEADER_FORMAT, origin_x, origin_y, columns, rows)
    offset_data = pack(f"<{num_blocks}H", *offsets)

    return header + offset_data + bytes(blocklists)
