# wadlib

[![CI](https://github.com/rembish/wadlib/actions/workflows/ci.yml/badge.svg)](https://github.com/rembish/wadlib/actions/workflows/ci.yml)

Python 3.12+ library and CLI toolkit for reading, writing, and analysing
id Software WAD files — Doom, Doom II, Heretic, Hexen, Strife, and
source-port mods (ZDoom, GZDoom, PK3, UDMF).

**[Full documentation →](https://rembish.github.io/wadlib/)**

---

## Installation

```bash
pip install wadlib
```

For FUSE filesystem mounting:

```bash
pip install "wadlib[fuse]"
```

For development:

```bash
git clone https://github.com/rembish/wadlib
cd wadlib
make install   # creates .venv, installs with dev + release deps
```

---

## Quick start

```python
from wadlib import WadFile

# Open a single WAD
with WadFile("DOOM2.WAD") as wad:
    print(wad.wad_type)        # WadType.IWAD
    print(len(wad.maps))       # 32
    print(wad.maps[0])         # MAP01

# Layer a PWAD on top — PWAD lumps shadow base-WAD lumps by name
with WadFile.open("DOOM2.WAD", "SIGIL_II.WAD") as wad:
    for m in wad.maps:
        print(m, "—", len(m.things), "things")
```

```python
from wadlib import WadArchive

# Read
with WadArchive("DOOM2.WAD") as wad:
    print(wad.namelist())
    data = wad.read("PLAYPAL")

# Append — modify in place (last-wins semantics match Doom engine)
with WadArchive("mod.wad", "a") as wad:
    wad.replace("PLAYPAL", new_palette)
    wad.writestr("NEWLUMP", data)

# Write — create from scratch with namespace markers
with WadArchive("patch.wad", "w") as wad:
    wad.writemarker("F_START")
    wad.writestr("MYFLOOR", flat_bytes)
    wad.writemarker("F_END")
```

```bash
# CLI
wadcli --wad DOOM2.WAD info
wadcli --wad DOOM2.WAD list maps
wadcli --wad DOOM2.WAD export map MAP01 map01.png
wadcli --wad DOOM2.WAD export sound DSPISTOL pistol.wav
wadcli --wad DOOM2.WAD check
```

For the full API, CLI reference, and how-to guides see the
**[documentation site](https://rembish.github.io/wadlib/)**.

---

## Stability and coverage

| Area | Status | Notes |
|---|---|---|
| Classic WAD reading | **Stable** | All binary lumps: maps, textures, flats, sprites, sounds, music, palettes |
| WAD writing / round-trip | **Stable** | `WadWriter`, `WadArchive`; all binary types support `to_bytes()` |
| Map inspection | **Stable** | Vanilla + Hexen map lumps; UDMF full read/write; ZNODES compressed BSP |
| Textures / compositing | **Stable** | TEXTURE1/2, PNAMES, ZDoom TEXTURES text format; `TextureCompositor` |
| Audio | **Stable** | DMX, MUS → MIDI, OGG/MP3/MIDI detection; WAV ↔ DMX, MIDI ↔ MUS |
| CLI (`wadcli`) | **Stable** | Export, diff, check, list, render, complevel, convert |
| PK3 / ZIP support | **Beta** | Read, write, WAD↔PK3; PK3-embedded WAD maps |
| FUSE mount (`wadmount`) | **Beta** | Virtual WAD filesystem; OS/libfuse dependent |
| UDMF maps | **Beta** | Full parse/serialize; namespace-specific validation started |
| ZMAPINFO | **Beta** | Maps, episodes, clusters, defaultmap; round-trip serialiser |
| DECORATE | **Beta** | Actors, flags, inheritance, `#include`, `replaces`; no ZScript |
| ANIMDEFS | **Beta** | Parse; `AnimDef.resolve_frames()` maps numeric pic indices to lump names |
| Compatibility analysis | **Beta** | `detect_complevel`, `check_downgrade`, `convert_complevel` |
| LANGUAGE / SNDINFO / SNDSEQ | **Beta** | Parsed for metadata; no engine-runtime semantics |
| ZScript / ACS execution | **Not supported** | Out of scope |

---

## Supported games

| Game | IWAD | Notes |
|---|---|---|
| Doom / Ultimate Doom | `DOOM.WAD` | E1M1–E4M9 |
| Doom II | `DOOM2.WAD` | MAP01–MAP32 |
| Heretic | `HERETIC.WAD` | FONTA/FONTB, Heretic thing catalog |
| Hexen | `HEXEN.WAD` | Hexen map format, SNDSEQ, MAPINFO, ANIMDEFS |
| Strife | `STRIFE1.WAD` | All 262 thing types; DIALOGUE/SCRIPTxx conversations |
| Source-port PWADs | `.wad` / `.pk3` | ZMAPINFO, ANIMDEFS, DEHACKED custom things |

---

## Examples

The `examples/` directory contains runnable scripts for common workflows:

| File | Description |
|---|---|
| `01_inspect_wad.py` | Map list, asset counts, source-port lumps detected |
| `02_extract_assets.py` | Export sprites, flats, and wall textures as PNG |
| `03_build_pwad.py` | Build a minimal PWAD from scratch and round-trip validate |
| `04_pwad_stack.py` | Load an IWAD + PWADs via `ResourceResolver`, collision report |
| `05_audio_conversion.py` | Extract DMX → WAV, MUS → MIDI; import back |
| `06_texture_audit.py` | Find unused textures/flats, per-map breakdown |
| `07_diagnostics.py` | Structured `analyze()` report; compatibility downgrade check |
| `08_zdoom_mod_info.py` | ZMAPINFO, DECORATE actors, LANGUAGE strings |
| `09_wad_diff.py` | What a PWAD changes vs. the base — added, removed, changed lumps |
| `10_render_maps.py` | Render overhead map views as PNG with floor textures |

---

## Requirements

- Python 3.12+
- [Pillow](https://python-pillow.org/) >= 9.2
