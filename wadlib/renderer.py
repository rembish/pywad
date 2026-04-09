"""MapRenderer — produces a PIL Image from a parsed map entry.

Supersedes the old MapExporter.  Key improvements:
  - Thing categories: players/monsters draw a direction arrow; pickups,
    keys, powerups, armor, health each use a distinct colour and shape.
  - Optional floor-texture rendering: fills each BSP subsector polygon
    with the sector's tiled floor flat (requires a WadFile for flat lookups).
  - RenderOptions dataclass controls all behaviour flags.

Coordinate system:
  WAD uses a right-hand 2D system (Y increases upward).
  PIL has Y increasing downward — we flip Y when projecting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PIL import Image
from PIL.ImageDraw import ImageDraw

from .doom_types import ThingCategory, get_category
from .lumps.map import BaseMapEntry
from .lumps.nodes import SSECTOR_FLAG
from .lumps.playpal import Palette

if TYPE_CHECKING:
    from .wad import WadFile

_PADDING = 40
_MAX_DIM = 4096

# ---- Rendering colours per category ----------------------------------------
_CATEGORY_COLOUR: dict[ThingCategory, tuple[int, int, int]] = {
    ThingCategory.PLAYER: (0, 220, 220),  # cyan
    ThingCategory.MONSTER: (220, 50, 50),  # red
    ThingCategory.WEAPON: (255, 220, 0),  # yellow
    ThingCategory.AMMO: (255, 140, 0),  # orange
    ThingCategory.HEALTH: (50, 220, 50),  # green
    ThingCategory.ARMOR: (50, 150, 255),  # blue
    ThingCategory.KEY: (255, 0, 255),  # magenta
    ThingCategory.POWERUP: (255, 255, 255),  # white
    ThingCategory.DECORATION: (90, 90, 90),  # dark grey
    ThingCategory.UNKNOWN: (50, 50, 50),  # very dark
}


def _clip_poly(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    polygon: list[tuple[float, float]],
    nx: float,
    ny: float,
    ndx: float,
    ndy: float,
    keep_right: bool,
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip of a convex polygon against a BSP half-plane.

    Half-plane convention (map-coordinate cross product):
        cross = (P.x - nx)*ndy - (P.y - ny)*ndx
        keep_right=True  → keep where cross >= 0  (Doom "right child" side)
        keep_right=False → keep where cross <= 0  (Doom "left child" side)
    """
    if len(polygon) < 2:
        return []

    def _cross(p: tuple[float, float]) -> float:
        return (p[0] - nx) * ndy - (p[1] - ny) * ndx

    def _intersect(p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
        c1, c2 = _cross(p1), _cross(p2)
        denom = c1 - c2
        if denom == 0.0:
            return p1
        t = c1 / denom
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))

    result: list[tuple[float, float]] = []
    n = len(polygon)
    for i in range(n):
        curr = polygon[i]
        prev = polygon[i - 1]
        cc = _cross(curr)
        pc = _cross(prev)
        curr_in = cc >= 0 if keep_right else cc <= 0
        prev_in = pc >= 0 if keep_right else pc <= 0
        if curr_in:
            if not prev_in:
                result.append(_intersect(prev, curr))
            result.append(curr)
        elif prev_in:
            result.append(_intersect(prev, curr))
    return result


@dataclass
class RenderOptions:
    """Controls what the renderer draws and at what scale."""

    scale: float = 0.0
    """Pixels per map unit.  0 = auto-fit to _MAX_DIM."""

    show_things: bool = True
    """Draw thing sprites (players, monsters, pickups, decorations)."""

    show_floors: bool = False
    """Fill subsector polygons with the sector's floor flat texture.
    Requires a WadFile to be passed to MapRenderer."""

    palette_index: int = 0
    """Index into PLAYPAL (0 = standard game palette)."""

    thing_scale: float = 1.0
    """Multiplier applied to the base thing-marker radius."""

    alpha: bool = False
    """Produce an RGBA image with transparent void areas.
    When False (default) the output is RGB with a dark background."""


class MapRenderer:
    """Renders a parsed map to a PIL RGB image.

    Args:
        map_entry:  Parsed map (BaseMapEntry) to render.
        wad:        Open WadFile — required only when show_floors=True or
                    a custom palette is needed.
        options:    RenderOptions controlling scale, visibility flags, etc.
                    Defaults to RenderOptions() (auto-scale, things on,
                    no floors).
    """

    def __init__(
        self,
        map_entry: BaseMapEntry,
        wad: WadFile | None = None,
        options: RenderOptions | None = None,
    ) -> None:
        self.level = map_entry
        self._wad = wad
        self._opts = options or RenderOptions()

        bounds = map_entry.boundaries
        self._min_x = bounds[0].x
        self._min_y = bounds[0].y
        self._max_x = bounds[1].x
        self._max_y = bounds[1].y

        map_w = max(self._max_x - self._min_x, 1)
        map_h = max(self._max_y - self._min_y, 1)

        scale = self._opts.scale
        if scale <= 0:
            scale = min(
                (_MAX_DIM - 2 * _PADDING) / map_w,
                (_MAX_DIM - 2 * _PADDING) / map_h,
            )
        self._scale = scale

        img_w = int(map_w * scale) + 2 * _PADDING
        img_h = int(map_h * scale) + 2 * _PADDING
        if self._opts.alpha:
            self.im = Image.new("RGBA", (img_w, img_h), color=(0, 0, 0, 0))
        else:
            self.im = Image.new("RGB", (img_w, img_h), color=(20, 20, 20))
        self.draw = ImageDraw(self.im)

        # Resolve palette once
        self._palette: Palette | None = None
        if wad is not None and wad.playpal is not None:
            self._palette = wad.playpal.get_palette(self._opts.palette_index)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _px(self, x: int, y: int) -> tuple[int, int]:
        """Map WAD coordinates to image pixel coordinates (flips Y)."""
        px = int((x - self._min_x) * self._scale) + _PADDING
        py = int((self._max_y - y) * self._scale) + _PADDING
        return px, py

    # ------------------------------------------------------------------
    # Floor rendering — BSP tree walk with Sutherland-Hodgman clipping
    # ------------------------------------------------------------------
    # Doom only stores linedef-based segs in the SEGS lump; the partition-
    # line segments that complete each subsector's convex boundary are
    # implicit in the BSP node tree.  Building the polygon from seg
    # start-vertices alone misses those boundary vertices, leaving ~44% of
    # subsectors with fewer than 3 points.
    #
    # The correct approach: walk the NODE tree recursively, clipping a
    # bounding polygon at each partition plane (Sutherland-Hodgman).  At
    # each leaf (subsector) the clipped polygon IS the full convex region.

    def _build_flat_tile(self, flat_name: str) -> Image.Image | None:
        """Decode and scale a flat for tiling."""
        if self._wad is None or self._palette is None:
            return None
        flat = self._wad.get_flat(flat_name)
        if flat is None:
            return None
        img = flat.decode(self._palette)
        tile_px = max(1, int(64 * self._scale))
        return img.resize((tile_px, tile_px), Image.Resampling.NEAREST)

    def _tile_canvas(self, tile: Image.Image) -> Image.Image:
        """Produce a canvas-sized image tiled with *tile* (same mode as self.im)."""
        mode = self.im.mode
        tiled = Image.new(mode, self.im.size)
        src = tile.convert(mode)
        tw, th = src.size
        for ty in range(0, self.im.height, th):
            for tx in range(0, self.im.width, tw):
                tiled.paste(src, (tx, ty))
        return tiled

    def _sector_for_seg(self, seg: Any) -> int | None:
        """Return the sector index that a Seg faces, or None."""
        m = self.level
        if m.lines is None or m.sidedefs is None:
            return None
        line = m.lines.get(seg.linedef)
        if line is None:
            return None
        sd_idx = line.right_sidedef if seg.direction == 0 else line.left_sidedef
        if sd_idx in (-1, 0xFFFF):
            return None
        sd = m.sidedefs.get(sd_idx)
        return sd.sector if sd is not None else None

    def _sector_from_ssector(self, ssector: Any) -> int | None:
        """Return the sector index for a subsector (from any of its segs)."""
        m = self.level
        if not m.segs:
            return None
        for j in range(ssector.seg_count):
            seg = m.segs.get(ssector.first_seg + j)
            if seg is None:
                continue
            sector_idx = self._sector_for_seg(seg)
            if sector_idx is not None:
                return sector_idx
        return None

    def _ssector_polygon(self, ssector_idx: int, ssector: Any) -> list[tuple[int, int]] | None:
        """Build the subsector's floor polygon.

        Primary: collect unique (start_vertex, end_vertex) map-coordinates from
        each seg, project to pixel space.  Works for 3+ seg subsectors.

        Fallback: for degenerate 1-seg subsectors (BSP partition artefacts),
        walk the NODE tree clipping the map bounding box down to the subsector's
        convex region (Sutherland-Hodgman).
        """
        m = self.level
        if not (m.segs and m.vertices):
            return None
        seen: dict[tuple[int, int], None] = {}
        for j in range(ssector.seg_count):
            seg = m.segs.get(ssector.first_seg + j)
            if seg is None:
                break
            for vid in (seg.start_vertex, seg.end_vertex):
                v = m.vertices.get(vid)
                if v is None:
                    break
                seen[(v.x, v.y)] = None
        points = [self._px(x, y) for x, y in seen]
        if len(points) >= 3:
            return points
        # Fallback: BSP walk to get the convex region for this subsector.
        return self._ssector_polygon_bsp(ssector_idx)

    def _ssector_polygon_bsp(self, target_idx: int) -> list[tuple[int, int]] | None:
        """BSP-walk fallback: clip map bounding box to the target subsector's region."""
        m = self.level
        if not m.nodes:
            return None
        # Initial convex polygon = map bounds in map coordinates (float).
        poly: list[tuple[float, float]] = [
            (float(self._min_x), float(self._min_y)),
            (float(self._max_x), float(self._min_y)),
            (float(self._max_x), float(self._max_y)),
            (float(self._min_x), float(self._max_y)),
        ]
        found = self._bsp_clip(m.nodes.get(len(m.nodes) - 1), target_idx, poly)
        if found is None or len(found) < 3:
            return None
        return [self._px(int(x), int(y)) for x, y in found]

    def _bsp_clip(
        self,
        node: Any,
        target_idx: int,
        poly: list[tuple[float, float]],
    ) -> list[tuple[float, float]] | None:
        """Recursively walk BSP tree, clipping *poly* at each partition.

        Returns the clipped polygon when the subsector at *target_idx* is reached.
        """
        if node is None:
            return None
        nx, ny, ndx, ndy = float(node.x), float(node.y), float(node.dx), float(node.dy)
        right_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=True)
        left_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=False)
        m = self.level
        for child_idx, child_poly in (
            (node.right_child, right_poly),
            (node.left_child, left_poly),
        ):
            if len(child_poly) < 3:
                continue
            if child_idx & SSECTOR_FLAG:
                if (child_idx & ~SSECTOR_FLAG) == target_idx:
                    return child_poly
            else:
                child_node = m.nodes.get(child_idx) if m.nodes else None
                result = self._bsp_clip(child_node, target_idx, child_poly)
                if result is not None:
                    return result
        return None

    def _fill_ssector_polygon(
        self,
        ssector_idx: int,
        ssector: Any,
        tile_cache: dict[str, Image.Image | None],
        tiled_canvas_cache: dict[str, Image.Image],
    ) -> None:
        """Render the floor flat for one subsector."""
        m = self.level
        sector_idx = self._sector_from_ssector(ssector)
        if sector_idx is None:
            return
        sector = m.sectors.get(sector_idx) if m.sectors else None
        if sector is None:
            return
        flat_name = sector.floor_texture.strip("\x00").rstrip().upper()
        if not flat_name or flat_name == "-":
            return
        if flat_name not in tile_cache:
            tile_cache[flat_name] = self._build_flat_tile(flat_name)
        tile = tile_cache[flat_name]
        if tile is None:
            return
        if flat_name not in tiled_canvas_cache:
            tiled_canvas_cache[flat_name] = self._tile_canvas(tile)
        tiled = tiled_canvas_cache[flat_name]
        points = self._ssector_polygon(ssector_idx, ssector)
        if points is None:
            return
        mask = Image.new("L", self.im.size, 0)
        ImageDraw(mask).polygon(points, fill=255, outline=255)
        self.im.paste(tiled, (0, 0), mask=mask)

    def _draw_floors(self) -> None:
        m = self.level
        if not (m.ssectors and m.segs and m.vertices and m.sectors):
            return
        if self._wad is None or self._palette is None:
            return
        tile_cache: dict[str, Image.Image | None] = {}
        tiled_canvas_cache: dict[str, Image.Image] = {}
        for i, ssector in enumerate(m.ssectors):
            self._fill_ssector_polygon(i, ssector, tile_cache, tiled_canvas_cache)

    # ------------------------------------------------------------------
    # Linedef rendering
    # ------------------------------------------------------------------

    def _iter_linedef_endpoints(
        self,
    ) -> list[tuple[tuple[int, int], tuple[int, int], bool]]:
        """Return [(p1, p2, one_sided)] for all linedefs with valid vertices."""
        result: list[tuple[tuple[int, int], tuple[int, int], bool]] = []
        m = self.level
        if not m.lines or not m.vertices:
            return result
        for line in m.lines:
            v1 = m.vertices.get(line.start_vertex)
            v2 = m.vertices.get(getattr(line, "finish_vertex", getattr(line, "end_vertex", -1)))
            if v1 is None or v2 is None:
                continue
            one_sided = line.left_sidedef in (-1, 0xFFFF)
            result.append((self._px(v1.x, v1.y), self._px(v2.x, v2.y), one_sided))
        return result

    def _draw_linedefs(self) -> None:
        lines = self._iter_linedef_endpoints()
        if self._opts.alpha:
            # Black outline pass on exterior (one-sided) walls.
            for p1, p2, one_sided in lines:
                if one_sided:
                    self.draw.line([p1, p2], fill=(0, 0, 0, 255), width=5)
        for p1, p2, one_sided in lines:
            colour = (220, 220, 220) if one_sided else (110, 110, 110)
            self.draw.line([p1, p2], fill=colour, width=1)

    # ------------------------------------------------------------------
    # Thing rendering
    # ------------------------------------------------------------------

    def _thing_facing(self, thing: Any) -> int:
        """Return facing angle in degrees (0=East, CCW positive)."""
        return int(getattr(thing, "direction", getattr(thing, "angle", 0)))

    def _draw_direction_triangle(
        self,
        centre: tuple[int, int],
        angle_deg: int,
        colour: tuple[int, int, int],
        size: int,
    ) -> None:
        """Draw a filled equilateral triangle pointing in *angle_deg* direction."""
        cx, cy = centre

        def _pt(deg: float) -> tuple[int, int]:
            r = math.radians(deg)
            return (cx + int(math.cos(r) * size), cy - int(math.sin(r) * size))

        tip = _pt(angle_deg)
        b1 = _pt(angle_deg + 120)
        b2 = _pt(angle_deg - 120)
        self.draw.polygon([tip, b1, b2], fill=colour)

    def _draw_thing(self, thing: Any) -> None:
        cat = get_category(thing.type)
        colour = _CATEGORY_COLOUR[cat]
        cx, cy = self._px(thing.x, thing.y)
        r = max(2, int(5 * self._scale * self._opts.thing_scale))

        if cat in (ThingCategory.PLAYER, ThingCategory.MONSTER):
            # Directional triangle (tip = facing direction)
            self._draw_direction_triangle((cx, cy), self._thing_facing(thing), colour, r * 2)

        elif cat == ThingCategory.KEY:
            # Diamond
            self.draw.polygon(
                [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                outline=colour,
            )

        elif cat in (ThingCategory.WEAPON, ThingCategory.POWERUP):
            # Outlined circle (larger)
            r2 = max(3, int(6 * self._scale * self._opts.thing_scale))
            self.draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=colour)

        elif cat in (ThingCategory.HEALTH, ThingCategory.ARMOR, ThingCategory.AMMO):
            # Small filled square
            self.draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill=colour)

        elif cat == ThingCategory.DECORATION:
            # Tiny dot
            rd = max(1, r // 2)
            self.draw.ellipse([cx - rd, cy - rd, cx + rd, cy + rd], fill=colour)

        else:
            # UNKNOWN — single pixel dot
            self.draw.point((cx, cy), fill=colour)

    def _draw_things(self) -> None:
        if not self.level.things:
            return
        for thing in self.level.things:
            self._draw_thing(thing)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self) -> Image.Image:
        """Draw all enabled layers and return the finished image."""
        if self._opts.show_floors:
            self._draw_floors()
        self._draw_linedefs()
        if self._opts.show_things:
            self._draw_things()
        return self.im

    def save(self, path: str) -> None:
        """Save the rendered image to *path*."""
        self.im.save(path)

    def show(self) -> None:
        """Open the rendered image in the system viewer."""
        self.im.show()
