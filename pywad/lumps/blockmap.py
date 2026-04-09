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
        self._size = entry.size
        self._offset = entry.offset
        self._owner = entry.owner
        self._data: bytes | None = None

    @property
    def data(self) -> bytes:
        if self._data is None:
            self._owner.fd.seek(self._offset)
            self._data = self._owner.fd.read(self._size)
        return self._data

    def can_see(self, from_sector: int, to_sector: int, num_sectors: int) -> bool:
        """Return True if *from_sector* CAN potentially see *to_sector*.

        A set bit means the engine skips the sight check (rejected).
        An unset bit means sight is possible.
        """
        bit_index = from_sector * num_sectors + to_sector
        byte_index, bit_offset = divmod(bit_index, 8)
        if byte_index >= len(self.data):
            return True
        return not bool(self.data[byte_index] & (1 << bit_offset))

    def __repr__(self) -> str:
        return f"<Reject {self._size} bytes>"


class BlockMap:
    """Spatial acceleration structure for linedef collision queries."""

    def __init__(self, entry: DirectoryEntry) -> None:
        self._size = entry.size
        self._offset = entry.offset
        self._owner = entry.owner
        self._parsed = False

        self._origin_x: int = 0
        self._origin_y: int = 0
        self._columns: int = 0
        self._rows: int = 0
        self._offsets: list[int] = []

    def _parse(self) -> None:
        if self._parsed:
            return
        fd = self._owner.fd
        hdr_size = calcsize(BLOCKMAP_HEADER_FORMAT)
        fd.seek(self._offset)
        self._origin_x, self._origin_y, self._columns, self._rows = unpack(
            BLOCKMAP_HEADER_FORMAT, fd.read(hdr_size)
        )
        num_blocks = self._columns * self._rows
        raw = fd.read(num_blocks * 2)
        self._offsets = list(unpack(f"<{num_blocks}H", raw))
        self._parsed = True

    @property
    def origin_x(self) -> int:
        self._parse()
        return self._origin_x

    @property
    def origin_y(self) -> int:
        self._parse()
        return self._origin_y

    @property
    def columns(self) -> int:
        self._parse()
        return self._columns

    @property
    def rows(self) -> int:
        self._parse()
        return self._rows

    @property
    def offsets(self) -> list[int]:
        self._parse()
        return self._offsets

    @property
    def block_count(self) -> int:
        self._parse()
        return self._columns * self._rows

    def __repr__(self) -> str:
        self._parse()
        return f"<BlockMap {self._columns}x{self._rows} origin=({self._origin_x},{self._origin_y})>"
