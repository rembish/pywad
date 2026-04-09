"""wadcli info — WAD header summary."""

import argparse

from .._wad_args import add_wad_args, open_wad


def configure(p: argparse.ArgumentParser) -> None:
    add_wad_args(p)
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        print(f"Type    : {wad.wad_type.name}")
        print(f"Lumps   : {wad.directory_size}")
        print(f"Maps    : {len(wad.maps)}")
        if wad.maps:
            names = "  ".join(str(m) for m in wad.maps[:8])
            suffix = f"  … (+{len(wad.maps) - 8})" if len(wad.maps) > 8 else ""
            print(f"          {names}{suffix}")
        print(f"Textures: {len(wad.texture1 or []) + len(wad.texture2 or [])}")
        print(f"Flats   : {len(wad.flats)}")
        pnames = wad.pnames
        print(f"Patches : {len(pnames) if pnames else 0}")
        playpal = wad.playpal
        print(f"Palettes: {len(playpal) if playpal else 0}")
        print(f"Sprites : {len(wad.sprites)}")
        print(f"Sounds  : {len(wad.sounds)}")
        print(f"Music   : {len(wad.music)}")
        print(f"Colormap: {'yes' if wad.colormap is not None else 'no'}")
        animdefs = wad.animdefs
        if animdefs is not None:
            print(f"ANIMDEFS: {len(animdefs.animations)} animations")
        else:
            print("ANIMDEFS: none")
        mapinfo = wad.mapinfo
        mi_count = len(mapinfo.maps) if mapinfo is not None else 0
        print(f"MAPINFO : {mi_count} maps" if mi_count else "MAPINFO : none")
        zmapinfo = wad.zmapinfo
        zmi_count = len(zmapinfo.maps) if zmapinfo is not None else 0
        print(f"ZMAPINFO: {zmi_count} maps" if zmi_count else "ZMAPINFO: none")
        sndinfo = wad.sndinfo
        if sndinfo is not None:
            print(f"SNDINFO : {len(sndinfo.sounds)} sounds")
        else:
            print("SNDINFO : none")
        fonts = []
        if wad.stcfn:
            fonts.append(f"STCFN ({len(wad.stcfn)} glyphs)")
        if wad.fonta:
            fonts.append(f"FONTA ({len(wad.fonta)} glyphs)")
        if wad.fontb:
            fonts.append(f"FONTB ({len(wad.fontb)} glyphs)")
        print(f"Fonts   : {', '.join(fonts) if fonts else 'none'}")
        deh = wad.dehacked
        if deh is not None:
            par_count = len(deh.par_times)
            ver = deh.doom_version
            ver_str = f" (Doom v{ver})" if ver else ""
            print(f"DEHACKED: yes{ver_str}{', ' + str(par_count) + ' par times' if par_count else ''}")
        else:
            print("DEHACKED: none")
