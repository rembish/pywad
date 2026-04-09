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
git clone https://github.com/arembish/pywad
cd pywad
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
    opts = RenderOptions(show_floors=True, alpha=True)
    r = MapRenderer(m, wad=wad, options=opts)
    r.render()
    r.save("e6m1.png")
```

---

## `wadcli` — command-line tool

Every subcommand accepts `--pwad PATH` (repeatable) to layer additional
PWADs on top of the base WAD.

```
wadcli info <wad> [--pwad <pwad>...]
wadcli list lumps   <wad>
wadcli list maps    <wad>
wadcli list flats   <wad>
wadcli list sprites <wad>
wadcli list textures <wad>
wadcli list sounds  <wad>
wadcli list music   <wad>
wadcli list patches <wad>
wadcli list animations <wad>
wadcli export map       <wad> <MAP>  <out.png> [--floors] [--alpha] [--scale N] [--pwad ...]
wadcli export flat      <wad> <NAME> <out.png>
wadcli export sprite    <wad> <NAME> <out.png>
wadcli export texture   <wad> <NAME> <out.png>
wadcli export patch     <wad> <NAME> <out.png>
wadcli export sound     <wad> <NAME> <out.wav>
wadcli export music     <wad> <NAME> <out.mid>
wadcli export colormap  <wad> <out.png>
wadcli export animation <wad> <NAME> <out.gif>
wadcli export lump      <wad> <NAME> <out.bin>
wadcli export endoom    <wad> [out.ansi]
```

### Examples

```bash
# WAD summary
wadcli info wads/DOOM2.WAD

# Render SIGIL II map with floor textures (flats come from base DOOM2.WAD)
wadcli export map wads/DOOM2.WAD E6M1 e6m1.png --floors --pwad wads/SIGIL_II.WAD

# List all Scythe 2 maps with thing/linedef counts
wadcli list maps wads/scythe2.wad

# Export a sprite as PNG
wadcli export sprite wads/DOOM.WAD TROOA1 trooper.png

# Export music as MIDI
wadcli export music wads/DOOM.WAD D_E1M1 e1m1.mid

# Export an animated flat as a GIF
wadcli export animation wads/HEXEN.WAD FLTWAWA1 water.gif
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
