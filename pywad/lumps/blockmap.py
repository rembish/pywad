"""REJECT and BLOCKMAP lump readers.

REJECT is a sector-visibility bitfield: bit [i*n+j] is set when monsters
in sector i cannot see sector j.

BLOCKMAP is a spatial index used by the engine for collision detection.
Its header contains the origin, column/row counts, and a flat array of
offsets into a variable-length list of linedefs per block.
"""

from __future__ import annotations

from struct import calcsize, unpack
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..directory import DirectoryEntry

BLOCKMAP_HEADER_FORMAT = "<hhHH"


class Reject:
    """Raw bitfield mapping sector-to-sector visibility."""

    def __init__(self, entry: DirectoryEntry) -> None:
        entry.owner.fd.seek(entry.offset)
        self._data: bytes = entry.owner.fd.read(entry.size)

    @property
    def data(self) -> bytes:
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
        ox, oy, cols, rows = unpack(BLOCKMAP_HEADER_FORMAT, fd.read(hdr_size))
        self._origin_x: int = int(ox)
        self._origin_y: int = int(oy)
        self._columns: int = int(cols)
        self._rows: int = int(rows)
        num_blocks = self._columns * self._rows
        raw = fd.read(num_blocks * 2)
        self._offsets: list[int] = [int(v) for v in unpack(f"<{num_blocks}H", raw)]

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

    def __repr__(self) -> str:
        return f"<BlockMap {self._columns}x{self._rows} origin=({self._origin_x},{self._origin_y})>"
