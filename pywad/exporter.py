"""Map renderer — produces a PIL Image from a parsed map entry.

Coordinate system notes:
  WAD uses a right-hand 2D system (Y increases upward).
  PIL has Y increasing downward, so we flip Y when projecting.

Colours:
  One-sided linedefs (solid walls) — white
  Two-sided linedefs (sector boundaries) — grey
  Things (entities) — red ellipses
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image
from PIL.ImageDraw import ImageDraw

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry

# Padding around the map geometry in pixels
_PADDING = 40
# Image dimension cap (avoids multi-GB images for huge maps)
_MAX_DIM = 4096


class MapExporter:
    def __init__(self, map_entry: BaseMapEntry, scale: float = 0.0) -> None:
        """
        Args:
            map_entry: parsed map to render.
            scale: pixels-per-map-unit. Pass 0 (default) to auto-fit the
                   map into _MAX_DIM x _MAX_DIM.
        """
        self.level = map_entry
        bounds = map_entry.boundaries
        self._min_x = bounds[0].x
        self._min_y = bounds[0].y
        self._max_x = bounds[1].x
        self._max_y = bounds[1].y

        map_w = max(self._max_x - self._min_x, 1)
        map_h = max(self._max_y - self._min_y, 1)

        if scale <= 0:
            scale = min(
                (_MAX_DIM - 2 * _PADDING) / map_w,
                (_MAX_DIM - 2 * _PADDING) / map_h,
            )
        self._scale = scale

        img_w = int(map_w * scale) + 2 * _PADDING
        img_h = int(map_h * scale) + 2 * _PADDING

        self.im = Image.new("RGB", (img_w, img_h), color=(20, 20, 20))
        self.draw = ImageDraw(self.im)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _px(self, x: int, y: int) -> tuple[int, int]:
        """Map WAD coordinates to pixel coordinates (flips Y)."""
        px = int((x - self._min_x) * self._scale) + _PADDING
        py = int((self._max_y - y) * self._scale) + _PADDING
        return px, py

    # ------------------------------------------------------------------
    # Drawing passes
    # ------------------------------------------------------------------

    def _draw_linedefs(self) -> None:
        lines = self.level.lines
        if not lines:
            return
        for line in lines:
            verts = self.level.vertices
            if verts is None:
                break
            v1 = verts.get(line.start_vertex)
            v2 = verts.get(line.finish_vertex)
            if v1 is None or v2 is None:
                continue
            x1, y1 = self._px(v1.x, v1.y)
            x2, y2 = self._px(v2.x, v2.y)
            # left_sidedef == -1 (or 0xFFFF) means one-sided (solid wall)
            one_sided = line.left_sidedef in (-1, 0xFFFF)
            colour = (220, 220, 220) if one_sided else (100, 100, 100)
            self.draw.line([(x1, y1), (x2, y2)], fill=colour, width=1)

    def _draw_things(self) -> None:
        if not self.level.things:
            return
        r = max(2, int(6 * self._scale))
        for thing in self.level.things:
            cx, cy = self._px(thing.x, thing.y)
            self.draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=(200, 50, 50),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self) -> None:
        """Render linedefs then things onto the internal image."""
        self._draw_linedefs()
        self._draw_things()

    def show(self) -> None:
        """Display the rendered image (opens the system viewer)."""
        self.im.show()

    def save(self, path: str) -> None:
        """Save the rendered image to *path*."""
        self.im.save(path)
