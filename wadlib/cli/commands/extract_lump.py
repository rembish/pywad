"""wadcli extract-lump — dump raw lump bytes to a file."""

import argparse
import sys

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("extract-lump", help="extract raw lump bytes to a file")
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("lump", help="lump name, e.g. PLAYPAL")
    p.add_argument("output", help="output file path")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        lump = wad.get_lump(args.lump.upper())
        if lump is None:
            print(f"Lump '{args.lump}' not found.", file=sys.stderr)
            sys.exit(1)
        data = lump.raw()
        with open(args.output, "wb") as fh:
            fh.write(data)
        print(f"Wrote {len(data)} bytes to {args.output}")
