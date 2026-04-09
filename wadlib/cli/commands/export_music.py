"""wadcli export music — export a MUS lump as MIDI or raw MUS bytes."""

import argparse
import sys

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.add_argument("name", help="music lump name, e.g. D_E1M1")
    p.add_argument("output", help="output file path")
    p.add_argument(
        "--raw",
        action="store_true",
        help="write raw MUS bytes instead of converting to MIDI",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    lump_name = args.name.upper()
    with open_wad(args) as wad:
        mus = wad.get_music(lump_name)
        if mus is None:
            available = ", ".join(sorted(wad.music))
            print(
                f"Music lump '{lump_name}' not found.\nAvailable: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

        data = mus.raw() if args.raw else mus.to_midi()
        with open(args.output, "wb") as f:
            f.write(data)

        fmt = "MUS" if args.raw else "MIDI"
        print(f"Saved {len(data)} bytes ({fmt}) to {args.output}")
