"""wadcli — command-line toolkit for Doom WAD files.

Adding a new command
--------------------
1. Create ``wadlib/cli/commands/my_command.py`` with:
     def register(subparsers): ...   # adds subparser + sets func=run
     def run(args): ...              # implements the command
2. Import and append it to ``_COMMANDS`` below.
"""

import argparse

from .commands import (
    export_flat,
    export_map,
    export_patch,
    export_texture,
    extract_lump,
    info,
    list_flats,
    list_lumps,
    list_maps,
    list_patches,
    list_textures,
)

_COMMANDS = [
    info,
    list_lumps,
    list_maps,
    list_textures,
    list_flats,
    list_patches,
    export_map,
    export_texture,
    export_flat,
    export_patch,
    extract_lump,
]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wadcli",
        description="Doom WAD file toolkit — inspect and export WAD contents.",
    )
    subs = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    for cmd in _COMMANDS:
        cmd.register(subs)

    args = parser.parse_args()
    args.func(args)
