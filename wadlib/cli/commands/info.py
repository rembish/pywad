"""wadcli info — WAD header summary."""

import argparse

from ...wad import WadFile


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
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
        if mapinfo is not None:
            print(f"MAPINFO : {len(mapinfo.maps)} maps")
        else:
            print("MAPINFO : none")
        sndinfo = wad.sndinfo
        if sndinfo is not None:
            print(f"SNDINFO : {len(sndinfo.sounds)} sounds")
        else:
            print("SNDINFO : none")
