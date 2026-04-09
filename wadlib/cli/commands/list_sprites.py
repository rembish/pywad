"""wadcli list sprites — list sprite lumps with dimensions and offsets."""

import argparse

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if not wad.sprites:
            print("No sprites found.")
            return
        print(f"{'NAME':<10}  {'WIDTH':>6}  {'HEIGHT':>6}  {'OFFSET_X':>9}  {'OFFSET_Y':>9}")
        print("-" * 48)
        for name, pic in sorted(wad.sprites.items()):
            print(
                f"{name:<10}  {pic.pic_width:>6}  {pic.pic_height:>6}"
                f"  {pic.left_offset:>9}  {pic.top_offset:>9}"
            )
