"""Doom picture format decoder/encoder.

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

from functools import cached_property
from struct import calcsize, pack, unpack
from typing import Any

from PIL import Image

from ..exceptions import CorruptLumpError
from ..lumps.base import BaseLump
from ..lumps.playpal import Palette

_HEADER_FMT = "<HHhh"
_HEADER_SIZE = calcsize(_HEADER_FMT)


class Picture(BaseLump[Any]):
    """A single Doom-format picture (patch, sprite, or weapon graphic)."""

    @cached_property
    def _header(self) -> tuple[int, int, int, int]:
        self.seek(0)
        raw = self.read(_HEADER_SIZE)
        if raw is None:
            raise CorruptLumpError(f"{self.name!r}: picture lump is empty")
        if len(raw) < _HEADER_SIZE:
            raise CorruptLumpError(
                f"{self.name!r}: picture header too short ({len(raw)} < {_HEADER_SIZE} bytes)"
            )
        w, h, lx, ty = unpack(_HEADER_FMT, raw)
        return int(w), int(h), int(lx), int(ty)

    @property
    def pic_width(self) -> int:
        return self._header[0]

    @property
    def pic_height(self) -> int:
        return self._header[1]

    @property
    def left_offset(self) -> int:
        return self._header[2]

    @property
    def top_offset(self) -> int:
        return self._header[3]

    def decode(self, palette: Palette) -> Image.Image:
        """Decode this picture into a PIL RGBA image using *palette*.

        Transparent pixels (gaps between posts) are fully transparent (alpha=0).

        Raises:
            CorruptLumpError: if the lump payload is malformed (truncated header,
                out-of-range column offsets, truncated post data, etc.).
        """
        self.seek(0)
        hdr_raw = self.read(_HEADER_SIZE)
        if hdr_raw is None:
            raise CorruptLumpError(f"{self.name!r}: picture lump is empty")
        if len(hdr_raw) < _HEADER_SIZE:
            raise CorruptLumpError(
                f"{self.name!r}: picture header too short ({len(hdr_raw)} < {_HEADER_SIZE} bytes)"
            )
        width, height, _loff, _toff = unpack(_HEADER_FMT, hdr_raw)
        width, height = int(width), int(height)

        try:
            col_raw = self.read(width * 4)
        except EOFError as exc:
            raise CorruptLumpError(
                f"{self.name!r}: column offset table truncated (need {width * 4} bytes)"
            ) from exc
        if col_raw is None or len(col_raw) < width * 4:
            raise CorruptLumpError(
                f"{self.name!r}: column offset table truncated "
                f"(got {len(col_raw) if col_raw else 0}, need {width * 4} bytes)"
            )
        col_offsets = unpack(f"<{width}I", col_raw)

        lump_size = self._size or 0

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = img.load()
        assert pixels is not None  # PIL invariant

        def _draw_column(col_x: int, col_off: int) -> None:
            self.seek(col_off)
            while True:
                try:
                    td_raw = self.read(1)
                except EOFError as exc:
                    raise CorruptLumpError(
                        f"{self.name!r}: column {col_x} at offset {col_off} has no terminator"
                    ) from exc
                if not td_raw:
                    raise CorruptLumpError(
                        f"{self.name!r}: column {col_x} at offset {col_off} has no terminator"
                    )
                topdelta = td_raw[0]
                if topdelta == 0xFF:
                    break
                try:
                    len_raw = self.read(1)
                except EOFError as exc:
                    raise CorruptLumpError(
                        f"{self.name!r}: column {col_x} post length missing after topdelta {topdelta}"
                    ) from exc
                if not len_raw:
                    raise CorruptLumpError(
                        f"{self.name!r}: column {col_x} post length missing after topdelta {topdelta}"
                    )
                post_len = len_raw[0]
                self.read(1)  # pre-padding (unused)
                for row in range(post_len):
                    if topdelta + row >= height:
                        raise CorruptLumpError(
                            f"{self.name!r}: column {col_x} post writes past image height "
                            f"(topdelta={topdelta}, row={row}, height={height})"
                        )
                    try:
                        px_raw = self.read(1)
                    except EOFError as exc:
                        raise CorruptLumpError(
                            f"{self.name!r}: column {col_x} post data truncated at pixel {row}"
                        ) from exc
                    if not px_raw:
                        raise CorruptLumpError(
                            f"{self.name!r}: column {col_x} post data truncated at pixel {row}"
                        )
                    r, g, b = palette[px_raw[0]]
                    pixels[col_x, topdelta + row] = (r, g, b, 255)
                self.read(1)  # post-padding (unused)

        for col_x, col_off in enumerate(col_offsets):
            if col_off >= lump_size:
                raise CorruptLumpError(
                    f"{self.name!r}: column {col_x} offset {col_off} beyond lump size {lump_size}"
                )
            _draw_column(col_x, int(col_off))

        return img


def _nearest_palette_index(r: int, g: int, b: int, palette: Palette) -> int:
    """Return the index of the closest colour in *palette*."""
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


def encode_picture(  # pylint: disable=too-many-locals
    image: Image.Image,
    palette: Palette,
    left_offset: int = 0,
    top_offset: int = 0,
) -> bytes:
    """Encode a PIL RGBA image into Doom picture format bytes.

    Transparent pixels (alpha < 128) become gaps between posts.
    Opaque pixels are quantised to the nearest palette colour.
    """
    image = image.convert("RGBA")
    width, height = image.size
    raw = image.tobytes()  # RGBA interleaved, row-major

    def _px(x: int, y: int) -> tuple[int, int, int, int]:
        off = (y * width + x) * 4
        return raw[off], raw[off + 1], raw[off + 2], raw[off + 3]

    # Build column data
    column_data = bytearray()
    column_offsets: list[int] = []
    data_start = _HEADER_SIZE + width * 4  # header + offset table

    for col_x in range(width):
        column_offsets.append(data_start + len(column_data))

        # Collect runs of opaque pixels as posts
        row = 0
        while row < height:
            # Skip transparent pixels
            while row < height and _px(col_x, row)[3] < 128:
                row += 1
            if row >= height:
                break

            # Start of a post
            topdelta = row
            post_pixels: list[int] = []
            while row < height and _px(col_x, row)[3] >= 128 and len(post_pixels) < 255:
                r, g, b, _a = _px(col_x, row)
                post_pixels.append(_nearest_palette_index(r, g, b, palette))
                row += 1

            # Handle topdelta > 254 by splitting into multiple posts
            # (vanilla Doom uses single-byte topdelta, max 254)
            while topdelta > 254:
                # Emit a zero-length post at 254 to advance the cursor
                column_data.append(254)
                column_data.append(0)
                column_data.append(0)  # pre-pad
                column_data.append(0)  # post-pad
                topdelta -= 254

            column_data.append(topdelta)
            column_data.append(len(post_pixels))
            column_data.append(0)  # pre-padding
            column_data.extend(post_pixels)
            column_data.append(0)  # post-padding

        # End-of-column marker
        column_data.append(0xFF)

    # Assemble the lump
    header = pack(_HEADER_FMT, width, height, left_offset, top_offset)
    offsets = pack(f"<{width}I", *column_offsets)
    return header + offsets + bytes(column_data)
