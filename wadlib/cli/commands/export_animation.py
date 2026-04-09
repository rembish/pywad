"""wadcli export animation — render an ANIMDEFS sequence as an animated GIF."""
import argparse
import sys

from PIL import Image

from ...compositor import TextureCompositor
from ...lumps.flat import Flat
from ...wad import WadFile

_TICS_MS = 1000 / 35  # ms per tic at 35 Hz


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("wad", help="path to WAD file")
    p.add_argument("name", help="flat or texture animation name (e.g. x_001)")
    p.add_argument("output", help="output GIF path")
    p.add_argument(
        "--palette",
        type=int,
        default=0,
        metavar="N",
        help="PLAYPAL palette index (default: 0)",
    )
    p.set_defaults(func=run)


def _flat_directory_order(wad: WadFile) -> list[str]:
    """Return all flat names in WAD directory order (F_START..F_END), any size."""
    result: list[str] = []
    inside = False
    for entry in wad.directory:
        if entry.name in ("F_START", "FF_START"):
            inside = True
            continue
        if entry.name in ("F_END", "FF_END"):
            inside = False
            continue
        if inside and entry.size > 0:
            result.append(entry.name)
    return result


def run(args: argparse.Namespace) -> None:
    with WadFile(args.wad) as wad:
        if wad.animdefs is None:
            print("No ANIMDEFS lump found.", file=sys.stderr)
            sys.exit(1)

        # Find animation (case-insensitive)
        anim = next(
            (a for a in wad.animdefs.animations if a.name.lower() == args.name.lower()),
            None,
        )
        if anim is None:
            names = ", ".join(a.name for a in wad.animdefs.animations)
            print(
                f"Animation '{args.name}' not found.\nAvailable: {names}",
                file=sys.stderr,
            )
            sys.exit(1)

        palette = wad.playpal.get_palette(args.palette) if wad.playpal else None

        # Build ordered name list for the relevant kind.
        # For flats, use the full directory order (not wad.flats which only keeps 4096-byte entries).
        if anim.kind == "flat":
            ordered = _flat_directory_order(wad)
        else:
            ordered = []
            for tl in (wad.texture1, wad.texture2):
                if tl:
                    ordered.extend(t.name for t in tl.textures)

        base_name = anim.name.upper()
        try:
            base_idx = next(i for i, n in enumerate(ordered) if n.upper() == base_name)
        except StopIteration:
            kind_label = "flat" if anim.kind == "flat" else "texture"
            print(
                f"Base {kind_label} '{args.name}' not found in WAD.",
                file=sys.stderr,
            )
            sys.exit(1)

        compositor = TextureCompositor(wad, palette=palette) if anim.kind == "texture" else None

        # Build a lookup from name -> DirectoryEntry for flats (any size)
        flat_entries: dict[str, object] = {}
        if anim.kind == "flat":
            inside = False
            for entry in wad.directory:
                if entry.name in ("F_START", "FF_START"):
                    inside = True
                    continue
                if entry.name in ("F_END", "FF_END"):
                    inside = False
                    continue
                if inside and entry.size > 0:
                    flat_entries[entry.name] = entry

        frames: list[Image.Image] = []
        durations: list[int] = []

        for frame in anim.frames:
            idx = base_idx + frame.pic - 1
            if idx < 0 or idx >= len(ordered):
                print(f"Frame {frame.pic} out of range.", file=sys.stderr)
                sys.exit(1)
            lump_name = ordered[idx]

            if anim.kind == "flat":
                entry = flat_entries.get(lump_name)
                if entry is None:
                    print(f"Flat '{lump_name}' not found.", file=sys.stderr)
                    sys.exit(1)
                flat = Flat(entry)  # type: ignore[arg-type]
                img = flat.decode(palette).convert("RGBA")
            else:
                assert compositor is not None
                img = compositor.compose(lump_name)
                if img is None:
                    print(f"Texture '{lump_name}' not found.", file=sys.stderr)
                    sys.exit(1)

            frames.append(img)
            ms = int(frame.min_tics * _TICS_MS)
            durations.append(max(ms, 20))  # GIF minimum ~20ms

        if not frames:
            print("No frames to render.", file=sys.stderr)
            sys.exit(1)

        frames[0].save(
            args.output,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
        )
        w, h = frames[0].size
        print(f"Saved {len(frames)}-frame {w}x{h} GIF to {args.output}")
