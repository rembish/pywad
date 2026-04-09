"""wadcli list-lumps — print full WAD directory."""

import argparse

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("list-lumps", help="list all directory entries")
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("--filter", metavar="NAME", help="only show lumps whose name contains NAME")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with WadFile(args.wad) as wad:
        print(f"{'#':>6}  {'NAME':<10}  {'SIZE':>10}  {'OFFSET':>10}")
        print("-" * 44)
        for i, entry in enumerate(wad.directory):
            if name_filter and name_filter not in entry.name.upper():
                continue
            print(f"{i:>6}  {entry.name:<10}  {entry.size:>10}  {entry.offset:>10}")
