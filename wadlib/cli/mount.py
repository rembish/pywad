"""wadmount — mount a WAD file as a FUSE filesystem."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wadmount",
        description="Mount a Doom WAD file as a virtual filesystem.",
    )
    parser.add_argument("wad", help="path to the WAD file")
    parser.add_argument("mountpoint", help="directory to mount on (must exist)")
    parser.add_argument(
        "--readonly",
        "-r",
        action="store_true",
        help="mount read-only (default: read-write)",
    )
    parser.add_argument(
        "--background",
        "-b",
        action="store_true",
        help="run in background (default: foreground)",
    )

    args = parser.parse_args()

    try:
        from ..fuse import mount
    except ImportError:
        print(
            "Error: fusepy is required for WAD mounting.\nInstall it with: pip install fusepy",
            file=sys.stderr,
        )
        sys.exit(1)

    mount(
        args.wad,
        args.mountpoint,
        foreground=not args.background,
        writable=not args.readonly,
    )
