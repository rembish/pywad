"""wadcli diff — compare two WADs and report added/removed/changed lumps."""

import argparse
import json
import sys

from ...directory import DirectoryEntry
from ...lumps.base import BaseLump
from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad_a", help="base WAD (or IWAD)")
    p.add_argument("wad_b", help="WAD to compare against (e.g. a PWAD)")
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def _index(wad: WadFile) -> dict[str, DirectoryEntry]:
    """Last-wins index by name — mirrors how PWAD shadow resolution works."""
    result: dict[str, DirectoryEntry] = {}
    for entry in wad.directory:
        result[entry.name] = entry
    return result


def run(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    with WadFile(args.wad_a) as a, WadFile(args.wad_b) as b:
        idx_a = _index(a)
        idx_b = _index(b)

        names_a = set(idx_a)
        names_b = set(idx_b)

        added = sorted(names_b - names_a)
        removed = sorted(names_a - names_b)
        changed = sorted(
            name
            for name in names_a & names_b
            if idx_a[name].size != idx_b[name].size
            or BaseLump(idx_a[name]).raw() != BaseLump(idx_b[name]).raw()
        )
        unchanged = len(names_a & names_b) - len(changed)

        if args.json:
            print(
                json.dumps(
                    {
                        "added": added,
                        "removed": removed,
                        "changed": changed,
                        "unchanged": unchanged,
                    },
                    indent=2,
                )
            )
            return

        if not added and not removed and not changed:
            print("No differences found.")
            return

        if added:
            print(f"Added ({len(added)}):")
            for name in added:
                e = idx_b[name]
                print(f"  + {name:<12}  {e.size:>8} bytes")
        if removed:
            print(f"\nRemoved ({len(removed)}):")
            for name in removed:
                e = idx_a[name]
                print(f"  - {name:<12}  {e.size:>8} bytes")
        if changed:
            print(f"\nChanged ({len(changed)}):")
            for name in changed:
                sa = idx_a[name].size
                sb = idx_b[name].size
                delta = sb - sa
                sign = "+" if delta >= 0 else ""
                print(f"  ~ {name:<12}  {sa:>8} → {sb:>8} bytes  ({sign}{delta:+d})")

        print(f"\nUnchanged: {unchanged} lumps")
        sys.exit(1 if (added or removed or changed) else 0)
