"""wadcli — command-line toolkit for Doom WAD files."""

import argparse

from .commands import (
    export_flat,
    export_map,
    export_music,
    export_patch,
    export_texture,
    extract_lump,  # registered as "export lump"
    info,
    list_flats,
    list_lumps,
    list_maps,
    list_music,
    list_patches,
    list_textures,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wadcli",
        description="Doom WAD file toolkit — inspect and export WAD contents.",
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    subs = parser.add_subparsers(dest="group", metavar="<command>")

    # info (top-level, no subgroup)
    info.configure(subs.add_parser("info", help="show WAD header and summary stats"))

    # list group
    list_p = subs.add_parser("list", help="list WAD contents")
    list_p.set_defaults(func=lambda _: list_p.print_help())
    list_subs = list_p.add_subparsers(dest="list_cmd", metavar="<what>")
    list_flats.configure(list_subs.add_parser("flats", help="list floor/ceiling flat names"))
    list_lumps.configure(list_subs.add_parser("lumps", help="list all directory entries"))
    list_maps.configure(list_subs.add_parser("maps", help="list maps with thing/linedef counts"))
    list_music.configure(list_subs.add_parser("music", help="list music lumps with sizes"))
    list_patches.configure(list_subs.add_parser("patches", help="list patch names from PNAMES"))
    list_textures.configure(
        list_subs.add_parser("textures", help="list composite texture names and dimensions")
    )

    # export group
    export_p = subs.add_parser("export", help="export WAD contents to files")
    export_p.set_defaults(func=lambda _: export_p.print_help())
    export_subs = export_p.add_subparsers(dest="export_cmd", metavar="<what>")
    export_flat.configure(export_subs.add_parser("flat", help="render a floor/ceiling flat to PNG"))
    extract_lump.configure(export_subs.add_parser("lump", help="dump raw lump bytes to a file"))
    export_map.configure(export_subs.add_parser("map", help="render a map to a PNG image"))
    export_music.configure(
        export_subs.add_parser(
            "music", help="export a music lump as MIDI (.mid) or raw MUS (--raw)"
        )
    )
    export_patch.configure(export_subs.add_parser("patch", help="render a patch or sprite to PNG"))
    export_texture.configure(export_subs.add_parser("texture", help="render a wall texture to PNG"))

    args = parser.parse_args()
    args.func(args)
