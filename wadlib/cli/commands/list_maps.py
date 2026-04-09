"""wadcli list maps — print maps with thing and linedef counts."""

import argparse
import re

from ...wad import WadFile

_DOOM1_MAP_RE = re.compile(r"^E(\d)M(\d)$", re.IGNORECASE)
_DOOM2_MAP_RE = re.compile(r"^MAP(\d{2})$", re.IGNORECASE)

# Doom 2 music lump names by map number (1-indexed)
_DOOM2_MUSIC = [
    "D_RUNNIN", "D_STALKS", "D_COUNTD", "D_BETWEE", "D_DOOM",
    "D_THE_DA", "D_SHAWN", "D_DDTBLU", "D_IN_CIT", "D_DEAD",
    "D_STLKS2", "D_THEDA2", "D_DOOM2", "D_DDTBL2", "D_RUNNI2",
    "D_DEAD2", "D_STLKS3", "D_ROMERO", "D_SHAWN2", "D_MESSAG",
    "D_COUNT2", "D_DDTBL3", "D_AMPIE", "D_THEDA3", "D_ADRIAN",
    "D_MESSG2", "D_ROMER2", "D_TENSE", "D_SHAWN3", "D_OPENIN",
    "D_EVIL", "D_ULTIMA",
]


def _music_for_map(map_name: str, music: dict, mapinfo_entry: object = None) -> str:
    """Return the music lump name (or cdtrack label) for this map."""
    m1 = _DOOM1_MAP_RE.match(map_name)
    if m1:
        e, m = m1.group(1), m1.group(2)
        # Doom 1 convention: D_E1M1; Heretic convention: MUS_E1M1
        for lump in (f"D_E{e}M{m}", f"MUS_E{e}M{m}"):
            if lump in music:
                return lump
        return ""
    m2 = _DOOM2_MAP_RE.match(map_name)
    if m2:
        idx = int(m2.group(1)) - 1
        # Doom 2 conventional lump names
        if 0 <= idx < len(_DOOM2_MUSIC):
            lump = _DOOM2_MUSIC[idx]
            if lump in music:
                return lump
        # Hexen (and PWADs): fall back to cdtrack from MAPINFO
        if mapinfo_entry is not None:
            cdtrack = getattr(mapinfo_entry, "cdtrack", None)
            if cdtrack is not None:
                return f"cd:{cdtrack}"
    return ""


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if not wad.maps:
            print("No maps found.")
            return

        mapinfo = wad.mapinfo
        music = wad.music

        # Determine if any map has a title or music to show
        has_title = mapinfo is not None
        has_music = bool(music)

        hdr_map = f"{'MAP':<10}"
        hdr_title = f"  {'TITLE':<28}" if has_title else ""
        hdr_music = f"  {'MUSIC':<12}" if has_music else ""
        hdr_counts = "  {:>8}  {:>10}  {:>10}  {:>8}".format(
            "THINGS", "LINEDEFS", "VERTICES", "SECTORS"
        )
        header = hdr_map + hdr_title + hdr_music + hdr_counts
        print(header)
        print("-" * len(header))

        for m in wad.maps:
            map_name = str(m)
            things = len(m.things) if m.things else 0
            lines = len(m.lines) if m.lines else 0
            verts = len(m.vertices) if m.vertices else 0
            sectors = len(m.sectors) if m.sectors else 0

            # Resolve MAPINFO entry once for both title and music
            mi_entry = None
            if mapinfo is not None:
                try:
                    num = int(map_name.lstrip("MAPmap"))
                except ValueError:
                    num = -1
                mi_entry = mapinfo.get(num) if num >= 0 else None

            row = f"{map_name:<10}"

            if has_title:
                title = mi_entry.title if mi_entry else ""
                row += f"  {title:<28}"

            if has_music:
                lump = _music_for_map(map_name, music, mi_entry)
                row += f"  {lump:<12}"

            row += f"  {things:>8}  {lines:>10}  {verts:>10}  {sectors:>8}"
            print(row)
