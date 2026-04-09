"""wadcli list-maps — print maps with thing and linedef counts."""

import argparse

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("list-maps", help="list maps with thing/linedef counts")
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if not wad.maps:
            print("No maps found.")
            return
        print(f"{'MAP':<10}  {'THINGS':>8}  {'LINEDEFS':>10}  {'VERTICES':>10}  {'SECTORS':>8}")
        print("-" * 54)
        for m in wad.maps:
            things = len(m.things) if m.things else 0
            lines = len(m.lines) if m.lines else 0
            verts = len(m.vertices) if m.vertices else 0
            sectors = len(m.sectors) if m.sectors else 0
            print(f"{m!s:<10}  {things:>8}  {lines:>10}  {verts:>10}  {sectors:>8}")
