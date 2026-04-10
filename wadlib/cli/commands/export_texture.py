"""wadcli export texture — render a composite wall texture to PNG."""

import argparse
import sys

from ...compositor import TextureCompositor
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("texture", help="texture name, e.g. STARTAN3")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (default: <TEXTURE>.png)",
    )
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    tex_name = args.texture.upper()
    output: str = args.output or f"{tex_name}.png"
    with open_wad(args) as wad:
        palette = None
        if wad.playpal is not None:
            palette = wad.playpal.get_palette(args.palette)
        comp = TextureCompositor(wad, palette=palette)
        img = comp.compose(tex_name)
        if img is None:
            print(f"Texture '{tex_name}' not found.", file=sys.stderr)
            sys.exit(1)
        img.save(output)
        w, h = img.size
        print(f"Saved {w}x{h} image to {output}")
