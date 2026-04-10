"""wadcli export colormap — render COLORMAP lump as a PNG colour grid."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (default: COLORMAP.png)",
    )
    p.add_argument(
        "--palette",
        type=int,
        default=0,
        metavar="N",
        help="PLAYPAL palette index to use for rendering (default: 0)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    output: str = args.output or "COLORMAP.png"
    with open_wad(args) as wad:
        if wad.colormap is None:
            print("No COLORMAP lump found.", file=sys.stderr)
            sys.exit(1)
        if wad.playpal is None:
            print("No PLAYPAL lump found.", file=sys.stderr)
            sys.exit(1)

        palette = wad.playpal.get_palette(args.palette)
        cm = wad.colormap
        cell = 4
        w_px = 256 * cell
        h_px = cm.count * cell

        from PIL import Image

        img = Image.new("RGB", (w_px, h_px))
        pixels = img.load()
        assert pixels is not None
        for row in range(cm.count):
            colormap = cm.get(row)
            for col in range(256):
                r, g, b = palette[colormap[col]]
                for dy in range(cell):
                    for dx in range(cell):
                        pixels[col * cell + dx, row * cell + dy] = (r, g, b)

        img.save(output)
        print(f"Saved {w_px}x{h_px} colormap grid to {output}")
