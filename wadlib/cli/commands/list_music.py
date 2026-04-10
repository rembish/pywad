"""wadcli list music — list music lumps with sizes."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if not wad.music:
            if args.json:
                print("[]")
            else:
                print("No music found.")
            return
        if args.json:
            print(
                json.dumps(
                    [
                        {"name": name, "size": len(mus.raw())}
                        for name, mus in sorted(wad.music.items())
                    ],
                    indent=2,
                )
            )
            return
        print(f"{'NAME':<14}  {'SIZE':>8}")
        print("-" * 26)
        for name, mus in sorted(wad.music.items()):
            size = len(mus.raw())
            print(f"{name:<14}  {size:>8}")
