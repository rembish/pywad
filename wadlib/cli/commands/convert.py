"""wadcli convert — WAD<->pk3 and complevel conversion."""

import argparse
import sys


def configure(p: argparse.ArgumentParser) -> None:
    p.set_defaults(func=lambda _: p.print_help())
    subs = p.add_subparsers(dest="convert_cmd", metavar="<what>")

    # pk3
    pk3_p = subs.add_parser("pk3", help="convert WAD to pk3 (ZIP archive)")
    pk3_p.add_argument("output", nargs="?", help="output pk3 path (default: <wad>.pk3)")
    pk3_p.set_defaults(func=run_pk3)

    # wad
    wad_p = subs.add_parser("wad", help="convert pk3 to WAD")
    wad_p.add_argument("pk3", help="input pk3 file")
    wad_p.add_argument("output", nargs="?", help="output WAD path (default: <pk3>.wad)")
    wad_p.set_defaults(func=run_wad)

    # complevel
    cl_p = subs.add_parser("complevel", help="downgrade WAD to target compatibility level")
    cl_p.add_argument(
        "level",
        help="target level: vanilla, boom, mbf, mbf21, zdoom, udmf",
    )
    cl_p.add_argument("output", nargs="?", help="output WAD path")
    cl_p.set_defaults(func=run_complevel)


def run_pk3(args: argparse.Namespace) -> None:
    from ...pk3 import wad_to_pk3

    wad_path = getattr(args, "wad", None)
    if not wad_path:
        print("error: --wad is required for wadcli convert pk3", file=sys.stderr)
        sys.exit(1)

    output = args.output or wad_path.rsplit(".", 1)[0] + ".pk3"
    wad_to_pk3(wad_path, output)
    print(f"Converted {wad_path} → {output}")


def run_wad(args: argparse.Namespace) -> None:
    from ...pk3 import pk3_to_wad

    output = args.output or args.pk3.rsplit(".", 1)[0] + ".wad"
    pk3_to_wad(args.pk3, output)
    print(f"Converted {args.pk3} → {output}")


def run_complevel(args: argparse.Namespace) -> None:
    from ...compat import CompLevel, convert_complevel
    from ...wad import WadFile

    wad_path = getattr(args, "wad", None)
    if not wad_path:
        print("error: --wad is required for wadcli convert complevel", file=sys.stderr)
        sys.exit(1)

    mapping = {
        "vanilla": CompLevel.VANILLA,
        "limit-removing": CompLevel.LIMIT_REMOVING,
        "boom": CompLevel.BOOM,
        "mbf": CompLevel.MBF,
        "mbf21": CompLevel.MBF21,
        "zdoom": CompLevel.ZDOOM,
        "udmf": CompLevel.UDMF,
    }
    key = args.level.lower().strip()
    if key not in mapping:
        print(f"error: unknown level {args.level!r}. Valid: {', '.join(mapping)}", file=sys.stderr)
        sys.exit(1)

    target = mapping[key]
    output = args.output or wad_path.rsplit(".", 1)[0] + f"_{key}.wad"

    with WadFile(wad_path) as wad:
        result = convert_complevel(wad, target, output)

    print(f"Converted {wad_path} → {output} (target: {target.label})")
    if result.applied:
        print(f"\nApplied ({len(result.applied)}):")
        for a in result.applied:
            print(f"  + {a}")
    if result.skipped:
        print(f"\nSkipped ({len(result.skipped)}):")
        for s in result.skipped:
            print(f"  ! {s.description}")
