#!/usr/bin/env python3
"""
10_render_maps.py — Render map overhead views as PNG images.

Uses MapRenderer to produce floor-textured overhead images. Renders MAP01
and MAP02 by default (pass --all to render the full WAD).

Usage:
    python examples/10_render_maps.py
    python examples/10_render_maps.py wads/freedoom2.wad output/maps/
    python examples/10_render_maps.py wads/freedoom2.wad output/maps/ --map MAP01
    python examples/10_render_maps.py wads/freedoom2.wad output/maps/ --all
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wadlib import WadFile
from wadlib.renderer import MapRenderer, RenderOptions

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"
DEFAULT_OUT = Path(__file__).parent / "output" / "maps"


def render_map(wad: WadFile, map_name: str, out_dir: Path, show_sprites: bool) -> None:
    target = next((m for m in wad.maps if str(m) == map_name.upper()), None)
    if target is None:
        print(f"  {map_name}: not found")
        return

    opts = RenderOptions(
        show_floors=True,   # fill sectors with floor texture colours
        alpha=True,         # transparent void (void = fully transparent)
        show_sprites=False, # True needs wad= passed to renderer
    )

    try:
        renderer = MapRenderer(target, wad=wad, options=opts)
        renderer.render()
        path = out_dir / f"{map_name.upper()}.png"
        renderer.save(str(path))
        print(f"  {map_name}: → {path}")
    except Exception as exc:
        print(f"  {map_name}: render failed — {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render WAD maps to PNG")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUT))
    parser.add_argument("--pwad", metavar="PATH", help="Optional PWAD to layer")
    parser.add_argument("--map", metavar="NAME", help="Render only this map (e.g. MAP01)")
    parser.add_argument("--all", action="store_true", dest="render_all",
                        help="Render every map in the WAD (default: MAP01 + MAP02)")
    parser.add_argument("--sprites", action="store_true",
                        help="Render actual sprites at thing positions")
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    extra = [args.pwad] if args.pwad else []
    with WadFile.open(args.wad, *extra) as wad:
        if args.map:
            maps = [m for m in wad.maps if str(m) == args.map.upper()]
            if not maps:
                print(f"Map {args.map!r} not found in {args.wad}")
                return
        elif args.render_all:
            maps = wad.maps
        else:
            # Default: first two maps only
            maps = wad.maps[:2]

        print(f"Rendering {len(maps)} map(s) from {args.wad}:")
        for m in maps:
            render_map(wad, str(m), out, args.sprites)


if __name__ == "__main__":
    main()
