#!/usr/bin/env python3
"""
05_audio_conversion.py — Extract and convert WAD audio (DMX sounds, MUS music).

Demonstrates both directions:
  WAD → standard:  DMX sound → WAV,  MUS music → MIDI
  standard → WAD:  WAV → DMX bytes,  MIDI → MUS bytes

Usage:
    python examples/05_audio_conversion.py
    python examples/05_audio_conversion.py wads/freedoom2.wad output/audio/
    python examples/05_audio_conversion.py wads/freedoom2.wad output/ --music --round-trip
"""

from __future__ import annotations

import argparse
from pathlib import Path

from wadlib import WadFile
from wadlib.lumps.mid2mus import midi_to_mus
from wadlib.lumps.sound import wav_to_dmx

WADS = Path(__file__).parent.parent / "wads"
DEFAULT_WAD = WADS / "freedoom2.wad"
DEFAULT_OUT = Path(__file__).parent / "output" / "audio"


def export_sounds(wad: WadFile, out_dir: Path) -> None:
    dest = out_dir / "sounds"
    dest.mkdir(parents=True, exist_ok=True)

    for name, sound in wad.sounds.items():
        wav_bytes = sound.to_wav()
        (dest / f"{name}.wav").write_bytes(wav_bytes)

    print(f"  Sounds: {len(wad.sounds)} WAV files → {dest}/")


def export_music(wad: WadFile, out_dir: Path) -> None:
    dest = out_dir / "music"
    dest.mkdir(parents=True, exist_ok=True)

    exported = 0
    for name, track in wad.music.items():
        try:
            midi_bytes = track.to_midi()
            (dest / f"{name}.mid").write_bytes(midi_bytes)
            exported += 1
        except Exception:
            # OGG/MP3 tracks don't have a to_midi() — skip them
            pass

    print(f"  Music : {exported} MIDI files → {dest}/")


def round_trip_demo(out_dir: Path) -> None:
    """
    Show how to import external audio back into WAD format.
    Takes the first exported WAV/MIDI and re-encodes it to DMX/MUS.
    """
    sounds_dir = out_dir / "sounds"
    music_dir = out_dir / "music"

    wav_files = list(sounds_dir.glob("*.wav")) if sounds_dir.exists() else []
    mid_files = list(music_dir.glob("*.mid")) if music_dir.exists() else []

    if wav_files:
        wav_path = wav_files[0]
        dmx_bytes = wav_to_dmx(wav_path.read_bytes())
        dmx_path = out_dir / f"{wav_path.stem}.dmx"
        dmx_path.write_bytes(dmx_bytes)
        print(f"  Re-encoded: {wav_path.name} → {dmx_path.name} ({len(dmx_bytes)} bytes)")

    if mid_files:
        mid_path = mid_files[0]
        mus_bytes = midi_to_mus(mid_path.read_bytes())
        mus_path = out_dir / f"{mid_path.stem}.mus"
        mus_path.write_bytes(mus_bytes)
        print(f"  Re-encoded: {mid_path.name} → {mus_path.name} ({len(mus_bytes)} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export WAD audio to standard formats")
    parser.add_argument("wad", nargs="?", default=str(DEFAULT_WAD))
    parser.add_argument("output", nargs="?", default=str(DEFAULT_OUT))
    parser.add_argument("--sounds", action="store_true", default=False)
    parser.add_argument("--music", action="store_true", default=False)
    parser.add_argument("--round-trip", action="store_true", default=False,
                        help="Re-encode one exported file back to WAD format")
    args = parser.parse_args()

    export_all = not (args.sounds or args.music)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    with WadFile(args.wad) as wad:
        print(f"Exporting audio from {args.wad}:")
        if export_all or args.sounds:
            export_sounds(wad, out)
        if export_all or args.music:
            export_music(wad, out)

    if args.round_trip:
        print("Round-trip re-encoding:")
        round_trip_demo(out)


if __name__ == "__main__":
    main()
