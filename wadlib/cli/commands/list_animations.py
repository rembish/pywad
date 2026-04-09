"""wadcli list animations — list ANIMDEFS flat/texture sequences."""
import argparse
import sys

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if wad.animdefs is None:
            print("No ANIMDEFS lump found.", file=sys.stderr)
            sys.exit(1)
        anims = wad.animdefs.animations
        if not anims:
            print("No animations defined.")
            return
        print(f"{'NAME':<16}  {'TYPE':<8}  {'FRAMES':>6}  {'TIMING'}")
        print("-" * 48)
        for anim in anims:
            timing = "random" if anim.is_random else f"{anim.frames[0].min_tics} tics"
            print(f"{anim.name:<16}  {anim.kind:<8}  {len(anim.frames):>6}  {timing}")
