"""wadcli list textures — list TEXTURE1/TEXTURE2 entries."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--filter", metavar="NAME", help="only show textures containing NAME")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    name_filter = args.filter.upper() if args.filter else None
    with open_wad(args) as wad:
        rows = []
        for tlist, lump_name in ((wad.texture1, "TEXTURE1"), (wad.texture2, "TEXTURE2")):
            if tlist is None:
                continue
            for td in tlist.textures:
                if name_filter and name_filter not in td.name.upper():
                    continue
                rows.append(
                    {
                        "name": td.name,
                        "width": td.width,
                        "height": td.height,
                        "patches": len(td.patches),
                        "source": lump_name,
                    }
                )

        if args.json:
            print(json.dumps(rows, indent=2))
            return
        if not rows:
            print("No textures found.")
            return
        print(f"{'NAME':<12}  {'W':>6}  {'H':>6}  {'PATCHES':>8}  {'SOURCE':<10}")
        print("-" * 50)
        for row in rows:
            print(
                f"{row['name']:<12}  {row['width']:>6}  {row['height']:>6}"
                f"  {row['patches']:>8}  {row['source']:<10}"
            )
        print(f"\nTotal: {len(rows)}")
