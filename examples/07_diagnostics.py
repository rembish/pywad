#!/usr/bin/env python3
"""
07_diagnostics.py — Run structured diagnostics and compatibility analysis.

analyze() checks: map reference integrity, missing textures/flats, PNAMES
bounds, resource collisions, and compatibility level detection. Suitable for
pre-release validation or CI gatekeeping.

Usage:
    python examples/07_diagnostics.py
    python examples/07_diagnostics.py wads/freedoom2.wad
    python examples/07_diagnostics.py wads/freedoom2.wad --compat
    python examples/07_diagnostics.py wads/freedoom2.wad --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wadlib import WadFile, analyze
from wadlib.compat import CompLevel, check_downgrade, detect_complevel
from wadlib.resolver import ResourceResolver

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"


def run_diagnostics(
    wad_path: str,
    pwad_path: str | None,
    show_compat: bool,
    as_json: bool,
) -> int:
    """Return exit code: 0 if clean, 1 if errors found."""
    extra = [pwad_path] if pwad_path else []

    wads = [WadFile(wad_path)] + [WadFile(p) for p in extra]
    try:
        source = (  # type: ignore[assignment]
            ResourceResolver.doom_load_order(*wads) if len(wads) > 1 else wads[0]
        )

        report = analyze(source)

        if as_json:
            json.dump(report.to_dict(), sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0 if report.is_clean else 1

        # --- Diagnostics report ---
        print(f"WAD: {wad_path}")
        if pwad_path:
            print(f"PWAD: {pwad_path}")
        print()

        if report.complevel:
            print(f"Compatibility level: {report.complevel.label}")
        if report.unsupported_features:
            print(f"Features detected  : {', '.join(report.unsupported_features)}")
        print()

        if not report.errors and not report.warnings:
            print("No errors found.")
        else:
            print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s):")

        for item in report.errors:
            print(f"  [ERROR  ] {item.context}: {item.message}")
        for item in report.warnings:
            print(f"  [WARNING] {item.context}: {item.message}")

        # --- Compatibility downgrade check ---
        if show_compat and len(wads) == 1:
            print()
            wad = wads[0]
            level = detect_complevel(wad)
            print(f"Detected compat level: {level.label}")

            for target in [CompLevel.VANILLA, CompLevel.BOOM]:
                if target < level:
                    issues = check_downgrade(wad, target)
                    if issues:
                        print(f"\nBlocking downgrade to {target.label}:")
                        for iss in issues[:5]:  # show first 5
                            print(f"  [{iss.current_level.label}] {iss.message}")
                        if len(issues) > 5:
                            print(f"  ... and {len(issues) - 5} more")
                    else:
                        print(f"\nDowngrade to {target.label}: no blocking issues.")

        return 0 if report.is_clean else 1

    finally:
        for w in wads:
            w.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run wadlib diagnostics")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("--pwad", metavar="PATH")
    parser.add_argument("--compat", action="store_true",
                        help="Check compatibility level downgrade feasibility")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    rc = run_diagnostics(args.wad, args.pwad, args.compat, args.as_json)
    sys.exit(rc)


if __name__ == "__main__":
    main()
