"""wadcli list sounds — list DMX sound lumps with sample rate and count."""

import argparse
import struct

from ...wad import WadFile

_HEADER_FMT = "<HHI"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)


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
            data = snd.raw()
            _fmt, rate, num_samples = struct.unpack_from(_HEADER_FMT, data)
            print(f"{name:<10}  {rate:>6}  {num_samples:>10}")
