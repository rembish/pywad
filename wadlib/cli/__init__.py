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
    subs = parser.add_subparsers(dest="group", required=True, metavar="<command>")

    # info (top-level, no subgroup)
    info.configure(subs.add_parser("info", help="show WAD header and summary stats"))

    # list group
    list_p = subs.add_parser("list", help="list WAD contents")
    list_subs = list_p.add_subparsers(dest="list_cmd", required=True, metavar="<what>")
    list_maps.configure(list_subs.add_parser("maps", help="list maps with thing/linedef counts"))
    list_lumps.configure(list_subs.add_parser("lumps", help="list all directory entries"))
    list_textures.configure(
        list_subs.add_parser("textures", help="list composite texture names and dimensions")
    )
    list_flats.configure(list_subs.add_parser("flats", help="list floor/ceiling flat names"))
    list_patches.configure(list_subs.add_parser("patches", help="list patch names from PNAMES"))
    list_music.configure(list_subs.add_parser("music", help="list music lumps with sizes"))

    # export group
    export_p = subs.add_parser("export", help="export WAD contents to files")
    export_subs = export_p.add_subparsers(dest="export_cmd", required=True, metavar="<what>")
    export_map.configure(export_subs.add_parser("map", help="render a map to a PNG image"))
    export_music.configure(
        export_subs.add_parser(
            "music", help="export a music lump as MIDI (.mid) or raw MUS (--raw)"
        )
    )
    export_texture.configure(export_subs.add_parser("texture", help="render a wall texture to PNG"))
    export_flat.configure(export_subs.add_parser("flat", help="render a floor/ceiling flat to PNG"))
    export_patch.configure(export_subs.add_parser("patch", help="render a patch or sprite to PNG"))
    extract_lump.configure(export_subs.add_parser("lump", help="dump raw lump bytes to a file"))

    args = parser.parse_args()
    args.func(args)
