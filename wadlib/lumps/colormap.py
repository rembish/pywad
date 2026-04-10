"""COLORMAP lump decoder."""

from __future__ import annotations

from typing import Any

from .base import BaseLump

_NUM_COLORMAPS = 34
_COLORMAP_SIZE = 256


class ColormapLump(BaseLump[Any]):
    """The COLORMAP lump: 34 light-level remapping tables of 256 bytes each."""

    @property
    def count(self) -> int:
        """Number of colormaps (always 34 for standard Doom WADs)."""
        return len(self.raw()) // _COLORMAP_SIZE

    def get(self, index: int, default: object = None) -> bytes:  # pylint: disable=unused-argument
        """Return colormap *index* as 256 raw bytes (palette-index remapping table)."""
        data = self.raw()
        offset = index * _COLORMAP_SIZE
        return data[offset : offset + _COLORMAP_SIZE]

    def apply(self, colormap_index: int, palette_index: int) -> int:
        """Remap *palette_index* through colormap *colormap_index*."""
        return self.get(colormap_index)[palette_index]
