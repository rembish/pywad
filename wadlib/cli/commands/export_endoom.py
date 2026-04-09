"""wadcli export endoom — export the ENDOOM lump as plain text or ANSI."""

import argparse
import sys

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("output", help="output file path")
    p.add_argument(
        "--ansi",
        action="store_true",
        help="include ANSI color codes in output",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        endoom = wad.endoom
        if endoom is None:
            print("No ENDOOM lump found.", file=sys.stderr)
            sys.exit(1)

        text = endoom.to_ansi() if args.ansi else endoom.to_text()
        data = text.encode("utf-8", errors="replace")
        with open(args.output, "wb") as f:
            f.write(data)

        print(f"Saved {len(data)} bytes to {args.output}")
