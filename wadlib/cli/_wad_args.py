"""Shared helpers for WAD path CLI arguments."""

from __future__ import annotations

import argparse
import sys

from ..wad import WadFile


def open_wad(args: argparse.Namespace) -> WadFile:
    """Open the WAD specified by *args*, layering any ``--pwad`` files on top.

    If ``--deh`` was supplied the standalone DeHackEd file is loaded into
    the returned WAD as its ``dehacked`` property.
    """
    wad_path: str | None = getattr(args, "wad", None)
    if not wad_path:
        print("error: --wad is required", file=sys.stderr)
        sys.exit(2)
    pwads: list[str] = getattr(args, "pwads", []) or []
    wad = WadFile.open(wad_path, *pwads)
    deh: str | None = getattr(args, "deh", None)
    if deh:
        wad.load_deh(deh)
    return wad
