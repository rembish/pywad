"""wadcli export endoom — export the ENDOOM lump as plain text or ANSI."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output file path (default: ENDOOM.ans with --ansi, ENDOOM.txt otherwise)",
    )
    p.add_argument(
        "--ansi",
        action="store_true",
        help="include ANSI color codes in output",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    default_ext = ".ans" if args.ansi else ".txt"
    output: str = args.output or f"ENDOOM{default_ext}"
    with open_wad(args) as wad:
        endoom = wad.endoom
        if endoom is None:
            print("No ENDOOM lump found.", file=sys.stderr)
            sys.exit(1)

        text = endoom.to_ansi() if args.ansi else endoom.to_text()
        data = text.encode("utf-8", errors="replace")
        with open(output, "wb") as f:
            f.write(data)

        print(f"Saved {len(data)} bytes to {output}")
