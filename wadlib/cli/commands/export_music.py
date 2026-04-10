"""wadcli export music -- export a MUS lump as MIDI, OGG, MP3, or raw bytes."""

import argparse
import sys

from ...lumps.mus import Mus
from ...lumps.ogg import Mp3Lump, OggLump
from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.add_argument("name", help="music lump name, e.g. D_E1M1")
    p.add_argument("output", help="output file path")
    p.add_argument(
        "--raw",
        action="store_true",
        help="write raw MUS bytes instead of converting to MIDI (MUS lumps only)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    lump_name = args.name.upper()
    with open_wad(args) as wad:
        lump = wad.get_music(lump_name)
        if lump is None:
            available = ", ".join(sorted(wad.music))
            print(
                f"Music lump '{lump_name}' not found.\nAvailable: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

        if isinstance(lump, Mus):
            data = lump.raw() if args.raw else lump.to_midi()
            fmt = "MUS" if args.raw else "MIDI"
        elif isinstance(lump, OggLump):
            data = lump.raw()
            fmt = "OGG"
        else:
            assert isinstance(lump, Mp3Lump)
            data = lump.raw()
            fmt = "MP3"

        with open(args.output, "wb") as f:
            f.write(data)

        print(f"Saved {len(data)} bytes ({fmt}) to {args.output}")
