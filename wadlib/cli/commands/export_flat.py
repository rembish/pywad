"""wadcli export-flat — render a floor/ceiling flat to PNG."""

import argparse
import sys

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("export-flat", help="render a floor/ceiling flat to PNG")
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("flat", help="flat name, e.g. FLOOR0_1")
    p.add_argument("output", help="output PNG path")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.add_argument(
        "--scale",
        type=int,
        default=1,
        metavar="N",
        help="integer upscale factor (default: 1 = 64x64)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        flat = wad.get_flat(args.flat.upper())
        if flat is None:
            print(f"Flat '{args.flat}' not found.", file=sys.stderr)
            sys.exit(1)
        if wad.playpal is None:
            print("WAD has no PLAYPAL lump.", file=sys.stderr)
            sys.exit(1)
        palette = wad.playpal.get_palette(args.palette)
        img = flat.decode(palette)
        if args.scale > 1:
            img = img.resize(
                (img.width * args.scale, img.height * args.scale),
                resample=0,  # NEAREST
            )
        img.save(args.output)
        w, h = img.size
        print(f"Saved {w}x{h} image to {args.output}")
