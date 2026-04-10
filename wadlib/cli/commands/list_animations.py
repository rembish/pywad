"""wadcli list animations — list ANIMDEFS flat/texture sequences."""

import argparse
import json
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if wad.animdefs is None:
            print("No ANIMDEFS lump found.", file=sys.stderr)
            sys.exit(1)
        anims = wad.animdefs.animations
        if not anims:
            if args.json:
                print("[]")
            else:
                print("No animations defined.")
            return
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": a.name,
                            "kind": a.kind,
                            "frames": len(a.frames),
                            "random": a.is_random,
                        }
                        for a in anims
                    ],
                    indent=2,
                )
            )
            return
        print(f"{'NAME':<16}  {'TYPE':<8}  {'FRAMES':>6}  {'TIMING'}")
        print("-" * 48)
        for anim in anims:
            timing = "random" if anim.is_random else f"{anim.frames[0].min_tics} tics"
            print(f"{anim.name:<16}  {anim.kind:<8}  {len(anim.frames):>6}  {timing}")
