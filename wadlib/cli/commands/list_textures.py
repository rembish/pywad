"""wadcli list-textures — list TEXTURE1/TEXTURE2 entries."""

import argparse

from ...wad import WadFile


def register(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser("list-textures", help="list composite texture names and dimensions")
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("--filter", metavar="NAME", help="only show textures containing NAME")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with WadFile(args.wad) as wad:
        rows = []
        for tlist, lump_name in ((wad.texture1, "TEXTURE1"), (wad.texture2, "TEXTURE2")):
            if tlist is None:
                continue
            for td in tlist.textures:
                if name_filter and name_filter not in td.name.upper():
                    continue
                rows.append((td.name, td.width, td.height, len(td.patches), lump_name))

        if not rows:
            print("No textures found.")
            return

        print(f"{'NAME':<12}  {'W':>6}  {'H':>6}  {'PATCHES':>8}  {'SOURCE':<10}")
        print("-" * 50)
        for name, w, h, patches, src in rows:
            print(f"{name:<12}  {w:>6}  {h:>6}  {patches:>8}  {src:<10}")
        print(f"\nTotal: {len(rows)}")
