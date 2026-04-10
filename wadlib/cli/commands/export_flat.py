"""wadcli export flat — render a floor/ceiling flat to PNG."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("flat", help="flat name, e.g. FLOOR0_1")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (default: <FLAT>.png)",
    )
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
    flat_name = args.flat.upper()
    output: str = args.output or f"{flat_name}.png"
    with open_wad(args) as wad:
        flat = wad.get_flat(flat_name)
        if flat is None:
            print(f"Flat '{flat_name}' not found.", file=sys.stderr)
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
        img.save(output)
        w, h = img.size
        print(f"Saved {w}x{h} image to {output}")
