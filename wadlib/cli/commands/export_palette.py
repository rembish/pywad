"""wadcli export palette — render PLAYPAL as a colour swatch PNG."""

import argparse
import sys

from .._wad_args import open_wad

_SWATCH_SIZE = 24  # pixels per colour cell
_COLS = 16  # colours per row (256 / 16 = 16 rows per palette)


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "output",
        nargs="?",
        default=None,
        help="output PNG path (default: PLAYPAL.png)",
    )
    p.add_argument(
        "--palette",
        type=int,
        default=None,
        metavar="N",
        help="export only palette N instead of all 14 (0-indexed)",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from PIL import Image

    output: str = args.output or "PLAYPAL.png"
    with open_wad(args) as wad:
        if wad.playpal is None:
            print("No PLAYPAL lump found.", file=sys.stderr)
            sys.exit(1)

        playpal = wad.playpal
        n_palettes = len(playpal)

        if args.palette is not None:
            if args.palette < 0 or args.palette >= n_palettes:
                print(
                    f"Palette index {args.palette} out of range (0-{n_palettes - 1}).",
                    file=sys.stderr,
                )
                sys.exit(1)
            palette_indices = [args.palette]
        else:
            palette_indices = list(range(n_palettes))

        rows_per_palette = 256 // _COLS
        w_px = _COLS * _SWATCH_SIZE
        h_px = rows_per_palette * _SWATCH_SIZE * len(palette_indices)

        img = Image.new("RGB", (w_px, h_px))
        pixels = img.load()
        assert pixels is not None

        for pal_row, pal_idx in enumerate(palette_indices):
            palette = playpal.get_palette(pal_idx)
            y_base = pal_row * rows_per_palette * _SWATCH_SIZE
            for i, (r, g, b) in enumerate(palette):
                col = i % _COLS
                row = i // _COLS
                x0 = col * _SWATCH_SIZE
                y0 = y_base + row * _SWATCH_SIZE
                for dy in range(_SWATCH_SIZE):
                    for dx in range(_SWATCH_SIZE):
                        pixels[x0 + dx, y0 + dy] = (r, g, b)

        img.save(output)
        label = (
            f"palette {palette_indices[0]}"
            if len(palette_indices) == 1
            else f"{len(palette_indices)} palettes"
        )
        print(f"Saved {w_px}x{h_px} swatch ({label}) to {output}")
