#!/usr/bin/env python3
"""
04_pwad_stack.py — Load a base IWAD + PWAD using ResourceResolver.

This mirrors how a Doom engine loads mods: the base IWAD provides defaults,
each PWAD overrides or adds resources, and the last PWAD wins on conflicts.

ResourceResolver is the right tool when you need to:
  - Know *which file* a resource comes from (for audit/tooling)
  - List all colliding resources across a load order
  - Iterate every unique resource in priority order

Usage:
    python examples/04_pwad_stack.py
    python examples/04_pwad_stack.py wads/freedoom2.wad wads/blasphem.wad
"""

from __future__ import annotations

import sys
from pathlib import Path

from wadlib import ResourceResolver, WadFile

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_BASE = WADS / "freedoom2.wad"
DEFAULT_PWAD = WADS / "blasphem.wad"


def main(base: str, *pwads: str) -> None:
    all_paths = [base, *pwads]
    wads = [WadFile(p) for p in all_paths]

    try:
        # doom_load_order: last wins, matching `-iwad base -file p1 p2` semantics.
        # Use ResourceResolver(w1, w2, ...) if you want first-wins priority instead.
        resolver = ResourceResolver.doom_load_order(*wads)

        # --- Collision report ---
        # A collision means multiple sources define the same lump name.
        collisions = resolver.collisions()
        if collisions:
            print(f"Collisions ({len(collisions)} names):")
            for name, refs in sorted(collisions.items()):
                winner = refs[0]
                losers = refs[1:]
                print(f"  {name:<12} winner={Path(winner.archive.fd.name).name}"
                      f"  shadowed={[Path(r.archive.fd.name).name for r in losers]}")
        else:
            print("No collisions between sources.")
        print()

        # --- Where does a specific resource live? ---
        for check in ("PLAYPAL", "D_RUNNIN", "MAP01"):
            refs = resolver.find_all(check)
            if refs:
                src = Path(refs[0].archive.path).name
                print(f"  {check:<12} → {src} ({refs[0].size} bytes)"
                      + (f"  [{len(refs)-1} shadowed]" if len(refs) > 1 else ""))
            else:
                print(f"  {check:<12} → not found")
        print()

        # --- Resource inventory ---
        # iter_resources() yields exactly one ResourceRef per unique name
        # (the highest-priority match), optionally filtered by PK3 category.
        total = sum(1 for _ in resolver.iter_resources())
        print(f"Total unique resources across load order: {total}")

        # Shadow report: lumps defined in the base but overridden by a PWAD
        shadowed_count = sum(
            1 for ref in resolver.iter_resources() if resolver.shadowed(ref.name)
        )
        print(f"Resources shadowed by PWAD(s): {shadowed_count}")

    finally:
        for w in wads:
            w.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = [str(DEFAULT_BASE), str(DEFAULT_PWAD)]
    elif len(args) < 2:
        print(f"Usage: {Path(sys.argv[0]).name} BASE.WAD PWAD1.WAD [PWAD2.WAD ...]")
        sys.exit(1)
    main(args[0], *args[1:])
