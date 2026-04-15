"""wadcli list mapinfo — list MAPINFO / ZMAPINFO map entries."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        # Prefer ZMAPINFO (ZDoom) over Hexen MAPINFO when both are present
        zmapinfo = wad.zmapinfo
        mapinfo = wad.mapinfo

        if zmapinfo is not None and zmapinfo.maps:
            _print_zmapinfo(zmapinfo, args.json)
        elif mapinfo is not None and mapinfo.maps:
            _print_mapinfo(mapinfo, args.json)
        else:
            if args.json:
                print("[]")
            else:
                print("No MAPINFO or ZMAPINFO lump found.")


def _print_mapinfo(mapinfo, as_json: bool) -> None:  # type: ignore[no-untyped-def]
    entries = mapinfo.maps
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "map_num": e.map_num,
                        "title": e.title,
                        "warptrans": e.warptrans,
                        "next": e.next,
                        "cluster": e.cluster,
                        "sky1": e.sky1,
                        "sky2": e.sky2,
                        "cdtrack": e.cdtrack,
                        "lightning": e.lightning,
                        "doublesky": e.doublesky,
                    }
                    for e in entries
                ],
                indent=2,
            )
        )
        return

    print(f"{'#':<6} {'Title':<32} {'Next':<8} {'Sky1':<12} {'Sky2'}")
    print("-" * 72)
    for e in entries:
        nxt = str(e.next) if e.next is not None else "-"
        sky1 = e.sky1 or "-"
        sky2 = e.sky2 or "-"
        print(f"{e.map_num:<6} {e.title:<32} {nxt:<8} {sky1:<12} {sky2}")
    print(f"\n{len(entries)} map(s) in MAPINFO.")


def _print_zmapinfo(zmapinfo, as_json: bool) -> None:  # type: ignore[no-untyped-def]
    entries = zmapinfo.maps
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "map_name": e.map_name,
                        "title": e.title,
                        "music": e.music,
                        "sky1": e.sky1,
                        "next": e.next,
                        "secretnext": e.secretnext,
                        "cluster": e.cluster,
                    }
                    for e in entries
                ],
                indent=2,
            )
        )
        return

    print(f"{'Map':<12} {'Title':<32} {'Music':<14} {'Next':<10} {'Sky1'}")
    print("-" * 75)
    for e in entries:
        music = e.music or "-"
        nxt = e.next or "-"
        sky1 = e.sky1 or "-"
        print(f"{e.map_name:<12} {e.title:<32} {music:<14} {nxt:<10} {sky1}")
    print(f"\n{len(entries)} map(s) in ZMAPINFO.")
