"""wadcli list sndseq — list SNDSEQ sound sequence definitions."""

import argparse
import json

from .._wad_args import open_wad


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output as JSON")
    p.add_argument(
        "--detail",
        action="store_true",
        help="show individual commands for each sequence",
    )
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> None:
    with open_wad(args) as wad:
        sndseq = wad.sndseq
        if sndseq is None:
            if args.json:
                print("[]")
            else:
                print("No SNDSEQ lump found.")
            return

        sequences = sndseq.sequences

        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": s.name,
                            "commands": [
                                {
                                    "command": c.command,
                                    "sound": c.sound,
                                    "tics": c.tics,
                                }
                                for c in s.commands
                            ],
                        }
                        for s in sequences
                    ],
                    indent=2,
                )
            )
            return

        if not sequences:
            print("No sound sequences defined in SNDSEQ.")
            return

        if args.detail:
            for seq in sequences:
                print(f":{seq.name}")
                for cmd in seq.commands:
                    parts = [f"  {cmd.command}"]
                    if cmd.sound:
                        parts.append(cmd.sound)
                    if cmd.tics is not None:
                        parts.append(str(cmd.tics))
                    print(" ".join(parts))
                print("  end")
                print()
        else:
            print(f"{'Name':<24} {'Commands':>8}")
            print("-" * 35)
            for seq in sequences:
                print(f"{seq.name:<24} {len(seq.commands):>8}")
            print(f"\n{len(sequences)} sequence(s) total.")
