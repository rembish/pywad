"""wadcli list sounds — list DMX sound lumps with sample rate and count."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        if not wad.sounds:
            if args.json:
                print("[]")
            else:
                print("No sounds found.")
            return
        if args.json:
            print(
                json.dumps(
                    [
                        {"name": name, "rate": snd.rate, "samples": snd.sample_count}
                        for name, snd in sorted(wad.sounds.items())
                    ],
                    indent=2,
                )
            )
            return
        print(f"{'NAME':<10}  {'RATE':>6}  {'SAMPLES':>10}")
        print("-" * 32)
        for name, snd in sorted(wad.sounds.items()):
            print(f"{name:<10}  {snd.rate:>6}  {snd.sample_count:>10}")
