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

from ..lumps.colormap import ColormapLump
from ..lumps.dehacked import DehackedThing
from ..lumps.map import BaseMapEntry
from ..lumps.playpal import Palette
from ..types import (
    GameType,
    ThingCategory,
    detect_game,
    get_category,
    get_invisible_types,
    get_sprite_prefix,
    get_sprite_suffixes,
)
from .floors import draw_floors

if TYPE_CHECKING:
    from ..wad import WadFile

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

    multiplayer: bool = False
    """Include multiplayer-only things (NOT_SINGLEPLAYER flag, types 2-4 player
    starts, deathmatch starts).  When False (default) those things are omitted,
    matching what a solo player sees in-game."""


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

        # Detect which game this WAD belongs to so the right type table is used
        self._game: GameType = detect_game(wad) if wad is not None else GameType.DOOM
        self._invisible_types: frozenset[int] = get_invisible_types(self._game)

        # Load custom thing type definitions from an embedded DEHACKED lump.
        # These extend (or redefine) the base game table for PWADs that add new
        # monsters, decorations, etc. via the DEHEXTRA "ID # = N" mechanism.
        self._deh_things: dict[int, DehackedThing] = (
            wad.dehacked.things if wad is not None and wad.dehacked is not None else {}
        )

        # Sprite image cache: 4-char prefix → scaled PIL image (or None = not found)
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
    # Floor rendering — delegates to floors module
    # ------------------------------------------------------------------

    def _draw_floors(self) -> None:
        draw_floors(self)

    # ------------------------------------------------------------------
    # Linedef rendering
    # ------------------------------------------------------------------

    # Doom automap colours (RGB).  Chosen to read clearly on both dark and
    # transparent backgrounds.
    _LINE_ONE_SIDED: tuple[int, int, int] = (220, 220, 220)  # solid wall — white
    _LINE_TWO_SIDED: tuple[int, int, int] = (110, 110, 110)  # passable — grey
    _LINE_FLOOR_CHANGE: tuple[int, int, int] = (220, 180, 80)  # step / ledge — yellow
    _LINE_CEIL_CHANGE: tuple[int, int, int] = (140, 140, 140)  # ceiling change — light grey
    _LINE_SECRET: tuple[int, int, int] = (220, 50, 220)  # secret — magenta
    _LINE_SPECIAL: tuple[int, int, int] = (80, 200, 255)  # door / trigger — cyan

    # Linedef flag bits (Doom / Boom)
    _FLAG_SECRET = 0x0020  # mapped as one-sided on automap

    def _linedef_colour(self, line: Any) -> tuple[int, int, int]:
        """Classify a linedef and return its automap colour."""
        m = self.level
        left_sd = getattr(line, "left_sidedef", -1)
        one_sided = left_sd in (-1, 0xFFFF)

        # Secret flag: draw as solid wall regardless of geometry
        if getattr(line, "flags", 0) & self._FLAG_SECRET:
            return self._LINE_SECRET

        if one_sided:
            # Check for special action (door, lift, trigger)
            if getattr(line, "special_type", 0):
                return self._LINE_SPECIAL
            return self._LINE_ONE_SIDED

        # Two-sided: compare front and back sector floor/ceiling heights
        if m.sidedefs and m.sectors:
            right_sd = getattr(line, "right_sidedef", 0)
            right_sec_idx = getattr(m.sidedefs.get(right_sd), "sector", None)
            left_sec_idx = getattr(m.sidedefs.get(left_sd), "sector", None)
            right_sec = m.sectors.get(right_sec_idx) if right_sec_idx is not None else None
            left_sec = m.sectors.get(left_sec_idx) if left_sec_idx is not None else None

            if right_sec and left_sec:
                if right_sec.floor_height != left_sec.floor_height:
                    return self._LINE_FLOOR_CHANGE
                if right_sec.ceiling_height != left_sec.ceiling_height:
                    return self._LINE_CEIL_CHANGE

        return self._LINE_TWO_SIDED

    def _iter_linedef_endpoints(
        self,
    ) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int, int]]]:
        """Return [(p1, p2, colour)] for all linedefs with valid vertices."""
        result: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int, int]]] = []
        m = self.level
        if not m.lines or not m.vertices:
            return result
        for line in m.lines:
            v1 = m.vertices.get(line.start_vertex)
            v2 = m.vertices.get(getattr(line, "finish_vertex", getattr(line, "end_vertex", -1)))
            if v1 is None or v2 is None:
                continue
            colour = self._linedef_colour(line)
            result.append((self._px(v1.x, v1.y), self._px(v2.x, v2.y), colour))
        return result

    def _draw_linedefs(self) -> None:
        lines = self._iter_linedef_endpoints()
        if self._opts.alpha:
            # Black outline pass on exterior (one-sided) walls.
            for p1, p2, colour in lines:
                if colour == self._LINE_ONE_SIDED:
                    self._draw.line([p1, p2], fill=(0, 0, 0, 255), width=5)
        for p1, p2, colour in lines:
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

        Uses ``get_sprite_suffixes`` to determine which frame suffixes to try
        (e.g. ``("A0", "A1")`` for idle sprites, ``("N0",)`` for dead poses).
        Result is cached by ``(prefix, suffixes)`` so types that share a prefix
        but need different frames get independent cache entries.
        """
        if self._wad is None or self._palette is None:
            return None
        deh = self._deh_things or None
        prefix = get_sprite_prefix(type_id, self._game, deh)
        if prefix is None:
            return None
        suffixes = get_sprite_suffixes(type_id, self._game, deh)
        cache_key = prefix + "|" + ",".join(suffixes)
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
        result: Image.Image | None = None
        for suffix in suffixes:
            lump_name = prefix + suffix
            sprite = self._wad.get_sprite(lump_name)
            if sprite is None:
                continue
            img = sprite.decode(self._palette)  # RGBA
            # Scale to map scale; minimum 8px so tiny sprites stay visible.
            w = max(8, int(img.width * self._scale))
            h = max(8, int(img.height * self._scale))
            result = img.resize((w, h), Image.Resampling.NEAREST)
            break
        self._sprite_cache[cache_key] = result
        return result

    def _draw_thing(self, thing: Any) -> None:
        if thing.type in self._invisible_types:
            return
        cat = get_category(thing.type, self._game, self._deh_things or None)
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

    _FLAG_NOT_SINGLEPLAYER = 0x0010
    # Player 2/3/4 starts are always present in the WAD but unused in singleplayer.
    # They carry no NOT_SINGLEPLAYER flag, so must be filtered by type.
    _COOP_PLAYER_STARTS = frozenset({2, 3, 4})

    def _draw_things(self) -> None:
        if not self.level.things:
            return
        for thing in self.level.things:
            if not self._opts.multiplayer:
                if getattr(thing, "flags", 0) & self._FLAG_NOT_SINGLEPLAYER:
                    continue
                if getattr(thing, "type", None) in self._COOP_PLAYER_STARTS:
                    continue
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
