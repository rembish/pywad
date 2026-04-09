"""wadcli list music — list music lumps with sizes."""

import argparse

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if not wad.music:
            print("No music found.")
            return
        print(f"{'NAME':<14}  {'SIZE':>8}")
        print("-" * 26)
        for name, mus in sorted(wad.music.items()):
            size = len(mus.raw())
            print(f"{name:<14}  {size:>8}")
