"""wadcli complevel — detect and display compatibility level."""

import argparse
import json

from ...compat import CompLevel, check_downgrade, detect_complevel, detect_features
from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.add_argument(
        "--check",
        metavar="LEVEL",
        help="check if WAD can be downgraded to this level "
        "(vanilla, boom, mbf, mbf21, zdoom, udmf)",
    )
    p.set_defaults(func=run)


def _parse_level(name: str) -> CompLevel:
    mapping = {
        "vanilla": CompLevel.VANILLA,
        "limit-removing": CompLevel.LIMIT_REMOVING,
        "boom": CompLevel.BOOM,
        "mbf": CompLevel.MBF,
        "mbf21": CompLevel.MBF21,
        "zdoom": CompLevel.ZDOOM,
        "udmf": CompLevel.UDMF,
    }
    key = name.lower().strip()
    if key not in mapping:
        raise SystemExit(f"Unknown level: {name!r}. Valid: {', '.join(mapping)}")
    return mapping[key]


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        level = detect_complevel(wad)
        features = detect_features(wad)

        if args.check:
            target = _parse_level(args.check)
            issues = check_downgrade(wad, target)

            if args.json:
                print(
                    json.dumps(
                        {
                            "current": level.label,
                            "target": target.label,
                            "compatible": len(issues) == 0,
                            "issues": [
                                {"level": i.current_level.label, "message": i.message}
                                for i in issues
                            ],
                        },
                        indent=2,
                    )
                )
                return

            if not issues:
                print(f"WAD is compatible with {target.label}.")
            else:
                print(f"WAD requires {level.label}, cannot downgrade to {target.label}:")
                for issue in issues:
                    print(f"  [{issue.current_level.label}] {issue.message}")
            return

        if args.json:
            print(
                json.dumps(
                    {
                        "level": level.label,
                        "features": [
                            {"level": f.level.label, "reason": f.reason} for f in features
                        ],
                    },
                    indent=2,
                )
            )
            return

        print(f"Compatibility level: {level.label}")
        if features:
            print(f"\nFeatures detected ({len(features)}):")
            for f in features:
                print(f"  [{f.level.label}] {f.reason}")
        else:
            print("No features beyond vanilla Doom detected.")
