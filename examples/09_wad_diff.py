#!/usr/bin/env python3
"""
09_wad_diff.py — Show what a PWAD changes relative to a base WAD.

Useful for understanding what a mod actually modifies: which lumps are replaced,
which are new additions, and — for map lumps — how the thing/linedef counts changed.

Usage:
    python examples/09_wad_diff.py
    python examples/09_wad_diff.py wads/freedoom1.wad wads/freedoom2.wad
    python examples/09_wad_diff.py wads/freedoom1.wad wads/freedoom2.wad --maps
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wadlib import WadFile

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_BASE = WADS / "freedoom1.wad"
DEFAULT_PATCH = WADS / "freedoom2.wad"


def diff_wads(base_path: str, patch_path: str, show_maps: bool) -> None:
    with WadFile(base_path) as base, WadFile(patch_path) as patch:
        base_lumps = {e.name: e for e in base.directory}
        patch_lumps = {e.name: e for e in patch.directory}

        added = sorted(n for n in patch_lumps if n not in base_lumps)
        removed = sorted(n for n in base_lumps if n not in patch_lumps)
        changed = sorted(
            n for n in patch_lumps
            if n in base_lumps and patch_lumps[n].size != base_lumps[n].size
        )
        unchanged = sorted(
            n for n in patch_lumps
            if n in base_lumps and patch_lumps[n].size == base_lumps[n].size
        )

        print(f"Base : {base_path}  ({len(base_lumps)} lumps)")
        print(f"Patch: {patch_path} ({len(patch_lumps)} lumps)")
        print()

        if added:
            print(f"Added ({len(added)}):")
            for name in added:
                print(f"  + {name:<12}  {patch_lumps[name].size} bytes")
            print()

        if removed:
            print(f"Removed ({len(removed)}):")
            for name in removed:
                print(f"  - {name}")
            print()

        if changed:
            print(f"Changed ({len(changed)}):")
            for name in changed:
                old = base_lumps[name].size
                new = patch_lumps[name].size
                delta = new - old
                sign = "+" if delta >= 0 else ""
                print(f"  ~ {name:<12}  {old} → {new} bytes  ({sign}{delta})")
            print()

        print(f"Unchanged: {len(unchanged)} lumps")

        # --- Map-level diff ---
        if not show_maps:
            return

        base_map_names = {str(m) for m in base.maps}
        patch_map_names = {str(m) for m in patch.maps}
        new_maps = patch_map_names - base_map_names
        replaced_maps = patch_map_names & base_map_names

        if new_maps:
            print(f"\nNew maps ({len(new_maps)}): {', '.join(sorted(new_maps))}")

        if replaced_maps:
            print(f"\nReplaced maps ({len(replaced_maps)}):")

            base_by_name = {str(m): m for m in base.maps}
            patch_by_name = {str(m): m for m in patch.maps}

            for name in sorted(replaced_maps):
                bm = base_by_name[name]
                pm = patch_by_name[name]
                b_things = len(list(bm.things))
                p_things = len(list(pm.things))
                b_lines = len(list(bm.lines))
                p_lines = len(list(pm.lines))
                b_sec = len(list(bm.sectors))
                p_sec = len(list(pm.sectors))

                def delta(old: int, new: int) -> str:
                    d = new - old
                    return f"{new} ({'+' if d >= 0 else ''}{d})"

                print(f"  {name}: things {delta(b_things, p_things)}"
                      f"  lines {delta(b_lines, p_lines)}"
                      f"  sectors {delta(b_sec, p_sec)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff a PWAD against a base WAD")
    parser.add_argument("base", nargs="?", default=str(DEFAULT_BASE))
    parser.add_argument("patch", nargs="?", default=str(DEFAULT_PATCH))
    parser.add_argument("--maps", action="store_true",
                        help="Show per-map thing/linedef/sector deltas")
    args = parser.parse_args()
    diff_wads(args.base, args.patch, args.maps)


if __name__ == "__main__":
    main()
