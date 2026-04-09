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
