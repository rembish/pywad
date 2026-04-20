"""AsciiMapRenderer — braille Unicode + ANSI 256-colour terminal map renderer.

Each character cell encodes a 2x4 braille dot grid (Unicode U+2800 block),
giving an effective resolution of (cols*2) x (rows*4) pixels for the map.

Linedefs are drawn with priority-based colouring so that higher-priority
categories (specials, secrets) always win when they share a cell with
lower-priority walls.  Drawing order: two-sided (lowest) -> one-sided ->
floor/ceiling changes -> specials -> secrets (highest).
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from typing import Any

from ..lumps.map import BaseMapEntry
from ..types import GameType, ThingCategory, get_category

# ---------------------------------------------------------------------------
# Braille dot bit layout (Unicode U+2800 block)
# ---------------------------------------------------------------------------
# Cell layout (2 cols x 4 rows):
#
#   col→  0   1
# row↓
#   0    (1) (4)   offset bits: 0  3
#   1    (2) (5)                1  4
#   2    (3) (6)                2  5
#   3    (7) (8)                6  7
#
# _BRAILLE_BIT[col][row] -> bit index added to 0x2800
_BRAILLE_BIT: tuple[tuple[int, int, int, int], tuple[int, int, int, int]] = (
    (0, 1, 2, 6),
    (3, 4, 5, 7),
)

# ---------------------------------------------------------------------------
# ANSI 256-colour codes and priorities for each linedef category
# ---------------------------------------------------------------------------
_C_TWO_SIDED = 238    # dark grey
_C_CEIL_CHANGE = 247  # light grey
_C_FLOOR_CHANGE = 220  # yellow
_C_ONE_SIDED = 255    # bright white
_C_SPECIAL = 51       # cyan
_C_SECRET = 201       # magenta

_PRI_TWO_SIDED = 0
_PRI_CEIL_CHANGE = 1
_PRI_FLOOR_CHANGE = 2
_PRI_ONE_SIDED = 3
_PRI_SPECIAL = 4
_PRI_SECRET = 5
_PRI_THING = 10  # always above all linedefs

# (glyph-unused, ANSI 256 color) per thing category — color used for dot cluster
_THING_COLOR: dict[ThingCategory, int] = {
    ThingCategory.PLAYER: 46,       # bright green
    ThingCategory.MONSTER: 196,     # red
    ThingCategory.WEAPON: 220,      # yellow
    ThingCategory.AMMO: 220,        # yellow
    ThingCategory.HEALTH: 82,       # green
    ThingCategory.ARMOR: 39,        # blue
    ThingCategory.KEY: 201,         # magenta
    ThingCategory.POWERUP: 255,     # white
    ThingCategory.DECORATION: 242,  # mid grey
    ThingCategory.UNKNOWN: 240,     # dark grey
}

_FLAG_SECRET = 0x0020
_FLAG_NOT_SINGLEPLAYER = 0x0010
_COOP_PLAYER_STARTS = frozenset({2, 3, 4})


# ---------------------------------------------------------------------------
# Bresenham line iterator
# ---------------------------------------------------------------------------

def _bresenham(x0: int, y0: int, x1: int, y1: int) -> Iterator[tuple[int, int]]:
    """Yield integer (x, y) coordinates along the line segment."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


# ---------------------------------------------------------------------------
# Braille canvas
# ---------------------------------------------------------------------------

class BrailleCanvas:
    """Character-cell canvas using Unicode braille patterns (U+2800-U+28FF).

    Pixel (px, py) maps to character cell (px//2, py//4) and braille dot
    (px%2, py%4) within it.  Each cell stores the accumulated dot bitmask
    plus the colour/priority of the highest-priority segment drawn there.
    """

    def __init__(self, cols: int, rows: int) -> None:
        self.cols = cols
        self.rows = rows
        n = cols * rows
        self._bits: bytearray = bytearray(n)   # braille bitmask per cell
        self._color: list[int] = [0] * n       # ANSI 256-colour index
        self._pri: list[int] = [-1] * n        # highest priority seen (-1 = empty)

    @property
    def dot_width(self) -> int:
        """Horizontal dot resolution."""
        return self.cols * 2

    @property
    def dot_height(self) -> int:
        """Vertical dot resolution."""
        return self.rows * 4

    def set_pixel(self, px: int, py: int, color: int, priority: int) -> None:
        """Set a single dot; updates cell colour when priority >= existing."""
        col = px >> 1
        row = py >> 2
        if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
            return
        cell = row * self.cols + col
        self._bits[cell] |= 1 << _BRAILLE_BIT[px & 1][py - row * 4]
        if priority >= self._pri[cell]:
            self._pri[cell] = priority
            self._color[cell] = color

    def render(self) -> str:
        """Return the canvas as an ANSI-coloured multi-line braille string."""
        lines: list[str] = []
        for row in range(self.rows):
            parts: list[str] = []
            cur = -1
            for col in range(self.cols):
                cell = row * self.cols + col
                bits = self._bits[cell]
                if bits == 0:
                    if cur != -1:
                        parts.append("\033[0m")
                        cur = -1
                    parts.append(" ")
                else:
                    c = self._color[cell]
                    if c != cur:
                        parts.append(f"\033[38;5;{c}m")
                        cur = c
                    parts.append(chr(0x2800 + bits))
            if cur != -1:
                parts.append("\033[0m")
            lines.append("".join(parts))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Map renderer
# ---------------------------------------------------------------------------

class AsciiMapRenderer:
    """Render a Doom map to a Unicode braille + ANSI 256-colour terminal string.

    Args:
        map_entry:   Parsed map to render.
        cols:        Terminal columns (0 = auto-detect).
        rows:        Terminal rows for the canvas (0 = auto-detect, minus 3 for
                     title, legend, and shell prompt).
        show_things: Draw thing markers as coloured dot clusters.
        multiplayer: Include NOT_SINGLEPLAYER things.
        game:        Game type for thing classification (default: DOOM).
    """

    def __init__(
        self,
        map_entry: BaseMapEntry,
        cols: int = 0,
        rows: int = 0,
        show_things: bool = True,
        multiplayer: bool = False,
        game: GameType = GameType.DOOM,
    ) -> None:
        term = shutil.get_terminal_size((80, 24))
        cols = cols or term.columns
        rows = rows or max(4, term.lines - 3)

        self._map = map_entry
        self._canvas = BrailleCanvas(cols, rows)
        self._show_things = show_things
        self._multiplayer = multiplayer
        self._game = game

        bounds = map_entry.boundaries
        self._min_x = bounds[0].x
        self._min_y = bounds[0].y
        self._max_x = bounds[1].x
        self._max_y = bounds[1].y

        map_w = max(self._max_x - self._min_x, 1)
        map_h = max(self._max_y - self._min_y, 1)

        dw = self._canvas.dot_width
        dh = self._canvas.dot_height

        # Uniform scale so circles stay round (same pixel-size per map unit in
        # x and y).  1-dot margin on each side prevents clipping at edges.
        self._scale = min((dw - 2) / map_w, (dh - 2) / map_h)
        self._off_x = (dw - int(map_w * self._scale)) // 2
        self._off_y = (dh - int(map_h * self._scale)) // 2

    def _dot(self, x: int, y: int) -> tuple[int, int]:
        """Convert WAD map coordinates to braille dot coordinates (Y flipped)."""
        return (
            int((x - self._min_x) * self._scale) + self._off_x,
            int((self._max_y - y) * self._scale) + self._off_y,
        )

    def _seg(self, x0: int, y0: int, x1: int, y1: int, color: int, pri: int) -> None:
        for px, py in _bresenham(x0, y0, x1, y1):
            self._canvas.set_pixel(px, py, color, pri)

    def _classify(self, line: Any) -> tuple[int, int]:
        """Return (ansi_color, priority) for a linedef."""
        m = self._map
        left_sd = getattr(line, "left_sidedef", -1)
        one_sided = left_sd in (-1, 0xFFFF)

        if getattr(line, "flags", 0) & _FLAG_SECRET:
            return _C_SECRET, _PRI_SECRET

        if one_sided:
            if getattr(line, "special_type", 0):
                return _C_SPECIAL, _PRI_SPECIAL
            return _C_ONE_SIDED, _PRI_ONE_SIDED

        if m.sidedefs and m.sectors:
            r_sd = getattr(line, "right_sidedef", 0)
            r_idx = getattr(m.sidedefs.get(r_sd), "sector", None)
            l_idx = getattr(m.sidedefs.get(left_sd), "sector", None)
            r_sec = m.sectors.get(r_idx) if r_idx is not None else None
            l_sec = m.sectors.get(l_idx) if l_idx is not None else None
            if r_sec and l_sec:
                if r_sec.floor_height != l_sec.floor_height:
                    return _C_FLOOR_CHANGE, _PRI_FLOOR_CHANGE
                if r_sec.ceiling_height != l_sec.ceiling_height:
                    return _C_CEIL_CHANGE, _PRI_CEIL_CHANGE

        return _C_TWO_SIDED, _PRI_TWO_SIDED

    def _draw_linedefs(self) -> None:
        m = self._map
        if not m.lines or not m.vertices:
            return
        # Collect all segments, then draw lowest priority first so higher-
        # priority colours overwrite shared cells.
        segs: list[tuple[int, int, int, int, int, int]] = []
        for line in m.lines:
            v1 = m.vertices.get(line.start_vertex)
            v2 = m.vertices.get(getattr(line, "finish_vertex", -1))
            if v1 is None or v2 is None:
                continue
            color, pri = self._classify(line)
            x0, y0 = self._dot(v1.x, v1.y)
            x1, y1 = self._dot(v2.x, v2.y)
            segs.append((x0, y0, x1, y1, color, pri))
        segs.sort(key=lambda s: s[5])
        for x0, y0, x1, y1, color, pri in segs:
            self._seg(x0, y0, x1, y1, color, pri)

    def _draw_things(self) -> None:
        m = self._map
        if not m.things:
            return
        for thing in m.things:
            if not self._multiplayer:
                if getattr(thing, "flags", 0) & _FLAG_NOT_SINGLEPLAYER:
                    continue
                if getattr(thing, "type", None) in _COOP_PLAYER_STARTS:
                    continue
            cat = get_category(getattr(thing, "type", 0), self._game)
            color = _THING_COLOR[cat]
            cx, cy = self._dot(thing.x, thing.y)
            # 2x2 dot cluster so things are visible even at small scales
            for dpx in range(2):
                for dpy in range(2):
                    self._canvas.set_pixel(cx + dpx - 1, cy + dpy - 1, color, _PRI_THING)

    def render(self) -> str:
        """Draw all layers and return the ANSI braille string."""
        self._draw_linedefs()
        if self._show_things:
            self._draw_things()
        return self._canvas.render()

    @staticmethod
    def legend() -> str:
        """Return a colour-coded legend line suitable for printing below the map."""

        def c(code: int, sym: str) -> str:
            return f"\033[38;5;{code}m{sym}\033[0m"

        return (
            f" {c(_C_ONE_SIDED, '─')} wall"
            f"  {c(_C_TWO_SIDED, '─')} 2-sided"
            f"  {c(_C_FLOOR_CHANGE, '─')} step"
            f"  {c(_C_CEIL_CHANGE, '─')} ceiling"
            f"  {c(_C_SPECIAL, '─')} special"
            f"  {c(_C_SECRET, '─')} secret"
            f"  {c(46, '●')} player"
            f"  {c(196, '●')} monster"
            f"  {c(82, '●')} health"
            f"  {c(201, '●')} key"
        )
