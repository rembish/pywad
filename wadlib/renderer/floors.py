"""Floor / BSP rendering logic extracted from MapRenderer.

All public functions accept a renderer instance (``MapRenderer``) as their
first argument so that MapRenderer can delegate to them without circular
imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PIL import Image
from PIL.ImageDraw import ImageDraw

from .geometry import _clip_poly

if TYPE_CHECKING:
    from ..lumps.playpal import Palette
    from .core import MapRenderer


# ------------------------------------------------------------------
# Palette / tile helpers
# ------------------------------------------------------------------


def _shaded_palette(renderer: MapRenderer, light_level: int) -> Palette:
    """Return a palette remapped through the colormap for *light_level*."""
    assert renderer._palette is not None
    if renderer._colormap is None:
        return renderer._palette
    colormap_idx = max(0, min(31, (255 - light_level) // 8))
    cmap = renderer._colormap.get(colormap_idx)
    return [renderer._palette[cmap[i]] for i in range(256)]


def _build_flat_tile(renderer: MapRenderer, flat_name: str, light_level: int) -> Image.Image | None:
    """Decode and scale a flat for tiling, shaded by *light_level*."""
    if renderer._wad is None or renderer._palette is None:
        return None
    flat = renderer._wad.get_flat(flat_name)
    if flat is None:
        return None
    img = flat.decode(_shaded_palette(renderer, light_level))
    tile_px = max(1, int(64 * renderer._scale))
    return img.resize((tile_px, tile_px), Image.Resampling.NEAREST)


def _tile_canvas(renderer: MapRenderer, tile: Image.Image) -> Image.Image:
    """Produce a canvas-sized image tiled with *tile* (same mode as renderer image)."""
    mode = renderer._im.mode
    tiled = Image.new(mode, renderer._im.size)
    src = tile.convert(mode)
    tw, th = src.size
    for ty in range(0, renderer._im.height, th):
        for tx in range(0, renderer._im.width, tw):
            tiled.paste(src, (tx, ty))
    return tiled


# ------------------------------------------------------------------
# Sector lookup helpers
# ------------------------------------------------------------------


def _sector_for_seg(renderer: MapRenderer, seg: Any) -> int | None:
    """Return the sector index that a Seg faces, or None."""
    m = renderer.level
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


def _sector_from_ssector(renderer: MapRenderer, ssector: Any) -> int | None:
    """Return the sector index for a subsector (from any of its segs)."""
    m = renderer.level
    if not m.segs:
        return None
    for j in range(ssector.seg_count):
        seg = m.segs.get(ssector.first_seg + j)
        if seg is None:
            continue
        sector_idx = _sector_for_seg(renderer, seg)
        if sector_idx is not None:
            return sector_idx
    return None


# ------------------------------------------------------------------
# BSP polygon clipping / collection
# ------------------------------------------------------------------


def _clip_by_segs(
    renderer: MapRenderer,
    poly: list[tuple[float, float]],
    ssector: Any,
) -> list[tuple[float, float]]:
    """Clip *poly* against each seg's half-plane to remove bleeding outside walls.

    The subsector always lies to the RIGHT of each seg's start→end direction
    (cross >= 0), so we keep the right side of every seg's half-plane.
    """
    m = renderer.level
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


def _collect_all_ssector_polys(renderer: MapRenderer) -> dict[int, list[tuple[float, float]]]:
    """Walk the BSP tree ONCE and collect every subsector's clipped polygon.

    This is O(N) in the number of BSP nodes, vs the naive O(N log N) approach
    of doing a separate root-to-leaf walk for every subsector.
    """

    m = renderer.level
    if not m.nodes:
        return {}
    initial_poly: list[tuple[float, float]] = [
        (float(renderer._min_x), float(renderer._min_y)),
        (float(renderer._max_x), float(renderer._min_y)),
        (float(renderer._max_x), float(renderer._max_y)),
        (float(renderer._min_x), float(renderer._max_y)),
    ]
    result: dict[int, list[tuple[float, float]]] = {}
    root_idx = len(m.nodes) - 1
    _bsp_collect(renderer, root_idx, initial_poly, result)
    return result


def _bsp_collect(
    renderer: MapRenderer,
    child_idx: int,
    poly: list[tuple[float, float]],
    result: dict[int, list[tuple[float, float]]],
) -> None:
    """Recursive BSP traversal that accumulates polygons for all subsectors."""
    from ..lumps.nodes import SSECTOR_FLAG  # local to avoid heavy top-level import

    if child_idx & SSECTOR_FLAG:
        result[child_idx & ~SSECTOR_FLAG] = poly
        return
    m = renderer.level
    node = m.nodes.get(child_idx) if m.nodes else None
    if node is None:
        return
    nx, ny, ndx, ndy = float(node.x), float(node.y), float(node.dx), float(node.dy)
    right_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=True)
    left_poly = _clip_poly(poly, nx, ny, ndx, ndy, keep_right=False)
    if len(right_poly) >= 3:
        _bsp_collect(renderer, node.right_child, right_poly, result)
    if len(left_poly) >= 3:
        _bsp_collect(renderer, node.left_child, left_poly, result)


# ------------------------------------------------------------------
# Subsector fill + top-level floor draw
# ------------------------------------------------------------------


def _fill_ssector_polygon(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    renderer: MapRenderer,
    ssector_idx: int,  # pylint: disable=unused-argument
    ssector: Any,
    poly: list[tuple[float, float]],
    tile_cache: dict[tuple[str, int], Image.Image | None],
    tiled_canvas_cache: dict[tuple[str, int], Image.Image],
) -> None:
    """Render the floor flat for one subsector using a pre-computed BSP polygon."""
    m = renderer.level
    sector_idx = _sector_from_ssector(renderer, ssector)
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
        tile_cache[key] = _build_flat_tile(renderer, flat_name, light_level)
    tile = tile_cache[key]
    if tile is None:
        return
    if key not in tiled_canvas_cache:
        tiled_canvas_cache[key] = _tile_canvas(renderer, tile)
    tiled = tiled_canvas_cache[key]
    refined = _clip_by_segs(renderer, poly, ssector)
    if len(refined) < 3:
        return
    points = [renderer._px(int(x), int(y)) for x, y in refined]
    mask = Image.new("L", renderer._im.size, 0)
    ImageDraw(mask).polygon(points, fill=255, outline=255)
    renderer._im.paste(tiled, (0, 0), mask=mask)


def draw_floors(renderer: MapRenderer) -> None:
    """Draw floor textures for all subsectors via BSP traversal."""
    m = renderer.level
    if not (m.ssectors and m.segs and m.vertices and m.sectors):
        return
    if renderer._wad is None or renderer._palette is None:
        return
    # Single O(N) BSP traversal collects every subsector polygon at once.
    all_polys = _collect_all_ssector_polys(renderer)
    tile_cache: dict[tuple[str, int], Image.Image | None] = {}
    tiled_canvas_cache: dict[tuple[str, int], Image.Image] = {}
    for i, ssector in enumerate(m.ssectors):
        poly = all_polys.get(i)
        if poly is None or len(poly) < 3:
            continue
        _fill_ssector_polygon(renderer, i, ssector, poly, tile_cache, tiled_canvas_cache)
