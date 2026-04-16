#!/usr/bin/env python3
"""
01_inspect_wad.py — Inspect the structure of any WAD file.

Usage:
    python examples/01_inspect_wad.py
    python examples/01_inspect_wad.py wads/freedoom2.wad
    python examples/01_inspect_wad.py wads/freedoom2.wad wads/blasphem.wad
"""

from __future__ import annotations

import sys
from pathlib import Path

from wadlib import WadFile
from wadlib.types import detect_game, get_category

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"


def inspect(base_path: str, *pwad_paths: str) -> None:
    with WadFile.open(base_path, *pwad_paths) as wad:
        game = detect_game(wad)

        print(f"File : {base_path}")
        if pwad_paths:
            print(f"PWAD : {', '.join(pwad_paths)}")
        print(f"Type : {wad.wad_type.name}")
        print(f"Game : {game.value}")
        print(f"Lumps: {len(wad.directory)}")
        print()

        # Maps
        maps = wad.maps
        print(f"Maps ({len(maps)}):")
        for m in maps:
            things = list(m.things)
            lines = list(m.lines)
            sectors = list(m.sectors)
            monsters = sum(
                1 for t in things if get_category(t.type, game).name == "MONSTER"
            )
            print(
                f"  {m!s:<8} {len(things):4} things  "
                f"{monsters:3} monsters  "
                f"{len(lines):4} lines  "
                f"{len(sectors):3} sectors"
            )
        print()

        # Asset counts
        print("Assets:")
        print(f"  Flats   : {len(wad.flats)}")
        print(f"  Sprites : {len(wad.sprites)}")
        print(f"  Sounds  : {len(wad.sounds)}")
        print(f"  Music   : {len(wad.music)}")

        tex1 = wad.texture1
        tex2 = wad.texture2
        tex_count = (len(tex1.textures) if tex1 else 0) + (
            len(tex2.textures) if tex2 else 0
        )
        print(f"  Textures: {tex_count}")
        print()

        # Source-port lumps present
        sp_lumps = []
        if wad.zmapinfo:
            zi = wad.zmapinfo
            sp_lumps.append(
                f"ZMAPINFO ({len(zi.maps)} maps, {len(zi.episodes)} episodes)"
            )
        if wad.decorate:
            d = wad.decorate
            sp_lumps.append(f"DECORATE ({len(d.actors)} actors)")
        if wad.language:
            sp_lumps.append("LANGUAGE")
        if wad.dehacked:
            sp_lumps.append("DEHACKED")

        if sp_lumps:
            print("Source-port lumps:")
            for lump in sp_lumps:
                print(f"  {lump}")
        else:
            print("No source-port lumps detected.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        args = [str(DEFAULT_WAD)]
    inspect(args[0], *args[1:])
