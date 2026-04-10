"""wadcli list stats — aggregate statistics across all maps."""

import argparse
import json
from collections import Counter

from ...doom_types import ThingCategory, get_category
from ...lumps.map import BaseMapEntry
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def _category_counts(maps: list[BaseMapEntry]) -> dict[str, int]:
    """Return thing counts grouped by ThingCategory across all maps."""
    counts: Counter[str] = Counter()
    for m in maps:
        things = getattr(m, "things", None)
        if things is None:
            continue
        for thing in things:
            cat = get_category(thing.type)
            counts[cat.value] += 1
    return dict(counts)


def run(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    with open_wad(args) as wad:
        if not wad.maps:
            if args.json:
                print("{}")
            else:
                print("No maps found.")
            return

        maps = wad.maps
        total_maps = len(maps)
        total_things = sum(len(m.things) if m.things else 0 for m in maps)
        total_lines = sum(len(m.lines) if m.lines else 0 for m in maps)
        total_verts = sum(len(m.vertices) if m.vertices else 0 for m in maps)
        total_sectors = sum(len(m.sectors) if m.sectors else 0 for m in maps)

        # Secret sectors (special == 9)
        total_secrets = sum(sum(1 for s in m.sectors if s.special == 9) for m in maps if m.sectors)

        by_category = _category_counts(maps)

        # Per-map totals for min/max/avg
        thing_counts = [len(m.things) if m.things else 0 for m in maps]
        line_counts = [len(m.lines) if m.lines else 0 for m in maps]

        if args.json:
            print(
                json.dumps(
                    {
                        "maps": total_maps,
                        "things": total_things,
                        "linedefs": total_lines,
                        "vertices": total_verts,
                        "sectors": total_sectors,
                        "secrets": total_secrets,
                        "things_by_category": by_category,
                        "per_map": {
                            "things": {
                                "min": min(thing_counts),
                                "max": max(thing_counts),
                                "avg": round(total_things / total_maps, 1),
                            },
                            "linedefs": {
                                "min": min(line_counts),
                                "max": max(line_counts),
                                "avg": round(total_lines / total_maps, 1),
                            },
                        },
                    },
                    indent=2,
                )
            )
            return

        print(f"Maps     : {total_maps}")
        print(
            f"Things   : {total_things}  (avg {total_things / total_maps:.0f}/map,"
            f" min {min(thing_counts)}, max {max(thing_counts)})"
        )
        print(
            f"Linedefs : {total_lines}  (avg {total_lines / total_maps:.0f}/map,"
            f" min {min(line_counts)}, max {max(line_counts)})"
        )
        print(f"Vertices : {total_verts}")
        print(f"Sectors  : {total_sectors}")
        print(f"Secrets  : {total_secrets}")
        print()
        print("Things by category:")
        for cat in ThingCategory:
            count = by_category.get(cat.value, 0)
            if count:
                print(f"  {cat.value:<14} {count:>6}")
