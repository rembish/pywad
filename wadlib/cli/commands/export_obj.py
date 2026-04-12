"""wadcli export obj — export a map as a Wavefront OBJ 3D mesh."""

import argparse
import sys

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("map", help="map name (e.g. MAP01, E1M1)")
    p.add_argument("output", nargs="?", help="output .obj path (default: <MAP>.obj)")
    p.add_argument("--scale", type=float, default=0.01, help="scale factor (default: 0.01)")
    p.add_argument("--materials", action="store_true", help="generate .mtl material file")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    from ...export3d import map_to_obj

    with open_wad(args) as wad:
        target = args.map.upper()
        m = next((m for m in wad.maps if m.name == target), None)
        if m is None:
            print(f"error: map {target!r} not found", file=sys.stderr)
            sys.exit(1)

        output = args.output or f"{target}.obj"

        if args.materials:
            result = map_to_obj(m, scale=args.scale, materials=True)
            assert isinstance(result, tuple)
            obj_text, mtl_text = result
            mtl_path = output.rsplit(".", 1)[0] + ".mtl"
            with open(output, "w") as f:
                f.write(obj_text)
            with open(mtl_path, "w") as f:
                f.write(mtl_text)
            print(f"Exported {target} -> {output} + {mtl_path}")
        else:
            result_str = map_to_obj(m, scale=args.scale)
            assert isinstance(result_str, str)
            with open(output, "w") as f:
                f.write(result_str)
            print(f"Exported {target} -> {output}")
