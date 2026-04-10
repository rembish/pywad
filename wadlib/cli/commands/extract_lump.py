"""wadcli export lump — dump raw lump bytes to a file."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("lump", help="lump name, e.g. PLAYPAL")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output file path (default: <LUMP>.bin)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    lump_name = args.lump.upper()
    output: str = args.output or f"{lump_name}.bin"
    with open_wad(args) as wad:
        lump = wad.get_lump(lump_name)
        if lump is None:
            print(f"Lump '{lump_name}' not found.", file=sys.stderr)
            sys.exit(1)
        data = lump.raw()
        with open(output, "wb") as fh:
            fh.write(data)
        print(f"Wrote {len(data)} bytes to {output}")
