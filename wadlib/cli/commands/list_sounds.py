"""wadcli list sounds — list DMX sound lumps with sample rate and count."""

import argparse

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if not wad.sounds:
            print("No sounds found.")
            return
        print(f"{'NAME':<10}  {'RATE':>6}  {'SAMPLES':>10}")
        print("-" * 32)
        for name, snd in sorted(wad.sounds.items()):
            print(f"{name:<10}  {snd.rate:>6}  {snd.sample_count:>10}")
