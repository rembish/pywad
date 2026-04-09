"""Shared helpers for WAD path CLI arguments."""
from __future__ import annotations

import argparse

from ..wad import WadFile


def add_wad_args(p: argparse.ArgumentParser, *, pwad_help: str = "additional PWAD to layer on top") -> None:
    """Add the standard ``wad`` positional and optional ``--pwad`` arguments."""
    p.add_argument("wad", help="path to base WAD file (IWAD or PWAD)")
    p.add_argument(
        "--pwad",
        dest="pwads",
        metavar="PATH",
        action="append",
        default=[],
        help=pwad_help + " (may be repeated)",
    )


def open_wad(args: argparse.Namespace) -> WadFile:
    """Open the WAD specified by *args*, layering any ``--pwad`` files on top."""
    pwads: list[str] = getattr(args, "pwads", []) or []
    return WadFile.open(args.wad, *pwads)
