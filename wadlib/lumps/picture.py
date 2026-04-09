"""Doom picture format decoder.

The picture format is a column-based, run-length encoded image used for
all patches, sprites, and weapon graphics in WAD files.

Binary layout:
  [2] width     (uint16)
  [2] height    (uint16)
  [2] left_offset  (int16) -- hotspot X relative to image origin
  [2] top_offset   (int16) -- hotspot Y relative to image origin
  [width * 4] column offsets (uint32 each) -- absolute positions in the lump

Each column is a series of "posts":
  [1] topdelta  (uint8)  -- 0xFF = end of column; row to start drawing at
  [1] length    (uint8)  -- number of pixels in this post
  [1] _pad      (uint8)  -- unused
  [length] pixel data    -- palette indices
  [1] _pad      (uint8)  -- unused
"""

from __future__ import annotations

from struct import calcsize, unpack
from typing import Any

from PIL import Image

from ..lumps.base import BaseLump
from ..lumps.playpal import Palette

_HEADER_FMT = "<HHhh"
_HEADER_SIZE = calcsize(_HEADER_FMT)


class Picture(BaseLump):
    """A single Doom-format picture (patch, sprite, or weapon graphic)."""

    @property
    def pic_width(self) -> int:
        self.seek(0)
        raw = self.read(_HEADER_SIZE)
        assert raw is not None
        return int(unpack(_HEADER_FMT, raw)[0])

    @property
    def pic_height(self) -> int:
        self.seek(0)
        raw = self.read(_HEADER_SIZE)
        assert raw is not None
        return int(unpack(_HEADER_FMT, raw)[1])

    @property
    def left_offset(self) -> int:
        self.seek(0)
        raw = self.read(_HEADER_SIZE)
        assert raw is not None
        return int(unpack(_HEADER_FMT, raw)[2])

    @property
    def top_offset(self) -> int:
        self.seek(0)
        raw = self.read(_HEADER_SIZE)
        assert raw is not None
        return int(unpack(_HEADER_FMT, raw)[3])

    def _draw_column(self, col_x: int, col_off: int, palette: Palette, pixels: Any) -> None:
        self.seek(col_off)
        while True:
            td_raw = self.read(1)
            assert td_raw is not None
            topdelta = td_raw[0]
            if topdelta == 0xFF:
                break
            len_raw = self.read(1)
            assert len_raw is not None
            post_len = len_raw[0]
            self.read(1)  # pre-padding (unused)
            for row in range(post_len):
                px_raw = self.read(1)
                assert px_raw is not None
                r, g, b = palette[px_raw[0]]
                pixels[col_x, topdelta + row] = (r, g, b, 255)
            self.read(1)  # post-padding (unused)

    def decode(self, palette: Palette) -> Image.Image:
        """Decode this picture into a PIL RGBA image using *palette*.

        Transparent pixels (gaps between posts) are fully transparent (alpha=0).
        """
        self.seek(0)
        hdr_raw = self.read(_HEADER_SIZE)
        assert hdr_raw is not None
        width, height, _loff, _toff = unpack(_HEADER_FMT, hdr_raw)
        width, height = int(width), int(height)

        col_raw = self.read(width * 4)
        assert col_raw is not None
        col_offsets = unpack(f"<{width}I", col_raw)

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = img.load()
        assert pixels is not None

        for col_x, col_off in enumerate(col_offsets):
            self._draw_column(col_x, int(col_off), palette, pixels)

        return img
