"""wadcli export font — render a WAD font as a sprite-sheet PNG."""

import argparse
import sys

from .._wad_args import open_wad

_FONTS = ("stcfn", "fonta", "fontb")
_LABEL_H = 12  # pixels reserved below each glyph for the character label
_GAP = 2  # gap between cells


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "font",
        choices=_FONTS,
        help="font to export: stcfn (Doom HUD), fonta (Heretic large), fontb (Heretic small)",
    )
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (default: <FONT>.png)",
    )
    p.add_argument(
        "--palette", type=int, default=0, metavar="N", help="PLAYPAL palette index (default: 0)"
    )
    p.add_argument(
        "--cols",
        type=int,
        default=16,
        metavar="N",
        help="glyphs per row in sprite sheet (default: 16)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from PIL import Image, ImageDraw

    font_key: str = args.font.lower()
    output: str = args.output or f"{font_key.upper()}.png"

    with open_wad(args) as wad:
        glyphs = getattr(wad, font_key)  # dict[int, Picture]
        if not glyphs:
            print(f"No {font_key.upper()} glyphs found in WAD.", file=sys.stderr)
            sys.exit(1)
        if wad.playpal is None:
            print("WAD has no PLAYPAL lump.", file=sys.stderr)
            sys.exit(1)

        palette = wad.playpal.get_palette(args.palette)
        decoded = {ordinal: pic.decode(palette) for ordinal, pic in sorted(glyphs.items())}

        cols = max(1, args.cols)
        cell_w = max(img.width for img in decoded.values()) + _GAP
        cell_h = max(img.height for img in decoded.values()) + _LABEL_H + _GAP
        n = len(decoded)
        sheet_rows = (n + cols - 1) // cols

        sheet = Image.new("RGBA", (cols * cell_w, sheet_rows * cell_h), (0, 0, 0, 255))
        draw = ImageDraw.Draw(sheet)

        for i, (ordinal, glyph_img) in enumerate(decoded.items()):
            col = i % cols
            row = i // cols
            x = col * cell_w
            y = row * cell_h
            sheet.paste(glyph_img, (x, y), glyph_img)
            char = chr(ordinal) if 32 <= ordinal < 127 else f"\\x{ordinal:02x}"
            draw.text((x, y + cell_h - _LABEL_H), char, fill=(180, 180, 180, 255))

        sheet.save(output)
        w, h = sheet.size
        print(f"Saved {n}-glyph {w}x{h} sprite sheet to {output}")
