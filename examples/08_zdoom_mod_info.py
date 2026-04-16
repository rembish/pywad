#!/usr/bin/env python3
"""
08_zdoom_mod_info.py — Read ZDoom source-port lumps: ZMAPINFO, DECORATE, LANGUAGE.

Useful when analysing a ZDoom/GZDoom mod to understand its maps, custom actors,
replaced monsters, include structure, and localised strings.

Usage:
    python examples/08_zdoom_mod_info.py
    python examples/08_zdoom_mod_info.py wads/blasphem.wad
    python examples/08_zdoom_mod_info.py DOOM2.WAD --pwad brutal_doom.wad
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wadlib import WadFile
from wadlib.lumps.decorate import resolve_inheritance

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "blasphem.wad"


def report_zmapinfo(wad: WadFile) -> None:
    zi = wad.zmapinfo
    if zi is None:
        print("ZMAPINFO: not present")
        return

    print(f"ZMAPINFO: {len(zi.maps)} maps, "
          f"{len(zi.episodes)} episodes, "
          f"{len(zi.clusters)} clusters")

    if zi.defaultmap:
        dm = zi.defaultmap
        fields = []
        if dm.sky1:
            fields.append(f"sky1={dm.sky1}")
        if dm.music:
            fields.append(f"music={dm.music}")
        if fields:
            print(f"  defaultmap: {', '.join(fields)}")

    for ep in zi.episodes:
        name = ep.name or f"lookup:{ep.name_lookup}"
        print(f"  episode {ep.map}: {name!r}  pic={ep.pic_name!r}  key={ep.key!r}")

    for cl in zi.clusters:
        print(f"  cluster {cl.cluster_num}: exittext={cl.exittext!r}  music={cl.music!r}")

    for entry in zi.maps:
        title = entry.title or (f"lookup:{entry.title_lookup}" if entry.title_lookup else "")
        extras = []
        if entry.sky1:
            extras.append(f"sky={entry.sky1}")
        if entry.music:
            extras.append(f"music={entry.music}")
        if entry.cluster is not None:
            extras.append(f"cluster={entry.cluster}")
        if entry.props:
            extras.append(f"props={list(entry.props)}")
        detail = "  " + ", ".join(extras) if extras else ""
        print(f"  map {entry.map_name}: {title!r}{detail}")
    print()


def report_decorate(wad: WadFile) -> None:
    dec = wad.decorate
    if dec is None:
        print("DECORATE: not present")
        return

    print(f"DECORATE: {len(dec.actors)} actors")

    if dec.includes:
        print(f"  Includes ({len(dec.includes)}):")
        for path in dec.includes:
            print(f"    #include {path!r}")

    if dec.replacements:
        print(f"  Replacements ({len(dec.replacements)}):")
        for old, new in dec.replacements.items():
            print(f"    {old} → {new}")

    # Resolve inheritance so computed properties are filled from parent chains
    actors = resolve_inheritance(dec.actors)
    monsters = [a for a in actors if a.is_monster]
    items = [a for a in actors if a.is_item]
    numbered = [a for a in actors if a.doomednum is not None]

    print(f"  Monsters: {len(monsters)}  Items: {len(items)}  "
          f"With DoomEdNum: {len(numbered)}")

    print("  Actors (name, ednum, parent, health, radius):")
    for actor in actors[:20]:  # cap at 20 for readability
        ednum = actor.doomednum if actor.doomednum is not None else "-"
        health = actor.health if actor.health is not None else "-"
        radius = actor.radius if actor.radius is not None else "-"
        parent = actor.parent or "-"
        print(f"    {actor.name:<30} ednum={ednum:<6} parent={parent:<20} "
              f"hp={health:<5} r={radius}")
    if len(actors) > 20:
        print(f"    ... and {len(actors) - 20} more")
    print()


def report_language(wad: WadFile) -> None:
    lang = wad.language
    if lang is None:
        print("LANGUAGE: not present")
        return

    locales = list(lang.all_locales.keys())
    total = sum(len(v) for v in lang.all_locales.values())
    print(f"LANGUAGE: {total} strings across {len(locales)} locale(s): {locales}")

    # Sample a few keys
    enu = lang.strings_for("enu") or lang.strings_for("default") or {}
    sample = list(enu.items())[:5]
    if sample:
        print("  Sample [enu]:")
        for k, v in sample:
            print(f"    {k} = {v!r}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Report ZDoom source-port lump info")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("--pwad", metavar="PATH", help="Optional PWAD to layer on top")
    args = parser.parse_args()

    extra = [args.pwad] if args.pwad else []
    with WadFile.open(args.wad, *extra) as wad:
        report_zmapinfo(wad)
        report_decorate(wad)
        report_language(wad)


if __name__ == "__main__":
    main()
