"""wadcli list language — list LANGUAGE lump string keys and values."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--locale",
        metavar="LOCALE",
        default=None,
        help='locale to display (e.g. "enu", "fra", "deu"); defaults to English (enu/default)',
    )
    p.add_argument(
        "--locales",
        action="store_true",
        help="list available locale names instead of showing strings",
    )
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        lang = wad.language
        if lang is None:
            if args.json:
                print("[]" if args.locales else "{}")
            else:
                print("No LANGUAGE lump found.")
            return

        if args.locales:
            locales = sorted(lang.all_locales.keys())
            if args.json:
                print(json.dumps(locales, indent=2))
            else:
                if not locales:
                    print("No locales defined.")
                else:
                    for loc in locales:
                        count = len(lang.all_locales[loc])
                        print(f"{loc:<12} ({count} strings)")
            return

        strings = lang.strings_for(args.locale) if args.locale else lang.strings

        if args.json:
            print(json.dumps(strings, indent=2, ensure_ascii=False))
            return

        if not strings:
            locale_label = args.locale or "enu/default"
            print(f"No strings found for locale '{locale_label}'.")
            return

        locale_label = args.locale or "enu"
        print(f"LANGUAGE strings [{locale_label}] — {len(strings)} entries")
        print("-" * 60)
        for key in sorted(strings):
            value = strings[key].replace("\n", "\\n")
            if len(value) > 60:
                value = value[:57] + "..."
            print(f"{key:<28} {value}")
