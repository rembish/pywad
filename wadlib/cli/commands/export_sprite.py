"""wadcli export sprite — render a sprite (or all sprites) to PNG."""

import argparse
import sys
from pathlib import Path

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "name",
        nargs="?",
        default=None,
        help="sprite lump name, e.g. PLAYA1 (omit with --all)",
    )
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (single) or directory (--all); default: <NAME>.png or ./",
    )
    p.add_argument("--all", action="store_true", help="export every sprite in the WAD")
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if wad.playpal is None:
            print("WAD has no PLAYPAL lump.", file=sys.stderr)
            sys.exit(1)
        palette = wad.playpal.get_palette(args.palette)

        if args.all:
            out_dir = Path(args.output or args.name or ".")
            if args.output is None and args.name is not None and not Path(args.name).is_dir():
                out_dir = Path(args.name)
            out_dir.mkdir(parents=True, exist_ok=True)
            sprites = wad.sprites
            if not sprites:
                print("No sprites found in WAD.", file=sys.stderr)
                sys.exit(1)
            for name, pic in sprites.items():
                img = pic.decode(palette)
                img.save(str(out_dir / f"{name}.png"))
            print(f"Exported {len(sprites)} sprite(s) to {out_dir}/")
            return

        if args.name is None:
            print("Specify a sprite name or use --all.", file=sys.stderr)
            sys.exit(1)

        lump_name = args.name.upper()
        output: str = args.output or f"{lump_name}.png"
        maybe_pic = wad.get_sprite(lump_name)
        if maybe_pic is None:
            print(f"Sprite '{lump_name}' not found.", file=sys.stderr)
            sys.exit(1)
        img = maybe_pic.decode(palette)
        img.save(output)
        w, h = img.size
        print(f"Saved {w}x{h} RGBA image to {output}")
