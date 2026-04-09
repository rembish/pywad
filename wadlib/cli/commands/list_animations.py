"""wadcli list animations — list ANIMDEFS flat/texture sequences."""
import argparse
import sys

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
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
