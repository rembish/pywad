"""wadcli export sprite — render a sprite to PNG."""

import argparse
import sys

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.add_argument("name", help="sprite lump name, e.g. PLAYA1")
    p.add_argument("output", help="output PNG path")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    lump_name = args.name.upper()
    with open_wad(args) as wad:
        pic = wad.get_sprite(lump_name)
        if pic is None:
            print(f"Sprite '{lump_name}' not found.", file=sys.stderr)
            sys.exit(1)
        if wad.playpal is None:
            print("WAD has no PLAYPAL lump.", file=sys.stderr)
            sys.exit(1)
        palette = wad.playpal.get_palette(args.palette)
        img = pic.decode(palette)
        img.save(args.output)
        w, h = img.size
        print(f"Saved {w}x{h} RGBA image to {args.output}")
