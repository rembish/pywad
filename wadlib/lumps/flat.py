"""Flat lump decoder/encoder — floor and ceiling textures.

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


def _nearest_palette_index(r: int, g: int, b: int, palette: Palette) -> int:
    """Return the index of the closest colour in *palette* (Euclidean distance)."""
    best_idx = 0
    best_dist = float("inf")
    for i, (pr, pg, pb) in enumerate(palette):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_dist:
            best_dist = d
            best_idx = i
            if d == 0:
                break
    return best_idx


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


def encode_flat(image: Image.Image, palette: Palette) -> bytes:
    """Encode a PIL image as a 64x64 flat (4096 raw palette indices).

    The image is resized to 64x64 if necessary, then each pixel is
    quantised to the nearest palette colour.
    """
    if image.size != (FLAT_SIZE, FLAT_SIZE):
        image = image.resize((FLAT_SIZE, FLAT_SIZE), Image.Resampling.NEAREST)
    image = image.convert("RGB")
    raw = image.tobytes()
    buf = bytearray(FLAT_BYTES)
    for i in range(FLAT_BYTES):
        off = i * 3
        buf[i] = _nearest_palette_index(raw[off], raw[off + 1], raw[off + 2], palette)
    return bytes(buf)
