#!/usr/bin/env python3
"""
02_extract_assets.py — Export sprites, flats, and wall textures as PNG files.

Usage:
    python examples/02_extract_assets.py
    python examples/02_extract_assets.py wads/freedoom2.wad output/
    python examples/02_extract_assets.py wads/freedoom2.wad output/ --sprites --textures
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wadlib import WadFile
from wadlib.compositor import TextureCompositor

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"
DEFAULT_OUT = Path(__file__).parent / "output"


def export_sprites(wad: WadFile, out_dir: Path, palette: list) -> None:
    dest = out_dir / "sprites"
    dest.mkdir(parents=True, exist_ok=True)
    for name, sprite in wad.sprites.items():
        img = sprite.decode(palette)
        img.save(dest / f"{name}.png")
    print(f"  Sprites: {len(wad.sprites)} → {dest}/")


def export_flats(wad: WadFile, out_dir: Path, palette: list) -> None:
    dest = out_dir / "flats"
    dest.mkdir(parents=True, exist_ok=True)
    for name, flat in wad.flats.items():
        img = flat.decode(palette)
        img.save(dest / f"{name}.png")
    print(f"  Flats  : {len(wad.flats)} → {dest}/")


def export_textures(wad: WadFile, out_dir: Path) -> None:
    # Composite textures are assembled from patches at export time.
    # TextureCompositor reads TEXTURE1/2 + PNAMES + patches from the WAD.
    tex1 = wad.texture1
    tex2 = wad.texture2
    if tex1 is None:
        print("  Textures: none (no TEXTURE1 lump)")
        return

    dest = out_dir / "textures"
    dest.mkdir(parents=True, exist_ok=True)
    comp = TextureCompositor(wad)

    names = [t.name for t in tex1.textures]
    if tex2:
        names += [t.name for t in tex2.textures]

    exported = 0
    failed = 0
    for name in names:
        try:
            img = comp.compose(name)
            if img is None:
                failed += 1
            else:
                img.save(dest / f"{name}.png")
                exported += 1
        except Exception:
            # Some patches may be missing in PWADs — skip gracefully.
            failed += 1

    msg = f"  Textures: {exported} exported"
    if failed:
        msg += f", {failed} skipped (missing patches)"
    print(f"{msg} → {dest}/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export WAD assets to PNG")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUT))
    parser.add_argument("--sprites", action="store_true", default=False)
    parser.add_argument("--flats", action="store_true", default=False)
    parser.add_argument("--textures", action="store_true", default=False)
    args = parser.parse_args()

    # Default: export everything if no specific flag given
    export_all = not (args.sprites or args.flats or args.textures)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    with WadFile(args.wad) as wad:
        if wad.playpal is None:
            print("No PLAYPAL found — cannot decode paletted images.", file=sys.stderr)
            sys.exit(1)
        palette = wad.playpal.get_palette(0)

        print(f"Exporting from {args.wad}:")
        if export_all or args.sprites:
            export_sprites(wad, out, palette)
        if export_all or args.flats:
            export_flats(wad, out, palette)
        if export_all or args.textures:
            export_textures(wad, out)


if __name__ == "__main__":
    main()
