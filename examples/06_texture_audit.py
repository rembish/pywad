#!/usr/bin/env python3
"""
06_texture_audit.py — Find unused textures/flats and report per-map usage.

Useful when cleaning up a WAD before release: spot defined-but-never-placed
assets that bloat the file, and see exactly which maps use which textures.

Usage:
    python examples/06_texture_audit.py
    python examples/06_texture_audit.py wads/freedoom2.wad
    python examples/06_texture_audit.py wads/freedoom2.wad --unused-only
    python examples/06_texture_audit.py wads/freedoom2.wad --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wadlib import WadFile
from wadlib.scanner import find_unused_flats, find_unused_textures, scan_usage

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit texture and flat usage")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("--pwad", metavar="PATH", help="Optional PWAD to layer on top")
    parser.add_argument("--unused-only", action="store_true",
                        help="Only print unused assets, not per-map breakdown")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Output as JSON")
    args = parser.parse_args()

    extra = [args.pwad] if args.pwad else []
    with WadFile.open(args.wad, *extra) as wad:
        usage = scan_usage(wad)
        unused_tex = find_unused_textures(wad)
        unused_flat = find_unused_flats(wad)

        if args.as_json:
            data = {
                "totals": {
                    "textures": usage.total_unique_textures,
                    "flats": usage.total_unique_flats,
                    "thing_types": usage.total_unique_thing_types,
                },
                "unused_textures": sorted(unused_tex),
                "unused_flats": sorted(unused_flat),
                "per_map": {
                    name: {
                        "things": mu.thing_count,
                        "linedefs": mu.linedef_count,
                        "sectors": mu.sector_count,
                        "textures": sorted(mu.textures),
                        "flats": sorted(mu.flats),
                    }
                    for name, mu in usage.per_map.items()
                },
            }
            json.dump(data, sys.stdout, indent=2)
            sys.stdout.write("\n")
            return

        # --- Summary ---
        print(f"WAD   : {args.wad}")
        print(f"Maps  : {len(usage.per_map)}")
        print(f"Unique textures used : {usage.total_unique_textures}")
        print(f"Unique flats used    : {usage.total_unique_flats}")
        print(f"Unique thing types   : {usage.total_unique_thing_types}")
        print()

        # --- Unused assets ---
        print(f"Unused textures ({len(unused_tex)}):")
        if unused_tex:
            for name in sorted(unused_tex):
                print(f"  {name}")
        else:
            print("  (none)")
        print()

        print(f"Unused flats ({len(unused_flat)}):")
        if unused_flat:
            for name in sorted(unused_flat):
                print(f"  {name}")
        else:
            print("  (none)")
        print()

        if args.unused_only:
            return

        # --- Per-map breakdown ---
        print("Per-map usage:")
        for map_name, mu in sorted(usage.per_map.items()):
            print(f"  {map_name}: {mu.thing_count} things  "
                  f"{mu.linedef_count} lines  "
                  f"{mu.sector_count} sectors  "
                  f"{len(mu.textures)} textures  "
                  f"{len(mu.flats)} flats")


if __name__ == "__main__":
    main()
