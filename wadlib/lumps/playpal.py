"""PLAYPAL lump reader — 14 palettes of 256 RGB triples each."""

from __future__ import annotations

from typing import Any

from ..exceptions import CorruptLumpError
from ..source import LumpSource
from .base import BaseLump

# Each palette: 256 colours x 3 bytes (R, G, B)
_PALETTE_SIZE = 256 * 3
_NUM_PALETTES = 14

# Type alias: a palette is a list of (r, g, b) tuples
Palette = list[tuple[int, int, int]]


class PlayPal(BaseLump[Any]):
    """PLAYPAL lump — up to 14 RGB palettes used by the game engine.

    Palette 0 is the standard game palette.  Palettes 1-8 are pain / pickup
    flashes.  Palettes 9-13 are radiation-suit tints.
    """

    def __init__(self, entry: LumpSource) -> None:
        super().__init__(entry)
        self._palette_index: int = 0

    @property
    def num_palettes(self) -> int:
        """Number of palettes stored in this lump (usually 14)."""
        if self._size is None:
            return 0
        return self._size // _PALETTE_SIZE

    def get_palette(self, index: int = 0) -> Palette:
        """Return palette *index* as a list of 256 (r, g, b) tuples.

        Raises:
            CorruptLumpError: if the lump is too short to contain any palette.
            IndexError: if *index* is out of range for a well-formed lump.
        """
        if (self._size or 0) < _PALETTE_SIZE:
            raise CorruptLumpError(
                f"PLAYPAL: lump too short for any palette "
                f"({self._size or 0} < {_PALETTE_SIZE} bytes)"
            )
        if index < 0 or index >= self.num_palettes:
            raise IndexError(index)
        offset = index * _PALETTE_SIZE
        self.seek(offset)
        raw = self.read(_PALETTE_SIZE)
        if raw is None or len(raw) < _PALETTE_SIZE:
            raise CorruptLumpError(
                f"PLAYPAL palette {index}: expected {_PALETTE_SIZE} bytes, "
                f"got {len(raw) if raw else 0}"
            )
        return [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, _PALETTE_SIZE, 3)]

    def __iter__(self) -> PlayPal:
        self._palette_index = 0  # reset on each new iteration
        return self

    def __next__(self) -> Palette:
        if self._palette_index >= self.num_palettes:
            raise StopIteration
        pal = self.get_palette(self._palette_index)
        self._palette_index += 1
        return pal

    def __len__(self) -> int:
        return self.num_palettes


def palette_to_bytes(palette: Palette) -> bytes:
    """Serialize a single 256-colour palette to 768 raw bytes."""
    buf = bytearray(256 * 3)
    for i, (r, g, b) in enumerate(palette):
        buf[i * 3] = r
        buf[i * 3 + 1] = g
        buf[i * 3 + 2] = b
    return bytes(buf)


def palettes_to_bytes(palettes: list[Palette]) -> bytes:
    """Serialize a list of palettes (typically 14) to a PLAYPAL lump."""
    return b"".join(palette_to_bytes(p) for p in palettes)
