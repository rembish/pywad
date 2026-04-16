# wadlib

![CI](https://github.com/rembish/wadlib/actions/workflows/ci.yml/badge.svg)

Python 3.12+ library and CLI toolkit for reading, writing, and analysing
id Software WAD files — Doom, Doom II, Heretic, Hexen, Strife, and
source-port mods (ZDoom, GZDoom, PK3, UDMF).

---

## Installation

```bash
pip install wadlib
```

For FUSE filesystem mounting:

```bash
pip install "wadlib[fuse]"
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

### Archive interface (zipfile-style)

```python
from wadlib import WadArchive

# Read
with WadArchive("DOOM2.WAD") as wad:
    print(wad.namelist())
    data = wad.read("PLAYPAL")

# Append: modify in place
with WadArchive("mod.wad", "a") as wad:
    wad.replace("PLAYPAL", new_palette)
    wad.writestr("NEWLUMP", data)

# Write: create from scratch
with WadArchive("patch.wad", "w") as wad:
    wad.writemarker("F_START")
    wad.writestr("MYFLOOR", flat_bytes)
    wad.writemarker("F_END")
```

### Creating WADs from scratch

```python
from wadlib import WadWriter
from wadlib.enums import WadType
from wadlib.lumps.things import Thing, Flags
from wadlib.lumps.vertices import Vertex

writer = WadWriter(WadType.PWAD)
writer.add_map(
    "MAP01",
    things=[Thing(0, 0, 0, 1, Flags(7))],
    vertices=[Vertex(0, 0), Vertex(64, 0), Vertex(64, 64), Vertex(0, 64)],
)
writer.save("my_map.wad")
```

---

## CLI

```bash
wadcli --wad DOOM2.WAD info
wadcli --wad DOOM2.WAD list maps
wadcli --wad DOOM2.WAD list lumps
wadcli --wad DOOM2.WAD export flat FLOOR0_1 floor.png
wadcli --wad DOOM2.WAD export sound DSPISTOL pistol.wav
wadcli --wad DOOM2.WAD render MAP01 map01.png
wadcli --wad DOOM2.WAD check
```

Mount as a virtual filesystem (requires `wadlib[fuse]`):

```bash
wadmount DOOM2.WAD /mnt/doom2
ls /mnt/doom2/flats/    # *.png
ls /mnt/doom2/sounds/   # *.wav
fusermount -u /mnt/doom2
```

---

## What's supported

| Area | Status | Notes |
|---|---|---|
| WAD reading / writing | **Stable** | IWAD + PWAD, PWAD layering, round-trip |
| Maps (Doom / Doom II) | **Stable** | Things, linedefs, sidedefs, sectors, BSP |
| Maps (Hexen binary) | **Stable** | 20-byte things, 16-byte linedefs, ACS args |
| Maps (UDMF) | **Beta** | Namespace validation, cross-ref checks |
| Textures (TEXTURE1/2) | **Stable** | Composite wall textures, PNAMES |
| Textures (ZDoom TEXTURES) | **Beta** | Full round-trip, Hypothesis-fuzzed |
| Graphics (Doom picture) | **Stable** | Decode to PIL Image, encode from PIL Image |
| Flats (64x64 raw) | **Stable** | Decode, encode |
| Audio (DMX / MUS) | **Stable** | DMX → WAV, MUS → MIDI, and reverse |
| Audio (OGG / MP3 / MIDI) | **Stable** | Detection and passthrough |
| PK3 / ZIP archives | **Beta** | Namespace mapping, embedded WAD maps |
| DECORATE actors | **Beta** | Metadata, inheritance, includes |
| ZMAPINFO | **Beta** | Episodes, clusters, defaultmap |
| DEHACKED | **Beta** | Things, frames, weapons, ammo, sounds, cheats |
| ANIMDEFS | **Beta** | Parse + `resolve_frames()` |
| LANGUAGE | **Beta** | Locale sections, combined `[enu default]` headers |
| Compatibility levels | **Beta** | Vanilla → UDMF detection and auto-conversion |
| FUSE mount | **Beta** | Read-write virtual filesystem |
| ZScript / ACS | Not supported | Out of scope |

---

## Next steps

- [Guides](guides.md) — practical how-to recipes for common tasks
- [API Reference](api.md) — full public API surface
- [Game Reference](games.md) — game detection, thing catalogs, compat levels
- [Format Reference](formats.md) — binary format details for WAD internals
