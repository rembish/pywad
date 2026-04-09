"""wadcli list-patches — list PNAMES entries."""

import argparse

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("list-patches", help="list patch names from PNAMES")
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("--filter", metavar="NAME", help="only show patches containing NAME")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with WadFile(args.wad) as wad:
        if wad.pnames is None:
            print("No PNAMES lump found.")
            return
        names = wad.pnames.names
        if name_filter:
            names = [n for n in names if name_filter in n.upper()]
        if not names:
            print("No patches found.")
            return
        col_w = max(len(n) for n in names) + 2
        cols = max(1, 72 // col_w)
        for i, name in enumerate(names):
            end = "\n" if (i + 1) % cols == 0 else ""
            print(f"{name:<{col_w}}", end=end)
        if len(names) % cols != 0:
            print()
        print(f"\nTotal: {len(names)}")
