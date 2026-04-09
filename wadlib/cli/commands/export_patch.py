"""wadcli export patch — render a patch/sprite graphic to PNG."""

import argparse
import sys

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.add_argument("patch", help="patch name, e.g. WALL01_1")
    p.add_argument("output", help="output PNG path")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        pic = wad.get_picture(args.patch.upper())
        if pic is None:
            print(f"Patch '{args.patch}' not found.", file=sys.stderr)
            sys.exit(1)
        if wad.playpal is None:
            print("WAD has no PLAYPAL lump.", file=sys.stderr)
            sys.exit(1)
        palette = wad.playpal.get_palette(args.palette)
        img = pic.decode(palette)
        img.save(args.output)
        w, h = img.size
        print(f"Saved {w}x{h} RGBA image to {args.output}")
