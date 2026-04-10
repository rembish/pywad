"""wadcli export sound — export a DMX sound lump as WAV or raw bytes."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("name", help="sound lump name, e.g. DSPISTOL")
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output file path (default: <NAME>.wav or <NAME>.dmx with --raw)",
    )
    p.add_argument(
        "--raw",
        action="store_true",
        help="write raw DMX bytes instead of converting to WAV",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    lump_name = args.name.upper()
    ext = ".dmx" if args.raw else ".wav"
    output: str = args.output or f"{lump_name}{ext}"
    with open_wad(args) as wad:
        snd = wad.get_sound(lump_name)
        if snd is None:
            available = ", ".join(sorted(wad.sounds))
            print(
                f"Sound lump '{lump_name}' not found.\nAvailable: {available}",
                file=sys.stderr,
            )
            sys.exit(1)

        data = snd.raw() if args.raw else snd.to_wav()
        with open(output, "wb") as f:
            f.write(data)

        fmt = "raw" if args.raw else "WAV"
        print(f"Saved {len(data)} bytes ({fmt}) to {output}")
