"""wadcli scan textures — report texture and flat usage across maps."""

import argparse
import json

from ...scanner import find_unused_flats, find_unused_textures, scan_usage
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.add_argument("--unused", action="store_true", help="show only unused textures/flats")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if args.unused:
            unused_tex = sorted(find_unused_textures(wad))
            unused_flat = sorted(find_unused_flats(wad))

            if args.json:
                print(
                    json.dumps(
                        {"unused_textures": unused_tex, "unused_flats": unused_flat}, indent=2
                    )
                )
                return

            if unused_tex:
                print(f"Unused textures ({len(unused_tex)}):")
                for t in unused_tex:
                    print(f"  {t}")
            else:
                print("No unused textures.")
            print()
            if unused_flat:
                print(f"Unused flats ({len(unused_flat)}):")
                for f in unused_flat:
                    print(f"  {f}")
            else:
                print("No unused flats.")
            return

        usage = scan_usage(wad)

        if args.json:
            print(
                json.dumps(
                    {
                        "total_textures": usage.total_unique_textures,
                        "total_flats": usage.total_unique_flats,
                        "total_thing_types": usage.total_unique_thing_types,
                        "maps": {
                            name: {
                                "textures": len(mu.textures),
                                "flats": len(mu.flats),
                                "things": mu.thing_count,
                                "linedefs": mu.linedef_count,
                                "sectors": mu.sector_count,
                            }
                            for name, mu in usage.per_map.items()
                        },
                    },
                    indent=2,
                )
            )
            return

        print(f"Textures used : {usage.total_unique_textures}")
        print(f"Flats used    : {usage.total_unique_flats}")
        print(f"Thing types   : {usage.total_unique_thing_types}")
        print(f"Maps scanned  : {len(usage.per_map)}")
        print()
        print(f"{'Map':<10} {'Textures':<10} {'Flats':<8} {'Things':<8} {'Lines':<8} {'Sectors'}")
        print("-" * 54)
        for name, mu in sorted(usage.per_map.items()):
            print(
                f"{name:<10} {len(mu.textures):<10} {len(mu.flats):<8} "
                f"{mu.thing_count:<8} {mu.linedef_count:<8} {mu.sector_count}"
            )
