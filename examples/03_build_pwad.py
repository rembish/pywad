#!/usr/bin/env python3
"""
03_build_pwad.py — Build a minimal PWAD from scratch and validate it.

This demonstrates the core modding workflow: create new map data, add custom
assets, write the PWAD, then verify it loads cleanly.

The output WAD can be loaded alongside any Doom-compatible IWAD, e.g.:
    gzdoom -iwad freedoom2.wad -file hello_doom.wad

Usage:
    python examples/03_build_pwad.py
    python examples/03_build_pwad.py --output my_mod.wad
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wadlib import WadFile, WadWriter
from wadlib.enums import WadType
from wadlib.lumps.lines import LineDefinition
from wadlib.lumps.sectors import Sector
from wadlib.lumps.sidedefs import SideDef
from wadlib.lumps.things import Flags, Thing
from wadlib.lumps.vertices import Vertex
from wadlib.validate import validate_wad

DEFAULT_OUT = Path(__file__).parent / "hello_doom.wad"


def build_map() -> dict:
    """
    A tiny square room: four walls, a player start, and one Zombieman.

    Vertices (counter-clockwise):
        (0,0) → (256,0) → (256,256) → (0,256)
    """
    vertices = [
        Vertex(0, 0),
        Vertex(256, 0),
        Vertex(256, 256),
        Vertex(0, 256),
    ]

    # A sector is the floor/ceiling space enclosed by sidedefs.
    sectors = [
        Sector(
            floor_height=0,
            ceiling_height=128,
            floor_texture="FLOOR0_1",
            ceiling_texture="CEIL3_5",
            light_level=192,
            special=0,
            tag=0,
        )
    ]

    # One sidedef per wall face, all pointing into sector 0.
    # middle_texture is the wall graphic; use "-" for invisible faces.
    sidedefs = [
        SideDef(x_offset=0, y_offset=0, upper_texture="-",
                lower_texture="-", middle_texture="STARTAN2", sector=0),
        SideDef(x_offset=0, y_offset=0, upper_texture="-",
                lower_texture="-", middle_texture="STARTAN2", sector=0),
        SideDef(x_offset=0, y_offset=0, upper_texture="-",
                lower_texture="-", middle_texture="STARTAN2", sector=0),
        SideDef(x_offset=0, y_offset=0, upper_texture="-",
                lower_texture="-", middle_texture="STARTAN2", sector=0),
    ]

    # Linedefs connect two vertices and reference a front sidedef.
    # impassable flag (0x1) makes them solid walls.
    linedefs = [
        LineDefinition(start_vertex=0, finish_vertex=1, flags=1,
                       special_type=0, sector_tag=0, right_sidedef=0, left_sidedef=-1),
        LineDefinition(start_vertex=1, finish_vertex=2, flags=1,
                       special_type=0, sector_tag=0, right_sidedef=1, left_sidedef=-1),
        LineDefinition(start_vertex=2, finish_vertex=3, flags=1,
                       special_type=0, sector_tag=0, right_sidedef=2, left_sidedef=-1),
        LineDefinition(start_vertex=3, finish_vertex=0, flags=1,
                       special_type=0, sector_tag=0, right_sidedef=3, left_sidedef=-1),
    ]

    things = [
        # Player 1 start (type 1) — required for a playable map
        Thing(x=64, y=64, direction=90, type=1, flags=Flags(7)),
        # Zombieman (type 3004) — flags=7 means present on all skill levels
        Thing(x=192, y=192, direction=270, type=3004, flags=Flags(7)),
    ]

    return {
        "things": things,
        "vertices": vertices,
        "linedefs": linedefs,
        "sidedefs": sidedefs,
        "sectors": sectors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a minimal PWAD")
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    writer = WadWriter(WadType.PWAD)
    writer.add_map("MAP01", **build_map())

    # Validate before saving: catches namespace errors, bad lump names, etc.
    issues = validate_wad(writer)
    if issues:
        for issue in issues:
            print(f"[WARN] {issue}")
    else:
        print("Validation passed.")

    writer.save(args.output)
    print(f"Saved: {args.output}")

    # Round-trip check: re-open and verify the map parses correctly.
    with WadFile(args.output) as wad:
        m = wad.maps[0]
        print(f"Re-opened: {m} — "
              f"{len(list(m.things))} things, "
              f"{len(list(m.lines))} linedefs, "
              f"{len(list(m.sectors))} sectors")


if __name__ == "__main__":
    main()
