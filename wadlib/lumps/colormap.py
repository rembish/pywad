"""COLORMAP lump decoder and builder.

The COLORMAP lump contains 34 remapping tables of 256 bytes each.  Each table
maps palette indices to darker versions of themselves for a given light level.

Tables 0-31 represent light levels from fullbright (0) to nearly black (31).
Table 32 is the invulnerability greyscale remap.
Table 33 is all-black (used by some engines as an extra dark level).

The builder generates these tables from a palette by computing the nearest
palette match for each colour darkened to the target light level.
"""

from __future__ import annotations

from typing import Any

from .base import BaseLump
from .playpal import Palette

_NUM_COLORMAPS = 34
_COLORMAP_SIZE = 256


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Parse a hex colour string to (r, g, b).

    Accepts ``"#RRGGBB"``, ``"RRGGBB"``, ``"#RGB"``, or ``"RGB"`` formats.

    Examples::

        hex_to_rgb("#FF0000")   # (255, 0, 0)
        hex_to_rgb("00FF00")    # (0, 255, 0)
        hex_to_rgb("#F00")      # (255, 0, 0)
    """
    c = color.lstrip("#")
    if len(c) == 3:
        c = c[0] * 2 + c[1] * 2 + c[2] * 2
    if len(c) != 6:
        raise ValueError(f"Invalid hex colour: {color!r}")
    try:
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        raise ValueError(f"Invalid hex colour: {color!r}") from None


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) to ``"#RRGGBB"`` hex string."""
    return f"#{r:02X}{g:02X}{b:02X}"


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

    def as_table(self, index: int) -> list[int]:
        """Return colormap *index* as a list of 256 remapped palette indices."""
        return list(self.get(index))

    def decode(self, index: int, palette: Palette) -> list[tuple[int, int, int]]:
        """Decode colormap *index* to 256 RGB colours using *palette*.

        Shows what each palette entry looks like after this light level
        is applied.
        """
        table = self.get(index)
        return [palette[table[i]] for i in range(256)]

    def all_tables(self) -> list[list[int]]:
        """Return all colormaps as a list of 256-int lists."""
        return [self.as_table(i) for i in range(self.count)]


# ---------------------------------------------------------------------------
# Colormap builder
# ---------------------------------------------------------------------------


def _nearest_index(r: int, g: int, b: int, palette: Palette) -> int:
    """Return the palette index closest to (r, g, b)."""
    best = 0
    best_d = float("inf")
    for i, (pr, pg, pb) in enumerate(palette):
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < best_d:
            best_d = d
            best = i
            if d == 0:
                break
    return best


def build_colormap(
    palette: Palette,
    *,
    num_levels: int = 32,
    invuln_tint: str | tuple[int, int, int] = "#00FF00",
) -> bytes:
    """Generate a standard 34-table COLORMAP from a palette.

    Parameters:
        palette:      A 256-colour palette (list of ``(r, g, b)`` tuples or hex strings).
        num_levels:   Number of darkening levels (default 32, standard Doom).
        invuln_tint:  Tint colour for the invulnerability greyscale map (table 32).
                      Accepts ``"#RRGGBB"`` hex string or ``(r, g, b)`` tuple.

    Returns:
        Raw bytes (34 x 256 = 8704 bytes) suitable for a COLORMAP lump.

    Example::

        from wadlib.lumps.colormap import build_colormap
        from wadlib.lumps.playpal import Palette

        pal: Palette = [(i, i, i) for i in range(256)]  # greyscale
        colormap_bytes = build_colormap(pal)
        colormap_bytes = build_colormap(pal, invuln_tint="#FFD700")  # gold invuln
    """
    # Normalise palette entries
    norm_pal: Palette = []
    for entry in palette:
        if isinstance(entry, str):
            norm_pal.append(hex_to_rgb(entry))
        else:
            norm_pal.append(entry)

    # Normalise invulnerability tint
    if isinstance(invuln_tint, str):
        inv_r, inv_g, inv_b = hex_to_rgb(invuln_tint)
    else:
        inv_r, inv_g, inv_b = invuln_tint

    tables = bytearray()

    # Tables 0 .. num_levels-1: progressive darkening
    for level in range(num_levels):
        # Factor: 1.0 (fullbright) down to ~0.0 (dark)
        factor = 1.0 - level / num_levels
        table = bytearray(_COLORMAP_SIZE)
        for i, (r, g, b) in enumerate(norm_pal):
            dr = int(r * factor + 0.5)
            dg = int(g * factor + 0.5)
            db = int(b * factor + 0.5)
            table[i] = _nearest_index(dr, dg, db, norm_pal)
        tables += table

    # Table 32: invulnerability greyscale tinted
    invuln = bytearray(_COLORMAP_SIZE)
    # Compute the tint's relative luminance weights
    inv_lum = max(inv_r + inv_g + inv_b, 1)
    inv_fr = inv_r / inv_lum
    inv_fg = inv_g / inv_lum
    inv_fb = inv_b / inv_lum
    for i, (r, g, b) in enumerate(norm_pal):
        grey = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
        tr = min(255, int(grey * inv_fr + 0.5))
        tg = min(255, int(grey * inv_fg + 0.5))
        tb = min(255, int(grey * inv_fb + 0.5))
        invuln[i] = _nearest_index(tr, tg, tb, norm_pal)
    tables += invuln

    # Table 33: all-black
    black_idx = _nearest_index(0, 0, 0, norm_pal)
    tables += bytes([black_idx]) * _COLORMAP_SIZE

    return bytes(tables)
