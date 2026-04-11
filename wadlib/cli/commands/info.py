"""wadcli info — WAD header summary."""

import argparse
import json

from ...compat import detect_complevel
from ...types import detect_game
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:  # pylint: disable=too-many-locals,too-many-statements
    with open_wad(args) as wad:
        pnames = wad.pnames
        playpal = wad.playpal
        animdefs = wad.animdefs
        mapinfo = wad.mapinfo
        zmapinfo = wad.zmapinfo
        sndinfo = wad.sndinfo
        deh = wad.dehacked

        game = detect_game(wad)
        complevel = detect_complevel(wad)

        # Count ACS scripts across all maps
        script_count = 0
        for m in wad.maps:
            if m.behavior is not None and hasattr(m.behavior, "scripts"):
                script_count += len(m.behavior.scripts)

        fonts = []
        if wad.stcfn:
            fonts.append(f"STCFN ({len(wad.stcfn)} glyphs)")
        if wad.fonta:
            fonts.append(f"FONTA ({len(wad.fonta)} glyphs)")
        if wad.fontb:
            fonts.append(f"FONTB ({len(wad.fontb)} glyphs)")

        if args.json:
            deh_info: dict[str, object] | None = None
            if deh is not None:
                deh_info = {
                    "doom_version": deh.doom_version,
                    "par_times": len(deh.par_times),
                }
            data: dict[str, object] = {
                "type": wad.wad_type.name,
                "game": game.value,
                "complevel": complevel.label,
                "lumps": wad.directory_size,
                "maps": [str(m) for m in wad.maps],
                "textures": len(wad.texture1 or []) + len(wad.texture2 or []),
                "flats": len(wad.flats),
                "patches": len(pnames) if pnames else 0,
                "palettes": len(playpal) if playpal else 0,
                "sprites": len(wad.sprites),
                "sounds": len(wad.sounds),
                "music": len(wad.music),
                "colormap": wad.colormap is not None,
                "animdefs": len(animdefs.animations) if animdefs else 0,
                "mapinfo": len(mapinfo.maps) if mapinfo else 0,
                "zmapinfo": len(zmapinfo.maps) if zmapinfo else 0,
                "sndinfo": len(sndinfo.sounds) if sndinfo else 0,
                "fonts": fonts,
                "scripts": script_count,
                "dehacked": deh_info,
            }
            print(json.dumps(data, indent=2))
            return

        print(f"Type    : {wad.wad_type.name}")
        print(f"Game    : {game.value.capitalize()}")
        print(f"CompLvl : {complevel.label}")
        print(f"Lumps   : {wad.directory_size}")
        print(f"Maps    : {len(wad.maps)}")
        if wad.maps:
            names = "  ".join(str(m) for m in wad.maps[:8])
            suffix = f"  … (+{len(wad.maps) - 8})" if len(wad.maps) > 8 else ""
            print(f"          {names}{suffix}")
        print(f"Textures: {len(wad.texture1 or []) + len(wad.texture2 or [])}")
        print(f"Flats   : {len(wad.flats)}")
        print(f"Patches : {len(pnames) if pnames else 0}")
        print(f"Palettes: {len(playpal) if playpal else 0}")
        print(f"Sprites : {len(wad.sprites)}")
        print(f"Sounds  : {len(wad.sounds)}")
        print(f"Music   : {len(wad.music)}")
        print(f"Colormap: {'yes' if wad.colormap is not None else 'no'}")
        if animdefs is not None:
            print(f"ANIMDEFS: {len(animdefs.animations)} animations")
        else:
            print("ANIMDEFS: none")
        mi_count = len(mapinfo.maps) if mapinfo is not None else 0
        print(f"MAPINFO : {mi_count} maps" if mi_count else "MAPINFO : none")
        zmi_count = len(zmapinfo.maps) if zmapinfo is not None else 0
        print(f"ZMAPINFO: {zmi_count} maps" if zmi_count else "ZMAPINFO: none")
        if sndinfo is not None:
            print(f"SNDINFO : {len(sndinfo.sounds)} sounds")
        else:
            print("SNDINFO : none")
        print(f"Scripts : {script_count}" if script_count else "Scripts : none")
        print(f"Fonts   : {', '.join(fonts) if fonts else 'none'}")
        if deh is not None:
            par_count = len(deh.par_times)
            ver = deh.doom_version
            ver_str = f" (Doom v{ver})" if ver else ""
            print(
                f"DEHACKED: yes{ver_str}{', ' + str(par_count) + ' par times' if par_count else ''}"
            )
        else:
            print("DEHACKED: none")
