"""PLAYPAL lump reader — 14 palettes of 256 RGB triples each."""

from __future__ import annotations

from typing import Any

from ..directory import DirectoryEntry
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

    def __init__(self, entry: DirectoryEntry) -> None:
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

        Raises IndexError for out-of-range indices.
        """
        if index < 0 or index >= self.num_palettes:
            raise IndexError(index)
        offset = index * _PALETTE_SIZE
        self.seek(offset)
        raw = self.read(_PALETTE_SIZE)
        assert raw is not None
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
