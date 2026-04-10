"""wadcli list sprites — list sprite lumps with dimensions and offsets."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if not wad.sprites:
            if args.json:
                print("[]")
            else:
                print("No sprites found.")
            return
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": name,
                            "width": pic.pic_width,
                            "height": pic.pic_height,
                            "offset_x": pic.left_offset,
                            "offset_y": pic.top_offset,
                        }
                        for name, pic in sorted(wad.sprites.items())
                    ],
                    indent=2,
                )
            )
            return
        print(f"{'NAME':<10}  {'WIDTH':>6}  {'HEIGHT':>6}  {'OFFSET_X':>9}  {'OFFSET_Y':>9}")
        print("-" * 48)
        for name, pic in sorted(wad.sprites.items()):
            print(
                f"{name:<10}  {pic.pic_width:>6}  {pic.pic_height:>6}"
                f"  {pic.left_offset:>9}  {pic.top_offset:>9}"
            )
