"""wadcli list actors — list DECORATE actor definitions."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from ...lumps.decorate import parse_decorate

    with open_wad(args) as wad:
        entry = wad.find_lump("DECORATE")
        if entry is None:
            if args.json:
                print("[]")
            else:
                print("No DECORATE lump found.")
            return

        wad.fd.seek(entry.offset)
        text = wad.fd.read(entry.size).decode("utf-8", errors="replace")
        actors = parse_decorate(text)

        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": a.name,
                            "parent": a.parent,
                            "doomednum": a.doomednum,
                            "health": a.health,
                            "monster": a.is_monster,
                            "item": a.is_item,
                            "states": a.states,
                        }
                        for a in actors
                    ],
                    indent=2,
                )
            )
            return

        if not actors:
            print("No actors defined in DECORATE.")
            return

        print(f"{'Name':<24} {'EdNum':<8} {'Parent':<16} {'Type'}")
        print("-" * 60)
        for a in actors:
            ednum = str(a.doomednum) if a.doomednum is not None else "-"
            atype = "monster" if a.is_monster else "item" if a.is_item else "other"
            print(f"{a.name:<24} {ednum:<8} {a.parent or '-':<16} {atype}")
        print(f"\n{len(actors)} actor(s) total.")
