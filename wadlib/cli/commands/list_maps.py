"""wadcli list maps — print maps with thing and linedef counts."""

import argparse
import json
import re
from collections.abc import Mapping

from ...lumps.mapinfo import MapInfoEntry, MapInfoLump
from ...lumps.zmapinfo import ZMapInfoEntry, ZMapInfoLump
from .._wad_args import open_wad

_DOOM1_MAP_RE = re.compile(r"^E(\d)M(\d)$", re.IGNORECASE)
_DOOM2_MAP_RE = re.compile(r"^MAP(\d{2})$", re.IGNORECASE)

# Doom 2 music lump names by map number (1-indexed)
_DOOM2_MUSIC = [
    "D_RUNNIN",
    "D_STALKS",
    "D_COUNTD",
    "D_BETWEE",
    "D_DOOM",
    "D_THE_DA",
    "D_SHAWN",
    "D_DDTBLU",
    "D_IN_CIT",
    "D_DEAD",
    "D_STLKS2",
    "D_THEDA2",
    "D_DOOM2",
    "D_DDTBL2",
    "D_RUNNI2",
    "D_DEAD2",
    "D_STLKS3",
    "D_ROMERO",
    "D_SHAWN2",
    "D_MESSAG",
    "D_COUNT2",
    "D_DDTBL3",
    "D_AMPIE",
    "D_THEDA3",
    "D_ADRIAN",
    "D_MESSG2",
    "D_ROMER2",
    "D_TENSE",
    "D_SHAWN3",
    "D_OPENIN",
    "D_EVIL",
    "D_ULTIMA",
]


def _resolve_mi(
    map_name: str,
    mapinfo: MapInfoLump | None,
    zmapinfo: ZMapInfoLump | None,
) -> ZMapInfoEntry | MapInfoEntry | None:
    """Return the MAPINFO or ZMAPINFO entry for map_name, or None."""
    # ZMAPINFO (ZDoom) takes priority when present — it has richer data
    if zmapinfo is not None:
        entry = zmapinfo.get(map_name)
        if entry is not None:
            return entry
    if mapinfo is not None:
        try:
            num = int(map_name.lstrip("MAPmapEe"))
        except ValueError:
            return None
        return mapinfo.get(num)
    return None


def _music_for_map(
    map_name: str,
    music: Mapping[str, object],
    mi_entry: ZMapInfoEntry | MapInfoEntry | None,
) -> str:
    """Return the music lump name (or cdtrack label) for this map."""
    # ZMAPINFO/MAPINFO may carry a direct music lump name
    if mi_entry is not None:
        direct = getattr(mi_entry, "music", None)
        if direct and direct in music:
            return str(direct)
        cdtrack = getattr(mi_entry, "cdtrack", None)
        if cdtrack is not None:
            return f"cd:{cdtrack}"

    m1 = _DOOM1_MAP_RE.match(map_name)
    if m1:
        e, m = m1.group(1), m1.group(2)
        for lump in (f"D_E{e}M{m}", f"MUS_E{e}M{m}"):
            if lump in music:
                return lump
        return ""

    m2 = _DOOM2_MAP_RE.match(map_name)
    if m2:
        idx = int(m2.group(1)) - 1
        if 0 <= idx < len(_DOOM2_MUSIC):
            lump = _DOOM2_MUSIC[idx]
            if lump in music:
                return lump

    return ""


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals
    with open_wad(args) as wad:
        if not wad.maps:
            if args.json:
                print("[]")
            else:
                print("No maps found.")
            return

        mapinfo = wad.mapinfo
        zmapinfo = wad.zmapinfo
        music = wad.music
        language = wad.language.strings if wad.language is not None else None

        rows = []
        for m in wad.maps:
            map_name = str(m)
            things = len(m.things) if m.things else 0
            lines = len(m.lines) if m.lines else 0
            verts = len(m.vertices) if m.vertices else 0
            sectors = len(m.sectors) if m.sectors else 0
            mi_entry = _resolve_mi(map_name, mapinfo, zmapinfo)

            raw_title: str = getattr(mi_entry, "title", "") or ""
            lookup_key: str | None = getattr(mi_entry, "title_lookup", None)
            if lookup_key and language:
                title = language.get(lookup_key.upper(), raw_title)
            else:
                title = raw_title

            lump = _music_for_map(map_name, music, mi_entry)
            rows.append(
                {
                    "name": map_name,
                    "title": title,
                    "music": lump,
                    "things": things,
                    "linedefs": lines,
                    "vertices": verts,
                    "sectors": sectors,
                }
            )

        if args.json:
            print(json.dumps(rows, indent=2))
            return

        has_title = mapinfo is not None or zmapinfo is not None
        has_music = bool(music)

        hdr_map = f"{'MAP':<10}"
        hdr_title = f"  {'TITLE':<28}" if has_title else ""
        hdr_music = f"  {'MUSIC':<12}" if has_music else ""
        hdr_counts = f"  {'THINGS':>8}  {'LINEDEFS':>10}  {'VERTICES':>10}  {'SECTORS':>8}"
        header = hdr_map + hdr_title + hdr_music + hdr_counts
        print(header)
        print("-" * len(header))

        for row in rows:
            line = f"{row['name']:<10}"
            if has_title:
                line += f"  {row['title']:<28}"
            if has_music:
                line += f"  {row['music']:<12}"
            line += (
                f"  {row['things']:>8}  {row['linedefs']:>10}"
                f"  {row['vertices']:>10}  {row['sectors']:>8}"
            )
            print(line)
