"""wadcli list flats — list F_START/F_END namespace entries."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--filter", metavar="NAME", help="only show flats containing NAME")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with open_wad(args) as wad:
        names = sorted(wad.flats.keys())
        if name_filter:
            names = [n for n in names if name_filter in n]
        if args.json:
            print(json.dumps(names))
            return
        if not names:
            print("No flats found.")
            return
        col_w = max(len(n) for n in names) + 2
        cols = max(1, 72 // col_w)
        for i, name in enumerate(names):
            end = "\n" if (i + 1) % cols == 0 else ""
            print(f"{name:<{col_w}}", end=end)
        if len(names) % cols != 0:
            print()
        print(f"\nTotal: {len(names)}")
