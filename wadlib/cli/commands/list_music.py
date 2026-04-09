"""wadcli list music — list music lumps with sizes."""

import argparse

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if not wad.music:
            print("No music found.")
            return
        print(f"{'NAME':<14}  {'SIZE':>8}")
        print("-" * 26)
        for name, mus in sorted(wad.music.items()):
            size = len(mus.raw())
            print(f"{name:<14}  {size:>8}")
