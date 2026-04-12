"""wadcli list scripts — list ACS scripts in map BEHAVIOR lumps."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        all_scripts = []
        for m in wad.maps:
            if m.behavior is None or not hasattr(m.behavior, "scripts"):
                continue
            for s in m.behavior.scripts:
                all_scripts.append(
                    {
                        "map": m.name,
                        "number": s.number,
                        "type": s.type_name,
                        "args": s.arg_count,
                    }
                )

        if args.json:
            print(json.dumps(all_scripts, indent=2))
            return

        if not all_scripts:
            print("No ACS scripts found.")
            return

        print(f"{'Map':<8} {'#':<6} {'Type':<12} {'Args'}")
        print("-" * 36)
        for s in all_scripts:
            print(f"{s['map']:<8} {s['number']:<6} {s['type']:<12} {s['args']}")
        print(f"\n{len(all_scripts)} script(s) total.")
