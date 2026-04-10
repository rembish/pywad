"""wadcli export map — render a map (or all maps) to PNG images."""

import argparse
import sys
from pathlib import Path

from ...lumps.map import BaseMapEntry
from ...renderer import MapRenderer, RenderOptions
from ...wad import WadFile
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "map",
        nargs="?",
        default=None,
        help="map name, e.g. E1M1 or MAP01 (omit with --all)",
    )
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (single map) or directory (--all); default: <MAP>.png or ./",
    )
    p.add_argument("--all", action="store_true", help="export every map in the WAD")
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
    p.add_argument(
        "--sprites",
        action="store_true",
        help="draw WAD sprites at thing positions instead of category shapes",
    )
    p.add_argument(
        "--multiplayer",
        action="store_true",
        help="include multiplayer-only things (NOT_SINGLEPLAYER flag, extra player starts)",
    )
    p.set_defaults(func=run)


def _render_one(target: object, wad: object, opts: RenderOptions, output: str) -> None:
    assert isinstance(target, BaseMapEntry)
    assert isinstance(wad, WadFile)
    renderer = MapRenderer(target, wad=wad, options=opts)
    renderer.render()
    renderer.save(output)
    w, h = renderer.image.size
    print(f"Saved {w}x{h} → {output}")


def run(args: argparse.Namespace) -> None:  # pylint: disable=too-many-branches
    opts = RenderOptions(
        scale=args.scale,
        show_things=not args.no_things,
        show_floors=args.floors,
        palette_index=args.palette,
        thing_scale=args.thing_scale,
        alpha=args.alpha,
        show_sprites=args.sprites,
        multiplayer=args.multiplayer,
    )

    if args.all:
        out_dir = Path(args.output or args.map or ".")
        if args.output is None and args.map is not None and not Path(args.map).is_dir():
            # positional arg was meant as the output dir when --all is used
            out_dir = Path(args.map)
        out_dir.mkdir(parents=True, exist_ok=True)
        with open_wad(args) as wad:
            maps = wad.maps
            if not maps:
                print("No maps found in WAD.", file=sys.stderr)
                sys.exit(1)
            for m in maps:
                dest = str(out_dir / f"{m}.png")
                _render_one(m, wad, opts, dest)
        print(f"Exported {len(maps)} map(s) to {out_dir}/")
        return

    # Single-map mode
    if args.map is None:
        print("Specify a map name or use --all.", file=sys.stderr)
        sys.exit(1)

    map_name = args.map.upper()
    output: str = args.output or f"{map_name}.png"

    with open_wad(args) as wad:
        target = next((m for m in wad.maps if str(m) == map_name), None)
        if target is None:
            available = ", ".join(str(m) for m in wad.maps)
            print(f"Map '{map_name}' not found. Available: {available}", file=sys.stderr)
            sys.exit(1)
        _render_one(target, wad, opts, output)
