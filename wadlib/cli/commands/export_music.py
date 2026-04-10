"""wadcli export music -- export a MUS lump as MIDI, OGG, MP3, or raw bytes."""

import argparse
import sys

from ...lumps.mus import Mus
from ...lumps.ogg import MidiLump, Mp3Lump, OggLump
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("name", help="music lump name, e.g. D_E1M1")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output file path (default: <NAME>.<ext> based on format)",
    )
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
            ext = ".mus" if args.raw else ".mid"
        elif isinstance(lump, MidiLump):
            data = lump.raw()
            fmt = "MIDI"
            ext = ".mid"
        elif isinstance(lump, OggLump):
            data = lump.raw()
            fmt = "OGG"
            ext = ".ogg"
        else:
            assert isinstance(lump, Mp3Lump)
            data = lump.raw()
            fmt = "MP3"
            ext = ".mp3"

        output: str = args.output or f"{lump_name}{ext}"
        with open(output, "wb") as f:
            f.write(data)

        print(f"Saved {len(data)} bytes ({fmt}) to {output}")
