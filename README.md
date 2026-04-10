# wadlib

Python 3.12+ library and CLI toolkit for reading and analysing id Software
WAD files (Doom, Doom II, Heretic, Hexen, and derivative source-port mods).

---

## Installation

```bash
pip install wadlib          # library + wadcli command
```

For development:

```bash
git clone https://github.com/arembish/wadlib
cd wadlib
make install                # creates .venv, installs with dev deps
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

# Layer a PWAD on top (PWAD lumps shadow base-WAD lumps by name)
with WadFile.open("DOOM2.WAD", "SIGIL_II.WAD") as wad:
    for m in wad.maps:
        print(m, "—", len(m.things), "things")
```

---

## API overview

### `WadFile`

| Property / method | Description |
|---|---|
| `WadFile(path)` | Open a single WAD file |
| `WadFile.open(base, *pwads)` | Open a base WAD with zero or more PWADs layered on top |
| `wad.wad_type` | `WadType.IWAD` or `WadType.PWAD` |
| `wad.directory` | Raw list of `DirectoryEntry` objects |
| `wad.maps` | List of `BaseMapEntry` (PWAD-aware, PWADs override/extend base maps) |
| `wad.playpal` | `PlayPal` — 14 RGBA palettes |
| `wad.colormap` | `ColormapLump` — 34 light-level remapping tables |
| `wad.flats` | `dict[str, Flat]` — floor/ceiling 64×64 textures |
| `wad.sprites` | `dict[str, Picture]` — sprite frames |
| `wad.texture1` / `wad.texture2` | `TextureList` — composite wall textures |
| `wad.pnames` | `PNames` — patch name list used by textures |
| `wad.music` | `dict[str, Mus]` — MUS music lumps (detected by magic bytes) |
| `wad.sounds` | `dict[str, DmxSound]` — DMX digitised sound lumps |
| `wad.endoom` | `Endoom` — 80×25 ANSI exit screen |
| `wad.stcfn` | `dict[int, Picture]` — Doom HUD font, keyed by ASCII ordinal |
| `wad.fonta` / `wad.fontb` | `dict[int, Picture]` — Heretic large/small fonts |
| `wad.sndinfo` | `SndInfo` — ZDoom/Heretic sound name mappings |
| `wad.sndseq` | `SndSeqLump` — Hexen sound sequence scripts |
| `wad.mapinfo` | `MapInfoLump` — Hexen MAPINFO (numeric map IDs, titles) |
| `wad.zmapinfo` | `ZMapInfoLump` — ZDoom ZMAPINFO (string map names, music, sky) |
| `wad.animdefs` | `AnimDefsLump` — Hexen/ZDoom flat/texture animation sequences |
| `wad.dehacked` | `DehackedLump` — embedded DeHackEd patch (PAR times, version) |
| `wad.get_flat(name)` | Look up a flat by name (PWAD-aware) |
| `wad.get_picture(name)` | Decode any lump as a Doom picture |
| `wad.get_lump(name)` | Raw lump bytes by name |
| `wad.get_music(name)` | Look up a MUS lump by name |
| `wad.get_sound(name)` | Look up a DMX sound by name |
| `wad.get_sprite(name)` | Look up a sprite frame by name |

All properties are cached and PWAD-aware.

### Maps

```python
m = wad.maps[0]        # BaseMapEntry
m.things               # Things lump (list of Thing)
m.lines                # Lines / HexenLineDefs lump
m.vertices             # Vertices lump
m.sectors              # Sectors lump
m.segs                 # Segs lump
m.ssectors             # SubSectors lump
m.nodes                # Nodes lump (BSP tree)
m.sidedefs             # SideDefs lump
m.blockmap             # BlockMap lump
m.reject               # Reject table lump
```

### Textures

```python
from wadlib import WadFile
from wadlib.compositor import TextureCompositor

with WadFile("DOOM2.WAD") as wad:
    comp = TextureCompositor(wad)
    img = comp.render("BRICK7")          # PIL Image (8-bit palette)
    img = comp.render_rgba("BRICK7")     # RGBA
```

### Audio export

```python
sound = wad.get_sound("DSPISTOL")
sound.to_wav("pistol.wav")

music = wad.get_music("D_E1M1")
music.to_midi("e1m1.mid")
```

### Map rendering

```python
from wadlib.renderer import MapRenderer, RenderOptions

with WadFile.open("DOOM2.WAD", "SIGIL_II.WAD") as wad:
    m = next(m for m in wad.maps if str(m) == "E6M1")
    # Floor textures + transparent void + WAD sprites at thing positions
    opts = RenderOptions(show_floors=True, alpha=True, show_sprites=True)
    r = MapRenderer(m, wad=wad, options=opts)
    r.render()
    r.save("e6m1.png")
```

---

## `wadcli` — command-line tool

`--wad`, `--pwad`, and `--deh` are global options placed **before** the
subcommand, so you can keep the WAD path constant while varying commands:

```bash
wadcli --wad DOOM2.WAD list maps
wadcli --wad DOOM2.WAD --pwad SIGIL_II.WAD list maps
wadcli --wad DOOM2.WAD export map E6M1
```

Output file arguments on `export` subcommands are optional — a sensible
default filename is derived from the lump/map name when omitted.

```
wadcli [--wad PATH] [--pwad PATH]... [--deh PATH] <command> ...

wadcli info [--json]
wadcli list lumps      [--filter NAME] [--json]
wadcli list maps       [--json]
wadcli list flats      [--filter NAME] [--json]
wadcli list sprites    [--json]
wadcli list textures   [--filter NAME] [--json]
wadcli list sounds     [--json]
wadcli list music      [--json]
wadcli list patches    [--filter NAME] [--json]
wadcli list animations [--json]
wadcli export map       <MAP>  [out.png]  [--floors] [--alpha] [--scale N]
wadcli export flat      <NAME> [out.png]
wadcli export sprite    <NAME> [out.png]
wadcli export texture   <NAME> [out.png]
wadcli export patch     <NAME> [out.png]
wadcli export sound     <NAME> [out.wav]  [--raw]
wadcli export music     <NAME> [out.mid]  [--raw]
wadcli export colormap  [out.png]
wadcli export palette   [out.png]         [--palette N]
wadcli export font      <stcfn|fonta|fontb> [out.png]
wadcli export animation <NAME> [out.gif]
wadcli export lump      <NAME> [out.bin]
wadcli export endoom    [out.txt]         [--ansi]
```

### Examples

```bash
# WAD summary
wadcli --wad DOOM2.WAD info

# WAD summary as JSON (useful in shell pipelines)
wadcli --wad DOOM2.WAD info --json | jq .maps

# Render SIGIL II map with floor textures (flats come from base DOOM2.WAD)
wadcli --wad DOOM2.WAD --pwad SIGIL_II.WAD export map E6M1

# List all maps with thing/linedef counts
wadcli --wad scythe2.wad list maps

# Export a sprite as PNG — output defaults to POSSA1.png
wadcli --wad DOOM.WAD export sprite POSSA1

# Export music as MIDI — output defaults to D_E1M1.mid
wadcli --wad DOOM.WAD export music D_E1M1

# Export the full colour palette swatch
wadcli --wad DOOM.WAD export palette

# Export Doom's HUD font as a sprite sheet
wadcli --wad DOOM.WAD export font stcfn

# Export an animated flat as a GIF
wadcli --wad HEXEN.WAD export animation FLTWAWA1
```

---

## Supported games / formats

| Game | IWAD | Notes |
|---|---|---|
| Doom / Ultimate Doom | `DOOM.WAD` | Episode maps E1M1–E4M9 |
| Doom II | `DOOM2.WAD` | MAP01–MAP32 |
| Heretic | `HERETIC.WAD` | FONTA/FONTB fonts, Heretic thing types |
| Hexen | `HEXEN.WAD` | Hexen map/things format, SNDSEQ, MAPINFO, ANIMDEFS |
| Source-port PWADs | `.wad` | ZDoom ZMAPINFO, ANIMDEFS, DEHACKED PAR times |

---

## Requirements

- Python 3.12+
- [Pillow](https://python-pillow.org/) ≥ 9.2
