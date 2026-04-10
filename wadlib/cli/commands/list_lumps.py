"""wadcli list lumps — print full WAD directory."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--filter", metavar="NAME", help="only show lumps whose name contains NAME")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with open_wad(args) as wad:
        entries = [e for e in wad.directory if not name_filter or name_filter in e.name.upper()]
        if args.json:
            print(
                json.dumps(
                    [
                        {"index": i, "name": e.name, "size": e.size, "offset": e.offset}
                        for i, e in enumerate(entries)
                    ],
                    indent=2,
                )
            )
            return
        print(f"{'#':>6}  {'NAME':<10}  {'SIZE':>10}  {'OFFSET':>10}")
        print("-" * 44)
        for i, entry in enumerate(entries):
            print(f"{i:>6}  {entry.name:<10}  {entry.size:>10}  {entry.offset:>10}")
