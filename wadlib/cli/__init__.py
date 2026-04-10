"""wadcli — command-line toolkit for Doom WAD files."""

import argparse

from .commands import (
    diff,
    export_animation,
    export_colormap,
    export_endoom,
    export_flat,
    export_font,
    export_map,
    export_music,
    export_palette,
    export_patch,
    export_sound,
    export_sprite,
    export_texture,
    extract_lump,  # registered as "export lump"
    info,
    list_animations,
    list_flats,
    list_lumps,
    list_maps,
    list_music,
    list_patches,
    list_sounds,
    list_sprites,
    list_stats,
    list_textures,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wadcli",
        description="Doom WAD file toolkit — inspect and export WAD contents.",
    )
    parser.set_defaults(func=lambda _: parser.print_help())

    # Global WAD arguments — shared by all subcommands
    parser.add_argument("--wad", metavar="PATH", help="path to base WAD file (IWAD or PWAD)")
    parser.add_argument(
        "--pwad",
        dest="pwads",
        metavar="PATH",
        action="append",
        default=[],
        help="additional PWAD to layer on top (may be repeated)",
    )
    parser.add_argument(
        "--deh",
        metavar="PATH",
        default=None,
        help="standalone .deh DeHackEd patch to apply",
    )

    subs = parser.add_subparsers(dest="group", metavar="<command>")

    # diff (top-level, no subgroup)
    diff.configure(subs.add_parser("diff", help="compare two WADs and report differences"))

    # info (top-level, no subgroup)
    info.configure(subs.add_parser("info", help="show WAD header and summary stats"))

    # list group
    list_p = subs.add_parser("list", help="list WAD contents")
    list_p.set_defaults(func=lambda _: list_p.print_help())
    list_subs = list_p.add_subparsers(dest="list_cmd", metavar="<what>")
    list_animations.configure(
        list_subs.add_parser("animations", help="list ANIMDEFS flat/texture animation sequences")
    )
    list_flats.configure(list_subs.add_parser("flats", help="list floor/ceiling flat names"))
    list_lumps.configure(list_subs.add_parser("lumps", help="list all directory entries"))
    list_maps.configure(list_subs.add_parser("maps", help="list maps with thing/linedef counts"))
    list_music.configure(list_subs.add_parser("music", help="list music lumps with sizes"))
    list_patches.configure(list_subs.add_parser("patches", help="list patch names from PNAMES"))
    list_sounds.configure(list_subs.add_parser("sounds", help="list DMX sound lumps"))
    list_sprites.configure(
        list_subs.add_parser("sprites", help="list sprite lumps with dimensions")
    )
    list_stats.configure(list_subs.add_parser("stats", help="aggregate statistics across all maps"))
    list_textures.configure(
        list_subs.add_parser("textures", help="list composite texture names and dimensions")
    )

    # export group
    export_p = subs.add_parser("export", help="export WAD contents to files")
    export_p.set_defaults(func=lambda _: export_p.print_help())
    export_subs = export_p.add_subparsers(dest="export_cmd", metavar="<what>")
    export_animation.configure(
        export_subs.add_parser("animation", help="render an ANIMDEFS sequence as an animated GIF")
    )
    export_colormap.configure(
        export_subs.add_parser("colormap", help="render COLORMAP lump as a PNG grid")
    )
    export_endoom.configure(
        export_subs.add_parser("endoom", help="export ENDOOM lump as text or ANSI")
    )
    export_flat.configure(export_subs.add_parser("flat", help="render a floor/ceiling flat to PNG"))
    export_font.configure(
        export_subs.add_parser("font", help="render a WAD font as a sprite-sheet PNG")
    )
    extract_lump.configure(export_subs.add_parser("lump", help="dump raw lump bytes to a file"))
    export_map.configure(export_subs.add_parser("map", help="render a map to a PNG image"))
    export_music.configure(
        export_subs.add_parser(
            "music", help="export a music lump as MIDI (.mid) or raw MUS (--raw)"
        )
    )
    export_palette.configure(
        export_subs.add_parser("palette", help="render PLAYPAL as a colour swatch PNG")
    )
    export_patch.configure(export_subs.add_parser("patch", help="render a patch or sprite to PNG"))
    export_sound.configure(
        export_subs.add_parser("sound", help="export a DMX sound lump as WAV or raw (--raw)")
    )
    export_sprite.configure(export_subs.add_parser("sprite", help="render a sprite to PNG"))
    export_texture.configure(export_subs.add_parser("texture", help="render a wall texture to PNG"))

    args = parser.parse_args()
    args.func(args)
