"""Shared helpers for WAD path CLI arguments."""

from __future__ import annotations

import argparse

from ..wad import WadFile


def add_wad_args(
    p: argparse.ArgumentParser, *, pwad_help: str = "additional PWAD to layer on top"
) -> None:
    """Add the standard ``wad`` positional and optional ``--pwad``/``--deh`` arguments."""
    p.add_argument("wad", help="path to base WAD file (IWAD or PWAD)")
    p.add_argument(
        "--pwad",
        dest="pwads",
        metavar="PATH",
        action="append",
        default=[],
        help=pwad_help + " (may be repeated)",
    )
    p.add_argument(
        "--deh",
        dest="deh",
        metavar="PATH",
        default=None,
        help="standalone .deh DeHackEd patch to apply (overrides embedded DEHACKED lump)",
    )


def open_wad(args: argparse.Namespace) -> WadFile:
    """Open the WAD specified by *args*, layering any ``--pwad`` files on top.

    If ``--deh`` was supplied the standalone DeHackEd file is loaded into
    the returned WAD as its ``dehacked`` property.
    """
    pwads: list[str] = getattr(args, "pwads", []) or []
    wad = WadFile.open(args.wad, *pwads)
    deh: str | None = getattr(args, "deh", None)
    if deh:
        wad.load_deh(deh)
    return wad
