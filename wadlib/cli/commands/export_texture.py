"""wadcli export texture — render a composite wall texture to PNG."""

import argparse
import sys

from ...compositor import TextureCompositor
from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("texture", help="texture name, e.g. STARTAN3")
    p.add_argument("output", help="output PNG path")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        palette = None
        if wad.playpal is not None:
            palette = wad.playpal.get_palette(args.palette)
        comp = TextureCompositor(wad, palette=palette)
        img = comp.compose(args.texture.upper())
        if img is None:
            print(f"Texture '{args.texture}' not found.", file=sys.stderr)
            sys.exit(1)
        img.save(args.output)
        w, h = img.size
        print(f"Saved {w}x{h} image to {args.output}")
