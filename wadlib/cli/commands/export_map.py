"""wadcli export map — render a map to a PNG image."""

import argparse
import sys

from ...renderer import MapRenderer, RenderOptions
from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("map", help="map name, e.g. E1M1 or MAP01")
    p.add_argument("output", help="output PNG path")
    p.add_argument(
        "--scale", type=float, default=0.0, help="pixels per map unit (default: auto-fit)"
    )
    p.add_argument("--no-things", action="store_true", help="omit thing markers")
    p.add_argument("--floors", action="store_true", help="fill sectors with floor flat textures")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.add_argument(
        "--thing-scale",
        type=float,
        default=1.0,
        metavar="F",
        help="multiplier for thing marker size (default: 1.0)",
    )
    p.add_argument(
        "--alpha",
        action="store_true",
        help="RGBA output with transparent void areas and black exterior outline",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    map_name = args.map.upper()
    opts = RenderOptions(
        scale=args.scale,
        show_things=not args.no_things,
        show_floors=args.floors,
        palette_index=args.palette,
        thing_scale=args.thing_scale,
        alpha=args.alpha,
    )
    with WadFile(args.wad) as wad:
        target = next((m for m in wad.maps if str(m) == map_name), None)
        if target is None:
            available = ", ".join(str(m) for m in wad.maps)
            print(f"Map '{map_name}' not found. Available: {available}", file=sys.stderr)
            sys.exit(1)

        renderer = MapRenderer(target, wad=wad, options=opts)
        renderer.render()
        renderer.save(args.output)
        w, h = renderer.im.size
        print(f"Saved {w}x{h} image to {args.output}")
