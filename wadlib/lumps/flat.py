"""Flat lump decoder — floor and ceiling textures.

Flats are raw 64x64 palette-indexed pixel arrays (4096 bytes), with no
header and no column encoding.  They live between F_START/F_END (or
FF_START/FF_END for PWAD patches) marker lumps in the directory.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

from ..lumps.base import BaseLump
from ..lumps.playpal import Palette

FLAT_SIZE = 64
FLAT_BYTES = FLAT_SIZE * FLAT_SIZE


class Flat(BaseLump[Any]):
    """A single 64x64 floor/ceiling texture."""

    def decode(self, palette: Palette) -> Image.Image:
        """Decode this flat into a 64x64 PIL RGB image using *palette*."""
        self.seek(0)
        raw = self.read(FLAT_BYTES)
        assert raw is not None
        img = Image.new("RGB", (FLAT_SIZE, FLAT_SIZE))
        pixels = img.load()
        assert pixels is not None
        for i, idx in enumerate(raw):
            x, y = i % FLAT_SIZE, i // FLAT_SIZE
            pixels[x, y] = palette[idx]
        return img
