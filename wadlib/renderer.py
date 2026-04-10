"""MapRenderer — produces a PIL Image from a parsed map entry.

Key features:
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

from .doom_types import ThingCategory, get_category, get_sprite_prefix
from .lumps.colormap import ColormapLump
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

    show_sprites: bool = False
    """Draw thing sprites from the WAD instead of (or on top of) category shapes.
    Falls back to the category shape if the sprite is not found.
    Requires a WadFile with PLAYPAL to be passed to MapRenderer."""


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
            self._im = Image.new("RGBA", (img_w, img_h), color=(0, 0, 0, 0))
        else:
            self._im = Image.new("RGB", (img_w, img_h), color=(20, 20, 20))
        self._draw = ImageDraw(self._im)

        # Resolve palette and colormap once
        self._palette: Palette | None = None
        self._colormap: ColormapLump | None = None
        if wad is not None and wad.playpal is not None:
            self._palette = wad.playpal.get_palette(self._opts.palette_index)
        if wad is not None:
            self._colormap = wad.colormap

        # Sprite image cache: lump name → scaled PIL image (or None = not found)
        self._sprite_cache: dict[str, Image.Image | None] = {}

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

    def _shaded_palette(self, light_level: int) -> Palette:
        """Return a palette remapped through the colormap for *light_level*."""
        assert self._palette is not None
        if self._colormap is None:
            return self._palette
        colormap_idx = max(0, min(31, (255 - light_level) // 8))
        cmap = self._colormap.get(colormap_idx)
        return [self._palette[cmap[i]] for i in range(256)]

    def _build_flat_tile(self, flat_name: str, light_level: int) -> Image.Image | None:
        """Decode and scale a flat for tiling, shaded by *light_level*."""
        if self._wad is None or self._palette is None:
            return None
        flat = self._wad.get_flat(flat_name)
        if flat is None:
            return None
        img = flat.decode(self._shaded_palette(light_level))
        tile_px = max(1, int(64 * self._scale))
        return img.resize((tile_px, tile_px), Image.Resampling.NEAREST)

    def _tile_canvas(self, tile: Image.Image) -> Image.Image:
        """Produce a canvas-sized image tiled with *tile* (same mode as self._im)."""
        mode = self._im.mode
        tiled = Image.new(mode, self._im.size)
        src = tile.convert(mode)
        tw, th = src.size
        for ty in range(0, self._im.height, th):
            for tx in range(0, self._im.width, tw):
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

    def _clip_by_segs(
        self, poly: list[tuple[float, float]], ssector: Any
    ) -> list[tuple[float, float]]:
        """Clip *poly* against each seg's half-plane to remove bleeding outside walls.

        The subsector always lies to the RIGHT of each seg's start→end direction
        (cross >= 0), so we keep the right side of every seg's half-plane.
        """
        m = self.level
        if not (m.segs and m.vertices):
            return poly
        for j in range(ssector.seg_count):
            seg = m.segs.get(ssector.first_seg + j)
            if seg is None:
                continue
            if getattr(seg, "linedef", None) == 0xFFFF:
                continue  # mini-seg: no real wall, skip clipping
            v1 = m.vertices.get(seg.start_vertex)
            v2 = m.vertices.get(seg.end_vertex)
            if v1 is None or v2 is None:
                continue
            dx, dy = float(v2.x - v1.x), float(v2.y - v1.y)
            if dx == 0.0 and dy == 0.0:
                continue
            poly = _clip_poly(poly, float(v1.x), float(v1.y), dx, dy, keep_right=True)
            if len(poly) < 3:
                return []
        return poly

    def _collect_all_ssector_polys(self) -> dict[int, list[tuple[float, float]]]:
        """Walk the BSP tree ONCE and collect every subsector's clipped polygon.

        This is O(N) in the number of BSP nodes, vs the naive O(N log N) approach
        of doing a separate root-to-leaf walk for every subsector.
        """
        m = self.level
        if not m.nodes:
            return {}
        initial_poly: list[tuple[float, float]] = [
            (float(self._min_x), float(self._min_y)),
            (float(self._max_x), float(self._min_y)),
            (float(self._max_x), float(self._max_y)),
            (float(self._min_x), float(self._max_y)),
        ]
        result: dict[int, list[tuple[float, float]]] = {}
        root_idx = len(m.nodes) - 1
        self._bsp_collect(root_idx, initial_poly, result)
        return result

    def _bsp_collect(
        self,
        child_idx: int,
        poly: list[tuple[float, float]],
        result: dict[int, list[tuple[float, float]]],
    ) -> None:
        """Recursive BSP traversal that accumulates polygons for all subsectors."""
        if child_idx & SSECTOR_FLAG:
            result[child_idx & ~SSECTOR_FLAG] = poly
            return
        m = self.level
        node = m.nodes.get(child_idx) if m.nodes else None
        if node is None:
            return
        nx, ny, ndx, ndy = float(node.x), float(node.y), float(node.dx), float(node.dy)
        right_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=True)
        left_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=False)
        if len(right_poly) >= 3:
            self._bsp_collect(node.right_child, right_poly, result)
        if len(left_poly) >= 3:
            self._bsp_collect(node.left_child, left_poly, result)

    def _fill_ssector_polygon(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        ssector_idx: int,  # pylint: disable=unused-argument
        ssector: Any,
        poly: list[tuple[float, float]],
        tile_cache: dict[tuple[str, int], Image.Image | None],
        tiled_canvas_cache: dict[tuple[str, int], Image.Image],
    ) -> None:
        """Render the floor flat for one subsector using a pre-computed BSP polygon."""
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
        light_level = getattr(sector, "light_level", 255)
        key = (flat_name, light_level)
        if key not in tile_cache:
            tile_cache[key] = self._build_flat_tile(flat_name, light_level)
        tile = tile_cache[key]
        if tile is None:
            return
        if key not in tiled_canvas_cache:
            tiled_canvas_cache[key] = self._tile_canvas(tile)
        tiled = tiled_canvas_cache[key]
        refined = self._clip_by_segs(poly, ssector)
        if len(refined) < 3:
            return
        points = [self._px(int(x), int(y)) for x, y in refined]
        mask = Image.new("L", self._im.size, 0)
        ImageDraw(mask).polygon(points, fill=255, outline=255)
        self._im.paste(tiled, (0, 0), mask=mask)

    def _draw_floors(self) -> None:
        m = self.level
        if not (m.ssectors and m.segs and m.vertices and m.sectors):
            return
        if self._wad is None or self._palette is None:
            return
        # Single O(N) BSP traversal collects every subsector polygon at once.
        all_polys = self._collect_all_ssector_polys()
        tile_cache: dict[tuple[str, int], Image.Image | None] = {}
        tiled_canvas_cache: dict[tuple[str, int], Image.Image] = {}
        for i, ssector in enumerate(m.ssectors):
            poly = all_polys.get(i)
            if poly is None or len(poly) < 3:
                continue
            self._fill_ssector_polygon(i, ssector, poly, tile_cache, tiled_canvas_cache)

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
                    self._draw.line([p1, p2], fill=(0, 0, 0, 255), width=5)
        for p1, p2, one_sided in lines:
            colour = (220, 220, 220) if one_sided else (110, 110, 110)
            self._draw.line([p1, p2], fill=colour, width=1)

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
        self._draw.polygon([tip, b1, b2], fill=colour)

    def _get_sprite_image(self, type_id: int) -> Image.Image | None:
        """Return a scaled sprite image for *type_id*, or None if unavailable.

        Tries lump ``{prefix}A0`` first (rotation-free), then ``{prefix}A1``
        (front-facing 8-way sprite).  Result is cached by lump name so each
        unique sprite is decoded and scaled at most once per render.
        """
        if self._wad is None or self._palette is None:
            return None
        prefix = get_sprite_prefix(type_id)
        if prefix is None:
            return None
        for suffix in ("A0", "A1"):
            lump_name = prefix + suffix
            if lump_name in self._sprite_cache:
                return self._sprite_cache[lump_name]
            sprite = self._wad.get_sprite(lump_name)
            if sprite is None:
                self._sprite_cache[lump_name] = None
                continue
            img = sprite.decode(self._palette)  # RGBA
            # Scale to map scale; minimum 8px so tiny sprites stay visible.
            w = max(8, int(img.width * self._scale))
            h = max(8, int(img.height * self._scale))
            scaled = img.resize((w, h), Image.Resampling.NEAREST)
            self._sprite_cache[lump_name] = scaled
            return scaled
        return None

    def _draw_thing(self, thing: Any) -> None:
        cat = get_category(thing.type)
        colour = _CATEGORY_COLOUR[cat]
        cx, cy = self._px(thing.x, thing.y)
        r = max(2, int(5 * self._scale * self._opts.thing_scale))

        if self._opts.show_sprites:
            sprite_img = self._get_sprite_image(thing.type)
            if sprite_img is not None:
                sw, sh = sprite_img.size
                self._im.paste(sprite_img, (cx - sw // 2, cy - sh // 2), mask=sprite_img)
                return

        if cat in (ThingCategory.PLAYER, ThingCategory.MONSTER):
            # Directional triangle (tip = facing direction)
            self._draw_direction_triangle((cx, cy), self._thing_facing(thing), colour, r * 2)

        elif cat == ThingCategory.KEY:
            # Diamond
            self._draw.polygon(
                [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
                outline=colour,
            )

        elif cat in (ThingCategory.WEAPON, ThingCategory.POWERUP):
            # Outlined circle (larger)
            r2 = max(3, int(6 * self._scale * self._opts.thing_scale))
            self._draw.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], outline=colour)

        elif cat in (ThingCategory.HEALTH, ThingCategory.ARMOR, ThingCategory.AMMO):
            # Small filled square
            self._draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill=colour)

        elif cat == ThingCategory.DECORATION:
            # Tiny dot
            rd = max(1, r // 2)
            self._draw.ellipse([cx - rd, cy - rd, cx + rd, cy + rd], fill=colour)

        else:
            # UNKNOWN — single pixel dot
            self._draw.point((cx, cy), fill=colour)

    def _draw_things(self) -> None:
        if not self.level.things:
            return
        for thing in self.level.things:
            self._draw_thing(thing)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def image(self) -> Image.Image:
        """The current canvas image."""
        return self._im

    def render(self) -> Image.Image:
        """Draw all enabled layers and return the finished image."""
        if self._opts.show_floors:
            self._draw_floors()
        self._draw_linedefs()
        if self._opts.show_things:
            self._draw_things()
        return self._im

    def save(self, path: str) -> None:
        """Save the rendered image to *path*."""
        self._im.save(path)

    def show(self) -> None:
        """Open the rendered image in the system viewer."""
        self._im.show()
