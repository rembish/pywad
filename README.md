# wadlib

![CI](https://github.com/rembish/wadlib/actions/workflows/ci.yml/badge.svg)

Python 3.12+ library and CLI toolkit for reading, writing, and analysing
id Software WAD files (Doom, Doom II, Heretic, Hexen, Strife, and derivative
source-port mods).

---

## Installation

```bash
pip install wadlib          # library + wadcli command
```

For development:

```bash
git clone https://github.com/rembish/wadlib
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

### Archive interface (zipfile-style)

```python
from wadlib import WadArchive

# Read
with WadArchive("DOOM2.WAD") as wad:
    print(wad.namelist())          # ['PLAYPAL', 'COLORMAP', ...]
    data = wad.read("PLAYPAL")    # raw bytes

# Write
with WadArchive("patch.wad", "w") as wad:
    wad.writestr("DEHACKED", deh_bytes)
    wad.writestr("THINGS", things_data)  # validated automatically

# Append (read-modify-write)
with WadArchive("mod.wad", "a") as wad:
    wad.replace("PLAYPAL", new_palette)
    wad.writestr("NEWLUMP", data)

# Extract all lumps to disk
with WadArchive("DOOM2.WAD") as wad:
    wad.extractall("output/")
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

# Or round-trip an existing WAD
with WadFile("DOOM2.WAD") as wad:
    writer = WadWriter.from_wad(wad)
    writer.replace_lump("ENDOOM", custom_endoom)
    writer.save("modified.wad")
```

---

## API overview

### `WadFile` (low-level reader)

| Property / method | Description |
|---|---|
| `WadFile(path)` | Open a single WAD file |
| `WadFile.open(base, *pwads)` | Open a base WAD with zero or more PWADs layered on top |
| `wad.wad_type` | `WadType.IWAD` or `WadType.PWAD` |
| `wad.directory` | Raw list of `DirectoryEntry` objects |
| `wad.maps` | List of `BaseMapEntry` (PWAD-aware, PWADs override/extend base maps) |
| `wad.playpal` | `PlayPal` — 14 RGBA palettes |
| `wad.colormap` | `ColormapLump` — 34 light-level remapping tables |
| `wad.flats` | `dict[str, Flat]` — floor/ceiling 64x64 textures |
| `wad.sprites` | `dict[str, Picture]` — sprite frames |
| `wad.texture1` / `wad.texture2` | `TextureList` — composite wall textures |
| `wad.pnames` | `PNames` — patch name list used by textures |
| `wad.music` | `dict[str, Mus\|MidiLump\|OggLump\|Mp3Lump]` — music lumps |
| `wad.sounds` | `dict[str, DmxSound]` — DMX digitised sound lumps |
| `wad.endoom` | `Endoom` — 80x25 ANSI exit screen |
| `wad.stcfn` | `dict[int, Picture]` — Doom HUD font, keyed by ASCII ordinal |
| `wad.fonta` / `wad.fontb` | `dict[int, Picture]` — Heretic large/small fonts |
| `wad.sndinfo` | `SndInfo` — ZDoom/Heretic sound name mappings |
| `wad.sndseq` | `SndSeqLump` — Hexen sound sequence scripts |
| `wad.mapinfo` | `MapInfoLump` — Hexen MAPINFO (numeric map IDs, titles) |
| `wad.zmapinfo` | `ZMapInfoLump` — ZDoom ZMAPINFO (maps, episodes, clusters, defaultmap) |
| `wad.animdefs` | `AnimDefsLump` — Hexen/ZDoom flat/texture animation sequences |
| `wad.decorate` | `DecorateLump` — ZDoom actor definitions (name, doomednum, flags, properties, includes, replacements) |
| `wad.dehacked` | `DehackedLump` — embedded DeHackEd patch (PAR times, custom thing types) |

All properties are cached and PWAD-aware.

### `WadArchive` (unified archive interface)

Modelled after `zipfile.ZipFile` with modes `"r"`, `"w"`, and `"a"`.

| Method | Description |
|---|---|
| `WadArchive(path, mode, wad_type)` | Open/create a WAD archive |
| `wad.namelist()` | List of lump names in directory order |
| `wad.infolist()` | List of `LumpInfo` objects (name, size, index) |
| `wad.getinfo(name)` | `LumpInfo` for a named lump |
| `wad.read(name)` | Raw bytes of a lump |
| `wad.writestr(name, data)` | Write raw bytes as a lump (validated) |
| `wad.write(filename, arcname)` | Add a file from disk as a lump |
| `wad.writemarker(name)` | Add a zero-length marker lump |
| `wad.replace(name, data)` | Replace an existing lump |
| `wad.remove(name)` | Remove a lump |
| `wad.extract(name, path)` | Extract a lump to disk as `.lmp` |
| `wad.extractall(path)` | Extract all lumps to disk |
| `name in wad` | Membership test |
| `for info in wad` | Iteration over `LumpInfo` objects |

Write operations validate lump names and data formats by default.
Pass `validate=False` to bypass for non-standard lumps.

### `ResourceResolver` (unified cross-archive lookup)

Mix WAD and PK3 sources in priority order; the first source that has a name
wins.

```python
from wadlib.resolver import ResourceResolver

with WadFile("DOOM2.WAD") as wad, Pk3Archive("mod.pk3") as pk3:
    # WAD wins over pk3 when both have the same name
    r = ResourceResolver(wad, pk3)
    data = r.read("PLAYPAL")           # bytes | None
    src  = r.find_source("D_E1M1")    # LumpSource | None
    "PLAYPAL" in r                     # True

    # All matches for a name, highest-priority first
    refs = r.find_all("PLAYPAL")       # list[ResourceRef]
    ref  = refs[0]
    ref.name              # "PLAYPAL"
    ref.kind              # "wad-name" | "pk3-lump-name"
    ref.namespace         # "" (WAD) or "flats" / "sprites" / … (PK3)
    ref.size              # int — byte size
    ref.load_order_index  # 0-based position in source list
    ref.read_bytes()      # bytes

    # Shadowing and collisions
    hidden   = r.shadowed("PLAYPAL")   # refs behind the winner
    clashes  = r.collisions()          # dict[name, list[ResourceRef]]

    # Iterate all unique resources (winner per name)
    for ref in r.iter_resources():
        print(ref.name, ref.size)

    # Filter by PK3 namespace
    for ref in r.iter_resources(category="flats"):
        print(ref.name)                # only PK3 flat entries

# Doom load order: last patch wins (mirrors -iwad/-file semantics)
r = ResourceResolver.doom_load_order(base_wad, patch1, patch2)
```

| Method / field | Description |
|---|---|
| `ResourceResolver(*sources)` | Priority order; first source wins |
| `ResourceResolver.doom_load_order(base, *patches)` | Last patch wins |
| `read(name)` | Raw bytes of first match, or `None` |
| `find_source(name)` | `LumpSource` for first match, or `None` |
| `find_all(name)` | All `ResourceRef` objects, highest-priority first |
| `shadowed(name)` | Refs hidden behind the first match |
| `collisions()` | All names with more than one match |
| `iter_resources(category=None)` | One ref per unique name; optional PK3 category filter |
| `name in resolver` | Membership test |
| `ResourceRef.kind` | `"wad-name"` or `"pk3-lump-name"` |
| `ResourceRef.namespace` | PK3 category string, or `""` for WAD entries |
| `ResourceRef.size` | Byte size |
| `ResourceRef.load_order_index` | Source position (0 = highest priority) |

### Unified map assembly

Maps can now be assembled from WAD files, PK3 embedded WADs, and PK3 decomposed
map directories through a single API.

```python
# Maps from a single PK3 (embedded WAD or decomposed directory)
with Pk3Archive("mod.pk3") as pk3:
    maps = pk3.maps                  # dict[str, BaseMapEntry]
    m = maps["MAP01"]
    m.origin                         # "mod.pk3/maps/MAP01.wad" or "mod.pk3/maps/MAP01/"

# Maps from a WAD parsed in memory (e.g. extracted from a PK3)
with open("maps/MAP01.wad", "rb") as f:
    wad = WadFile.from_bytes(f.read())
    print(wad.maps)                  # list[BaseMapEntry] as usual

# All maps across a resolver, highest-priority source wins
with WadFile("DOOM2.WAD") as base, Pk3Archive("megawad.pk3") as mod:
    r = ResourceResolver(mod, base)  # mod overrides base
    maps = r.maps()                  # dict[str, BaseMapEntry]
    for name, m in maps.items():
        print(name, m.origin)        # shows which file contributed each map
```

| API | Description |
|---|---|
| `WadFile.from_bytes(data)` | Parse a WAD from raw bytes (no file needed) |
| `WadFile.all_wads` | PWAD stack, highest-priority first |
| `Pk3Archive.maps` | `dict[str, BaseMapEntry]` from embedded WADs + decomposed dirs |
| `ResourceResolver.maps()` | Merged maps across all sources, priority order |
| `BaseMapEntry.origin` | Source path that contributed this map entry |

### `WadWriter` (low-level writer)

| Method | Description |
|---|---|
| `WadWriter(wad_type)` | Create a new empty WAD |
| `WadWriter.from_wad(wad)` | Copy all lumps from an existing `WadFile` |
| `add_lump(name, data)` | Add a raw lump |
| `add_map(name, things=, vertices=, ...)` | Add a complete map with typed data |
| `add_flat(name, data)` | Add inside F_START/F_END namespace |
| `add_sprite(name, data)` | Add inside S_START/S_END namespace |
| `add_typed_lump(name, items)` | Serialize `to_bytes()` items into a lump |
| `replace_lump(name, data)` | Replace by name |
| `remove_lump(name)` | Remove by name |
| `save(filename)` | Write the WAD to disk |
| `to_bytes()` | Serialize to an in-memory byte string |

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

All map data types support `to_bytes()` for serialization back to WAD format.

### Format conversion

The main binary/media formats have explicit decode and encode helpers:

| Format | Decode (WAD -> standard) | Encode (standard -> WAD) |
|---|---|---|
| Pictures/Sprites | `Picture.decode(palette)` -> PIL Image | `encode_picture(image, palette)` |
| Flats | `Flat.decode(palette)` -> PIL Image | `encode_flat(image, palette)` |
| Sounds | `DmxSound.to_wav()` -> WAV bytes | `wav_to_dmx(wav)` / `encode_dmx(pcm, rate)` |
| Music (MUS) | `Mus.to_midi()` -> MIDI bytes | `midi_to_mus(midi_bytes)` |
| Palettes | `PlayPal.get_palette()` -> RGB tuples | `palette_to_bytes(palette)` |
| Colormaps | `ColormapLump.get(level)` -> 256 bytes | `build_colormap(palette)` |
| Textures (binary) | `TextureList.textures` -> TextureDef list | `texturelist_to_bytes(textures)` |
| Textures (ZDoom) | `TexturesLump.definitions` -> TexturesDef list | `serialize_textures(defs)` |
| Patch names | `PNames.names` -> string list | `pnames_to_bytes(names)` |

### Textures

```python
from wadlib import WadFile
from wadlib.compositor import TextureCompositor

with WadFile("DOOM2.WAD") as wad:
    comp = TextureCompositor(wad)
    img = comp.render("BRICK7")          # PIL Image (8-bit palette)
    img = comp.render_rgba("BRICK7")     # RGBA
```

### Audio

```python
# Export: DMX → WAV, MUS → MIDI
sound = wad.get_sound("DSPISTOL")
wav_bytes = sound.to_wav()

music = wad.get_music("D_E1M1")
midi_bytes = music.to_midi()

# Import: WAV → DMX, MIDI → MUS
from wadlib.lumps.sound import wav_to_dmx
dmx_bytes = wav_to_dmx(open("pistol.wav", "rb").read())

from wadlib.lumps.mid2mus import midi_to_mus
mus_bytes = midi_to_mus(open("e1m1.mid", "rb").read())
```

### Colormaps

```python
from wadlib.lumps.colormap import build_colormap, hex_to_rgb, rgb_to_hex

# Build a COLORMAP from a palette (34 light-level tables)
with WadFile("DOOM2.WAD") as wad:
    pal = wad.playpal.get_palette(0)
    colormap = build_colormap(pal)

# Custom invulnerability tint using hex colour
colormap = build_colormap(pal, invuln_tint="#FFD700")  # gold

# Hex colour utilities
r, g, b = hex_to_rgb("#FF8800")       # (255, 136, 0)
hex_str = rgb_to_hex(255, 136, 0)     # "#FF8800"
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

### ZMAPINFO — ZDoom map metadata

```python
zi = wad.zmapinfo   # ZMapInfoLump

# Map entries
for entry in zi.maps:
    print(entry.map_name, entry.title, entry.sky1, entry.music)
    print(entry.props)          # unknown keys captured here

entry = zi.get_map("MAP01")     # ZMapInfoEntry | None

# Episodes
for ep in zi.episodes:
    print(ep.map, ep.name or ep.name_lookup, ep.pic_name, ep.key)

# Clusters
for cl in zi.clusters:
    print(cl.cluster_num, cl.exittext, cl.music)

# defaultmap baseline (or None)
dm = zi.defaultmap              # ZMapInfoEntry | None
```

### UDMF — Universal Doom Map Format

```python
from wadlib.lumps.udmf import parse_udmf, UdmfParseError

# Permissive (default) — missing namespace is silently ignored
udmf_map = parse_udmf(textmap_bytes.decode())

# Strict — raises UdmfParseError if namespace declaration is absent
try:
    udmf_map = parse_udmf(text, strict=True)
except UdmfParseError as e:
    print(e)    # "no namespace declaration found in TEXTMAP"
```

### DECORATE — actor definitions

```python
d = wad.decorate                # DecorateLump

# All actors
for actor in d.actors:
    print(actor.name, actor.doomednum, actor.parent)

# Inherited properties/flags resolved
from wadlib import resolve_inheritance
resolved = resolve_inheritance(d.actors)

# #include paths (comment-stripped, in order)
print(d.includes)               # ["actors/monsters.dec", ...]

# Replacement map: replaced actor → replacing actor
print(d.replacements)           # {"ZombieMan": "MyZombie", ...}

# Editor numbers
print(d.editor_numbers)         # {9001: <DecorateActor ...>}
```

### Structured diagnostics

`analyze()` runs a suite of read-side checks across any combination of WAD and
PK3 sources and returns a JSON-serializable `ValidationReport`.

```python
from wadlib import analyze, WadFile
from wadlib.resolver import ResourceResolver

# Single WAD
with WadFile("doom2.wad") as wad:
    report = analyze(wad)
    print(report.complevel)           # CompLevel.VANILLA
    print(report.is_clean)            # True  (no errors)
    for item in report.warnings:
        print(item)                   # <WARNING [MISSING_TEXTURE] MAP01: ...>

# Full load order (PWAD overrides base)
with WadFile("doom2.wad") as base, WadFile("mod.wad") as mod:
    resolver = ResourceResolver.doom_load_order(base, mod)
    report = analyze(resolver)
    print(report.to_dict())           # JSON-safe dict

# Checks included:
# - Map reference integrity (vertex/sidedef/sector indices)
# - Missing textures and flats
# - PNAMES patch index bounds
# - Resource collisions across sources
# - Compatibility level detection
```

| Attribute | Type | Description |
|---|---|---|
| `report.errors` | `list[DiagnosticItem]` | Severity ERROR items |
| `report.warnings` | `list[DiagnosticItem]` | Severity WARNING items |
| `report.is_clean` | `bool` | No errors (warnings allowed) |
| `report.complevel` | `CompLevel \| None` | Minimum required compat level |
| `report.unsupported_features` | `list[str]` | Features that push up the compat level |
| `report.to_dict()` | `dict` | JSON-serializable summary |

### Writer-side validation

```python
from wadlib.validate import validate_lump, validate_name, validate_wad

# Name validation
issues = validate_name("TOOLONGNAME")  # error: too long

# Format validation
issues = validate_lump("THINGS", data)  # checks record size
issues = validate_lump("FLOOR1", data, is_flat=True)  # checks 4096 bytes

# Structural validation
issues = validate_wad(writer)  # namespace pairing, orphan lumps
```

### Compatibility levels

```python
from wadlib.compat import detect_complevel, check_downgrade, convert_complevel, CompLevel

with WadFile("mod.wad") as wad:
    level = detect_complevel(wad)           # CompLevel.BOOM
    issues = check_downgrade(wad, CompLevel.VANILLA)
    # Semi-auto downgrade (strips lumps, clears flags, converts UDMF)
    result = convert_complevel(wad, CompLevel.VANILLA, "vanilla_mod.wad")
```

### Texture usage scanning

```python
from wadlib.scanner import scan_usage, find_unused_textures

with WadFile("mymod.wad") as wad:
    usage = scan_usage(wad)
    print(f"{usage.total_unique_textures} textures used across {len(usage.per_map)} maps")
    unused = find_unused_textures(wad)
    print(f"{len(unused)} textures defined but never referenced")
```

---

## `wadcli` -- command-line tool

`--wad`, `--pwad`, and `--deh` are global options placed **before** the
subcommand, so you can keep the WAD path constant while varying commands:

```bash
wadcli --wad DOOM2.WAD list maps
wadcli --wad DOOM2.WAD --pwad SIGIL_II.WAD list maps
wadcli --wad DOOM2.WAD export map E6M1
```

Output file arguments on `export` subcommands are optional -- a sensible
default filename is derived from the lump/map name when omitted.

```
wadcli [--wad PATH] [--pwad PATH]... [--deh PATH] <command> ...

wadcli info [--json]
wadcli check [--json]
wadcli complevel [--json] [--check LEVEL]
wadcli diff <WAD_B> [--json]
wadcli list actors     [--json]
wadcli list animations [--json]
wadcli list flats      [--filter NAME] [--json]
wadcli list lumps      [--filter NAME] [--json]
wadcli list maps       [--json]
wadcli list music      [--json]
wadcli list patches    [--filter NAME] [--json]
wadcli list scripts    [--json]
wadcli list sounds     [--json]
wadcli list sprites    [--json]
wadcli list stats      [--json]
wadcli list textures   [--filter NAME] [--json]
wadcli export animation <NAME> [out.gif]
wadcli export colormap  [out.png]
wadcli export endoom    [out.txt]         [--ansi]
wadcli export flat      <NAME> [out.png]
wadcli export font      <stcfn|fonta|fontb> [out.png]
wadcli export lump      <NAME> [out.bin]
wadcli export map       <MAP>  [out.png]  [--floors] [--alpha] [--scale N]
wadcli export music     <NAME> [out.mid]  [--raw]
wadcli export obj       <MAP>  [out.obj]  [--scale N] [--materials]
wadcli export palette   [out.png]         [--palette N]
wadcli export patch     <NAME> [out.png]
wadcli export sound     <NAME> [out.wav]  [--raw]
wadcli export sprite    <NAME> [out.png]
wadcli export texture   <NAME> [out.png]
wadcli scan textures [--json] [--unused]
wadcli convert pk3      [out.pk3]
wadcli convert wad      <pk3> [out.wad]
wadcli convert complevel <LEVEL> [out.wad]
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

### Shell completion

Bash and Zsh completions are provided in the `completion/` directory:

```bash
# Bash — add to ~/.bashrc or copy to /etc/bash_completion.d/
source completion/wadcli.bash

# Zsh — copy to a directory in $fpath or source directly
source completion/wadcli.zsh
```

Completions cover all subcommands, options, file type filtering (`.wad`, `.deh`),
and context-aware argument hints (font names, export flags, etc.).

### FUSE mounting

Mount any WAD as a virtual directory with auto-format conversion:

```bash
pip install wadlib[fuse]     # install fusepy dependency
wadmount DOOM2.WAD /mnt/doom2

ls /mnt/doom2/flats/         # *.png (auto-converted from 64x64 raw)
ls /mnt/doom2/sounds/        # *.wav (auto-converted from DMX)
ls /mnt/doom2/music/         # *.mid (auto-converted from MUS)
ls /mnt/doom2/sprites/       # *.png (auto-converted from Doom picture)
ls /mnt/doom2/maps/MAP01/    # *.lmp (raw map data)
ls /mnt/doom2/lumps/         # *.lmp (raw access to everything)

# Write support — drop files in and they auto-convert back:
cp pistol.wav /mnt/doom2/sounds/DSPISTOL.wav   # WAV -> DMX
cp e1m1.mid /mnt/doom2/music/D_E1M1.mid        # MIDI -> MUS
cp floor.png /mnt/doom2/flats/MYFLOOR.png       # PNG -> flat

fusermount -u /mnt/doom2     # unmount (saves changes)
```

---

## Stability and coverage

"Stable" and "Beta" below describe **file-format API stability and test coverage** —
not game-engine or renderer completeness.  Engine runtime behavior (ACS/ZScript
execution, actor state machines, renderer semantics) is intentionally out of scope
for the entire library.

| Area | Status | Notes |
|---|---|---|
| Classic WAD reading | Stable | All binary lumps: maps, textures, flats, sprites, sounds, music, palettes, colormaps |
| WAD writing / round-trip | Stable | `WadWriter`, `WadArchive` write + validate; all binary types support `to_bytes()` |
| Map inspection | Stable | All vanilla + Hexen map lump types; UDMF full read/write; ZNODES (compressed BSP) |
| Textures / compositing | Stable | TEXTURE1/2 + PNAMES binary; ZDoom TEXTURES text format; `TextureCompositor` |
| Audio | Stable | DMX PCM, MUS → MIDI, OGG/MP3/MIDI; WAV ↔ DMX, MIDI ↔ MUS conversions |
| CLI (`wadcli`) | Stable | Export, diff, check, list, render, complevel |
| FUSE mount (`wadmount`) | Beta | Virtual WAD filesystem; OS/libfuse dependent; no CI mount integration tests |
| PK3 / ZIP support | Beta | Read, write, WAD↔PK3 conversion; PK3-embedded WAD maps; namespace mapping |
| UDMF maps | Beta | Full parse/serialize; `strict` mode; unknown props preserved; namespace-specific validation started (required fields, cross-refs, namespace-specific field warnings) |
| ZMAPINFO | Beta | Maps, episodes, clusters, defaultmap; `props` catch-all; round-trip serialiser |
| DECORATE | Beta | Actors, flags, states, inheritance; `#include` paths; `replaces` mapping; no ZScript |
| LANGUAGE / SNDINFO / SNDSEQ | Beta | Parsed for metadata; no engine-runtime semantics |
| Compatibility analysis | Beta | `detect_complevel`, `check_downgrade`, `convert_complevel`; structured `analyze()` report |
| ANIMDEFS / TEXTURES (ZDoom) | Beta | Parsed for metadata; `AnimDef.resolve_frames()` maps numeric pic indices to lump names given an ordered name list |
| Full ZScript | Not supported | Out of scope; would require a source-port runtime |
| ACS bytecode execution | Not supported | ACS `BEHAVIOR` lump is read as bytes only; no interpreter |

> **Stable** — API is production-quality; breaking changes would be semver-major.
> **Beta** — API is functional and tested but may evolve as more real-world WADs are tested.
> **Not supported** — explicitly excluded; contributions welcome.

---

## Supported games / formats

| Game | IWAD | Notes |
|---|---|---|
| Doom / Ultimate Doom | `DOOM.WAD` | Episode maps E1M1-E4M9 |
| Doom II | `DOOM2.WAD` | MAP01-MAP32 |
| Heretic | `HERETIC.WAD` | FONTA/FONTB fonts, Heretic thing types |
| Hexen | `HEXEN.WAD` | Hexen map/things format, SNDSEQ, MAPINFO, ANIMDEFS |
| Strife | `STRIFE1.WAD` | All 262 thing types, Strife-specific keys/monsters/NPCs |
| Source-port PWADs | `.wad` | ZDoom ZMAPINFO, ANIMDEFS, DEHACKED PAR times + custom things |

### Format / feature support matrix

| Format or feature | Support | Notes |
|---|---|---|
| Vanilla Doom / Doom II WAD | Full | IWAD + PWAD overlay, all binary map lumps, textures, sounds, music, sprites |
| Heretic | Full | FONTA/FONTB fonts, Heretic thing catalog |
| Hexen | Full | Hexen map/thing format, SNDSEQ, MAPINFO, ANIMDEFS, compiled ACS BEHAVIOR |
| Strife | Full | Thing type catalog (all 262 types); DIALOGUE lump parsed into `ConversationPage` / `ConversationChoice` dataclasses |
| Boom / MBF / MBF21 | Full | `line.generalized` decodes all 7 action categories; `sector.special_name`; MBF21 linedef flags |
| ZDoom / GZDoom WAD | Partial | ZMAPINFO (maps, episodes, clusters, defaultmap), SNDINFO, ANIMDEFS, LANGUAGE, DECORATE actors; no ZScript |
| UDMF maps | Partial | All blocks and properties parsed; hex integer literals and escaped strings handled; unknown fields preserved in `props`; `strict=True` raises `UdmfParseError` on missing namespace; namespace-specific validation: required fields (type/sector/textures), cross-reference integrity, z-height and arg0-arg4 namespace checks |
| PK3 (ZIP-based resource pack) | Partial | Read, write, WAD↔PK3 conversion; no full ZDoom resource overlay |
| DeHackEd | Partial | Things, frames, weapons, ammo, sounds, text replacements, PAR times, DEHEXTRA/MBF21 custom IDs; no cheat/state machine |
| DECORATE | Full | `wad.decorate` → `DecorateLump`; actors, doomednum, flags, properties, states; `resolve_inheritance()` fills inherited properties through parent chains; `.includes` lists `#include` paths; `.replacements` maps replaced → replacing actor |
| LANGUAGE | Full | `wad.language` → `LanguageLump`; multi-locale string lookup, `strings_for(locale)` |
| ZScript | None | Not parsed |

> **Full** = complete file-format read/write API — struct parsing, typed access, and round-trip serialization.
> **Partial** = useful but incomplete; known gaps noted above.
> Engine runtime behavior (renderer, state machines, codepointers, expression evaluation, ACS/ZScript execution) is out of scope for every entry in this table.

### Lump-type capability matrix

Legend: ✅ full  ⚠ partial  — not applicable / not present in this format

| Lump / feature | Vanilla | Heretic | Hexen | Strife | Boom/MBF21 | ZDoom | UDMF |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| THINGS (binary) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| LINEDEFS (binary) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SIDEDEFS / SEGS / SSECTORS / NODES | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SECTORS (binary) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| TEXTMAP (UDMF) | — | — | — | — | — | ✅ | ✅ |
| BLOCKMAP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| REJECT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| GL nodes (GL_VERT / GL_SEGS / GL_SSECT) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| BEHAVIOR / ACS bytecode | — | — | ✅ | — | — | ✅ | ✅ |
| DIALOGUE (Strife NPC conversation) | — | — | — | ✅ | — | — | — |
| Generalized linedefs | — | — | — | — | ✅ | — | — |
| PNAMES / TEXTURE1 / TEXTURE2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| TEXTURES (ZDoom format) | — | — | — | — | — | ✅ | ✅ |
| PLAYPAL / COLORMAP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DMX sound (PC speaker / OPL) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MUS music | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MP3 / OGG music | — | — | — | — | — | ✅ | ✅ |
| DEHACKED | — | — | — | — | ⚠ | ⚠ | — |
| DECORATE | — | — | — | — | — | ✅ | ✅ |
| LANGUAGE | — | — | — | — | — | ✅ | ✅ |
| SNDSEQ | — | ✅ | ✅ | — | — | ✅ | ✅ |
| SNDINFO | — | ✅ | — | — | — | ✅ | ✅ |
| MAPINFO (Hexen) | — | — | ✅ | — | — | — | — |
| ZMAPINFO (ZDoom) | — | — | — | — | — | ✅ | ✅ |
| ANIMDEFS | — | — | ✅ | — | — | ✅ | ✅ |
| ANIMATED / SWITCHES | ✅ | ✅ | — | — | ✅ | — | — |

### PWAD custom types (DEHEXTRA / MBF21)

PWADs that add new monsters or decorations beyond the base game's 137 types embed
their definitions in a `DEHACKED` lump using the `ID # = N` extension.  wadlib
reads these automatically -- custom things render with the correct colour on map
exports rather than appearing as blank grey dots.

| PWAD | Custom types detected |
|---|---|
| REKKR | 633, 654, 666, 668, 699, 750, ... (15 types) |
| Eviternity | 140-144, 4901-4902 (7 types) |

MBF-standard type 888 (Helper Dog, sprite `DOGS`) is also recognised without
requiring a DEHACKED declaration.

---

## Game type system

Thing type catalogs are organised under `wadlib.types` with per-game modules:

```python
from wadlib.types import detect_game, get_category, get_name, ThingCategory

game = detect_game(wad)              # GameType.DOOM / HERETIC / HEXEN / STRIFE
cat = get_category(thing.type, game) # ThingCategory.MONSTER / WEAPON / ...
name = get_name(thing.type, game)    # "Imp", "Fire Gargoyle", etc.
```

---

## Examples

The `examples/` directory contains runnable scripts for the most common
developer workflows:

| File | Description |
|---|---|
| `01_inspect_wad.py` | Map list, asset counts, source-port lumps detected |
| `02_extract_assets.py` | Export sprites, flats, and wall textures as PNG |
| `03_build_pwad.py` | Build a minimal PWAD from scratch and round-trip validate |
| `04_pwad_stack.py` | Load a base IWAD + PWADs via `ResourceResolver`, collision report |
| `05_audio_conversion.py` | Extract DMX sounds → WAV, MUS music → MIDI; import back |
| `06_texture_audit.py` | Find unused textures/flats, per-map breakdown, optional JSON |
| `07_diagnostics.py` | Structured `analyze()` report; compatibility downgrade check |
| `08_zdoom_mod_info.py` | ZMAPINFO, DECORATE actors/replacements/includes, LANGUAGE strings |
| `09_wad_diff.py` | What a PWAD changes vs. the base — added, removed, changed lumps |
| `10_render_maps.py` | Render overhead map views as PNG with floor textures |

Each script accepts `--help` for options.

---

## Requirements

- Python 3.12+
- [Pillow](https://python-pillow.org/) >= 9.2
