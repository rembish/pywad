# wadlib API Reference

Python 3.12+ library for reading, writing, and analysing id Software WAD files
(Doom, Doom II, Heretic, Hexen, Strife, and source-port mods).

```python
from wadlib import WadFile, WadWriter, WadArchive, LumpInfo
```

---

## WadFile (Reader)

Low-level WAD reader with PWAD layering support. All properties are cached
and PWAD-aware (PWAD lumps shadow base-WAD lumps by name). Use as a context
manager or call `close()` when done.

| Property / Method | Description |
|---|---|
| `WadFile(path)` | Open a single WAD file for reading |
| `WadFile.open(base, *pwads)` | Open a base WAD with zero or more PWADs layered on top |
| `close()` | Release all file handles (base + PWADs) |
| `wad_type` | `WadType.IWAD` or `WadType.PWAD` |
| `directory` | List of `DirectoryEntry` objects (raw lump directory) |
| `maps` | List of `BaseMapEntry` objects, sorted by map name |
| `maps_in_order` | List of `BaseMapEntry` objects in WAD directory order (no sorting) |
| `playpal` | `PlayPal` -- 14 RGBA palettes, or `None` |
| `colormap` | `ColormapLump` -- 34 light-level remapping tables, or `None` |
| `flats` | `dict[str, Flat]` -- floor/ceiling 64x64 textures between F_START/F_END |
| `sprites` | `dict[str, Picture]` -- sprite frames between S_START/S_END |
| `sounds` | `dict[str, DmxSound]` -- DMX digitised sound effects |
| `music` | `dict[str, Mus\|MidiLump\|OggLump\|Mp3Lump]` -- music lumps by name |
| `find_lump(name)` | Return highest-priority `DirectoryEntry` for *name*, or `None` |
| `get_lump(name)` | Return a `BaseLump` wrapper for *name*, or `None` |
| `get_flat(name)` | Return a named `Flat`, or `None` |
| `get_picture(name)` | Return a named lump decoded as `Picture`, or `None` |
| `get_sprite(name)` | Return a named sprite `Picture`, or `None` |
| `get_sound(name)` | Return a named `DmxSound`, or `None` |
| `get_music(name)` | Return a named music lump (MUS/MIDI/OGG/MP3), or `None` |
| `pnames` | `PNames` -- patch name list used by composite textures, or `None` |
| `texture1` | `TextureList` -- TEXTURE1 composite wall textures, or `None` |
| `texture2` | `TextureList` -- TEXTURE2 composite wall textures, or `None` |
| `endoom` | `Endoom` -- 80x25 ANSI exit screen, or `None` |
| `stcfn` | `dict[int, Picture]` -- Doom HUD font glyphs keyed by ASCII ordinal |
| `fonta` | `dict[int, Picture]` -- Heretic large font glyphs keyed by ASCII ordinal |
| `fontb` | `dict[int, Picture]` -- Heretic small font glyphs keyed by ASCII ordinal |
| `sndinfo` | `SndInfo` -- ZDoom/Heretic sound name mappings, or `None` |
| `sndseq` | `SndSeqLump` -- Hexen sound sequence scripts, or `None` |
| `mapinfo` | `MapInfoLump` -- Hexen MAPINFO (numeric map IDs, titles), or `None` |
| `zmapinfo` | `ZMapInfoLump` -- ZDoom ZMAPINFO (maps, episodes, clusters, defaultmap), or `None` |
| `animdefs` | `AnimDefsLump` -- Hexen/ZDoom animation sequences, or `None` |
| `dehacked` | `DehackedLump` -- embedded DeHackEd patch, or `None` |
| `load_deh(path)` | Load an external `.deh` file, overriding any embedded DEHACKED |
| `language` | `LanguageLump` -- ZDoom LANGUAGE string tables, or `None` |
| `decorate` | `DecorateLump` -- ZDoom DECORATE actor definitions with `.includes` and `.replacements` (PWAD-aware), or `None` |
| `load_pwad(path)` | Dynamically layer another PWAD on top, invalidating all caches |

---

## WadWriter

Low-level writer for creating and modifying WAD files from scratch. Supports
building complete maps from typed data classes and round-tripping existing WADs.

| Method / Property | Description |
|---|---|
| `WadWriter(wad_type=WadType.PWAD)` | Create a new empty WAD writer |
| `WadWriter.from_wad(wad)` | Copy all lumps from an existing `WadFile` into a new writer |
| `add_lump(name, data)` | Append a raw lump; returns its index |
| `add_marker(name)` | Append a zero-length marker lump; returns its index |
| `insert_lump(index, name, data)` | Insert a lump at *index*, shifting subsequent lumps right |
| `replace_lump(name, data)` | Replace the first lump named *name*; returns `True` if found |
| `remove_lump(name)` | Remove the first lump named *name*; returns `True` if found |
| `find_lump(name, start=0)` | Return index of first matching lump at or after *start*, or `-1` |
| `get_lump(name)` | Return raw bytes of the first matching lump, or `None` |
| `add_map(name, *, things=, vertices=, ...)` | Add a complete map marker and all sub-lumps from typed lists |
| `add_flat(name, data)` | Add a lump inside F_START/F_END (creates markers if needed) |
| `add_sprite(name, data)` | Add a lump inside S_START/S_END (creates markers if needed) |
| `add_patch(name, data)` | Add a lump inside P_START/P_END (creates markers if needed) |
| `add_typed_lump(name, items)` | Serialize `to_bytes()` items and add as a single lump |
| `to_bytes()` | Serialize the entire WAD to an in-memory byte string |
| `save(filename)` | Write the WAD to disk |
| `lumps` | The internal `list[WriterEntry]` of lump entries |
| `lump_names` | Ordered list of lump name strings |
| `lump_count` | Total number of lumps |

---

## WadArchive

Unified archive interface modelled after `zipfile.ZipFile`. Supports modes
`"r"` (read), `"w"` (create), and `"a"` (append / read-modify-write). Write
operations validate lump names and data by default; pass `validate=False` to
bypass.

| Method / Property | Description |
|---|---|
| `WadArchive(path, mode="r", wad_type=WadType.PWAD)` | Open or create a WAD archive in the given mode |
| `mode` | Current mode string (`"r"`, `"w"`, or `"a"`) |
| `wad_type` | `WadType.IWAD` or `WadType.PWAD` |
| `close()` | Flush pending writes (if writable) and release resources |
| `namelist()` | List of lump names in directory order |
| `infolist()` | List of `LumpInfo` objects (name, size, index) |
| `getinfo(name)` | Return `LumpInfo` for a named lump; raises `KeyError` if absent |
| `read(name)` | Return raw bytes of a named lump; raises `KeyError` if absent |
| `writestr(name, data, *, validate=True)` | Write raw bytes as a new lump (appended to directory) |
| `write(filename, arcname=None, *, validate=True)` | Add a file from disk as a lump (name derived from filename) |
| `writemarker(name)` | Add a zero-length marker lump |
| `replace(name, data, *, validate=True)` | Replace the first lump named *name*; returns `True` if found |
| `remove(name)` | Remove the first lump named *name*; returns `True` if found |
| `extract(name, path=".")` | Extract a single lump to disk as a `.lmp` file; returns file path |
| `extractall(path=".")` | Extract all non-empty lumps to disk; returns list of file paths |
| `name in wad` | Membership test (`__contains__`) |
| `for info in wad` | Iterate over `LumpInfo` objects |
| `len(wad)` | Total number of lumps |

### LumpInfo

Frozen dataclass with fields: `name: str`, `size: int`, `index: int`.

---

## Pk3Archive

Read and write pk3 (ZIP-based) archives used by GZDoom and other modern
source ports. Files are organised into directories (`flats/`, `sprites/`,
`sounds/`, `music/`, `maps/`, `patches/`, `lumps/`).

| Method / Property | Description |
|---|---|
| `Pk3Archive(file, mode="r")` | Open or create a pk3 archive (`"r"`, `"w"`, or `"a"`) |
| `namelist()` | List of file paths in the archive (excluding directories) |
| `infolist()` | List of `Pk3Entry` objects (path, size, compressed_size) |
| `read(path)` | Read a file from the archive by its full path |
| `writestr(path, data)` | Write data to a path inside the archive |
| `write(filename, arcname=None)` | Add a file from disk to the archive |
| `path in pk3` | Membership test |
| `len(pk3)` | Number of files |

### Conversion Functions

| Function | Description |
|---|---|
| `wad_to_pk3(wad_path, pk3_path)` | Convert a WAD file to a pk3 archive (lumps placed by namespace) |
| `pk3_to_wad(pk3_path, wad_path)` | Convert a pk3 archive back to a WAD file |

```python
from wadlib.pk3 import Pk3Archive, wad_to_pk3, pk3_to_wad
```

---

## Format Encoders

Functions for converting between standard formats (PNG, WAV, MIDI) and
WAD-native binary formats. Importable from their respective lump modules.

| Function | Module | Description |
|---|---|---|
| `encode_picture(image, palette)` | `wadlib.lumps.picture` | Encode a PIL Image to Doom picture format bytes |
| `encode_flat(image, palette)` | `wadlib.lumps.flat` | Encode a PIL Image to 4096-byte raw flat format |
| `encode_dmx(pcm_samples, rate=11025)` | `wadlib.lumps.sound` | Encode raw 8-bit PCM to DMX sound lump bytes |
| `wav_to_dmx(wav_data)` | `wadlib.lumps.sound` | Convert WAV file bytes to DMX sound lump bytes |
| `midi_to_mus(midi_data)` | `wadlib.lumps.mid2mus` | Convert Standard MIDI bytes to MUS format bytes |
| `build_colormap(palette, invuln_tint=None)` | `wadlib.lumps.colormap` | Build a 34-table COLORMAP from a palette |
| `hex_to_rgb(color)` | `wadlib.lumps.colormap` | Parse `"#RRGGBB"` or `"#RGB"` to `(r, g, b)` tuple |
| `rgb_to_hex(r, g, b)` | `wadlib.lumps.colormap` | Convert `(r, g, b)` to `"#RRGGBB"` hex string |
| `palette_to_bytes(palette)` | `wadlib.lumps.playpal` | Serialize 256 RGB tuples to 768-byte PLAYPAL data |
| `pnames_to_bytes(names)` | `wadlib.lumps.textures` | Serialize a list of patch names to PNAMES lump bytes |
| `texturelist_to_bytes(textures)` | `wadlib.lumps.textures` | Serialize `TextureDef` list to TEXTURE1/2 lump bytes |
| `animated_to_bytes(entries)` | `wadlib.lumps.animated` | Serialize `AnimatedEntry` list to Boom ANIMATED lump bytes |
| `switches_to_bytes(entries)` | `wadlib.lumps.animated` | Serialize `SwitchEntry` list to Boom SWITCHES lump bytes |
| `parse_textures(text)` | `wadlib.lumps.texturex` | Parse ZDoom TEXTURES lump text into `TexturesDef` list |
| `serialize_textures(defs)` | `wadlib.lumps.texturex` | Serialize `TexturesDef` list to ZDoom TEXTURES lump text |

---

## Validation

Validators for lump names, lump data, and whole-WAD structural integrity.
Used automatically by `WadArchive` on write; also usable standalone.

```python
from wadlib.validate import validate_name, validate_lump, validate_wad
from wadlib.validate import InvalidLumpError, Severity, ValidationIssue
```

| Function / Class | Description |
|---|---|
| `validate_name(name)` | Check a lump name for length, charset, and case; returns `list[ValidationIssue]` |
| `validate_lump(name, data, *, hexen=False, is_flat=False, is_picture=False)` | Check lump data against known format rules; returns `list[ValidationIssue]` |
| `validate_wad(writer)` | Check structural integrity of a `WadWriter` (namespaces, map ordering); returns `list[ValidationIssue]` |
| `InvalidLumpError` | Exception raised on write when validation finds errors; has `.issues` list |
| `Severity` | Enum with values `ERROR` and `WARNING` |
| `ValidationIssue` | Frozen dataclass with fields: `severity: Severity`, `lump: str`, `message: str` |

---

## Compatibility

Detect, compare, and convert between Doom source-port compatibility levels.

```python
from wadlib.compat import (
    CompLevel, detect_complevel, detect_features,
    check_downgrade, check_upgrade, plan_downgrade, convert_complevel,
)
```

| Function / Class | Description |
|---|---|
| `CompLevel` | IntEnum: `VANILLA`, `LIMIT_REMOVING`, `BOOM`, `MBF`, `MBF21`, `ZDOOM`, `UDMF` (ordered strictest to most permissive) |
| `detect_complevel(wad)` | Return the minimum `CompLevel` required by a WAD |
| `detect_features(wad)` | Return a list of `CompLevelFeature` objects found in the WAD |
| `check_downgrade(wad, target)` | Return `list[DowngradeIssue]` preventing downgrade to *target* level |
| `check_upgrade(wad, target)` | Return a list of feature description strings available at *target* |
| `plan_downgrade(wad, target)` | Return `list[ConvertAction]` needed to reach *target* (with `auto` and `lossy` flags) |
| `convert_complevel(wad, target, output_path)` | Apply auto-convertible actions and save result; returns `ConvertResult` |

---

## Boom / MBF21

Generalized linedef decoder and extended sector/linedef metadata for
Boom-compatible WADs.

```python
from wadlib.lumps.boom import (
    GeneralizedCategory, GeneralizedTrigger, GeneralizedSpeed,
    GeneralizedLinedef, decode_generalized,
    DOOM_SECTOR_SPECIALS, MBF21_LINEDEF_FLAGS,
)
```

| Name | Description |
|---|---|
| `GeneralizedCategory` | IntEnum: `CRUSHER`, `STAIR`, `LIFT`, `LOCKED_DOOR`, `DOOR`, `CEILING`, `FLOOR` -- lower bound of each category's `special_type` range |
| `GeneralizedTrigger` | IntEnum: `W1`, `WR`, `S1`, `SR`, `G1`, `GR`, `P1`, `PR` -- bits 0-2 of `special_type` |
| `GeneralizedSpeed` | IntEnum: `SLOW`, `NORMAL`, `FAST`, `TURBO` -- bits 3-4 of `special_type` |
| `GeneralizedLinedef` | Frozen dataclass: `category`, `trigger`, `speed`, `subtype` |
| `decode_generalized(special_type)` | Return `GeneralizedLinedef` when `special_type >= 0x2F80`, else `None` |
| `DOOM_SECTOR_SPECIALS` | `dict[int, str]` mapping vanilla sector special numbers 0-17 to names |
| `MBF21_LINEDEF_FLAGS` | `dict[int, str]` mapping MBF21 linedef flag bits (`0x0200`/`0x0400`/`0x0800`) to names |

These are also available through the map data classes:

- `LineDefinition.generalized` -- decoded `GeneralizedLinedef | None` for the linedef's `special_type`
- `Sector.special_name` -- human-readable name for the sector's `special` field

---

## LANGUAGE

ZDoom string localisation tables. The lump is divided into locale sections
(`[enu]`, `[default]`, `[fra]`, etc.); combined headers like `[enu default]`
expand to both locales.

```python
from wadlib.lumps.language import LanguageLump

# via WadFile:
with WadFile("mod.wad") as wad:
    lang = wad.language
    if lang:
        # All strings merged from [enu] + [default] sections
        print(lang.lookup("GOTSTUFFMSG"))          # "You got some stuff!"
        # Per-locale access
        all_locs = lang.all_locales                # dict[str, dict[str, str]]
        french = lang.strings_for("fra")           # dict[str, str] or {}
        # Locale-specific lookup with fallback
        val = lang.lookup("GOTSTUFFMSG", locale="fra")
```

| Property / Method | Description |
|---|---|
| `all_locales` | `dict[str, dict[str, str]]` -- all locale sections, keyed by lowercase locale name |
| `strings` | `dict[str, str]` -- merged `[enu]` + `[default]` strings |
| `strings_for(locale)` | Return `dict[str, str]` for the given locale name, or `{}` if absent |
| `lookup(key, default="", locale=None)` | Return the string for *key* (uppercased); uses `strings` unless *locale* is given |
| `serialize()` | Re-encode the lump to bytes |

---

## ZMAPINFO

ZDoom ZMAPINFO lump — brace-delimited map metadata blocks.

```python
from wadlib.lumps.zmapinfo import ZMapInfoLump, ZMapInfoEntry, ZMapInfoEpisode, ZMapInfoCluster

with WadFile("mod.wad") as wad:
    zi = wad.zmapinfo
    if zi:
        for entry in zi.maps:
            print(entry.map_name, entry.title, entry.sky1, entry.music)
            print(entry.props)          # unknown keys captured here
        for ep in zi.episodes:
            print(ep.map, ep.name or ep.name_lookup, ep.pic_name)
        for cl in zi.clusters:
            print(cl.cluster_num, cl.exittext, cl.music)
        dm = zi.defaultmap             # ZMapInfoEntry | None
```

| Class / Property | Description |
|---|---|
| `ZMapInfoLump` | Parsed ZMAPINFO lump |
| `ZMapInfoLump.maps` | `list[ZMapInfoEntry]` — all map blocks |
| `ZMapInfoLump.episodes` | `list[ZMapInfoEpisode]` — all episode blocks |
| `ZMapInfoLump.clusters` | `list[ZMapInfoCluster]` — all cluster blocks |
| `ZMapInfoLump.defaultmap` | `ZMapInfoEntry \| None` — baseline for all maps |
| `ZMapInfoLump.get_map(name)` | Return entry by map name (case-insensitive), or `None` |
| `ZMapInfoEntry` | Dataclass: `map_name`, `title`, `title_lookup`, `levelnum`, `next`, `secretnext`, `sky1`, `music`, `titlepatch`, `cluster`, `par`, `props` (catch-all dict) |
| `ZMapInfoEpisode` | Dataclass: `map`, `name`, `name_lookup`, `pic_name`, `key`, `no_skill_menu` |
| `ZMapInfoCluster` | Dataclass: `cluster_num`, `exittext`, `entertext`, `exittextislump`, `entertextislump`, `music`, `flat` |
| `serialize_zmapinfo(entries)` | Serialize a list of `ZMapInfoEntry` back to ZMAPINFO text |

---

## DECORATE

ZDoom actor definitions. Parses `DoomEdNum`, `Radius`, `Height`, and `States`
blocks from DECORATE text.

```python
from wadlib.lumps.decorate import DecorateLump, DecorateActor

# via WadFile (PWAD-aware):
with WadFile.open("DOOM2.WAD", "mod.wad") as wad:
    dec = wad.decorate
    if dec:
        for actor in dec.actors:
            print(f"{actor.name}  ednum={actor.doomednum}")
        # #include paths in declaration order (comments stripped)
        print(dec.includes)        # ["actors/monsters.dec", ...]
        # Actors that replace a base game actor
        print(dec.replacements)    # {"ZombieMan": "MyZombie", ...}
```

| Class / Property | Description |
|---|---|
| `DecorateLump` | Parsed DECORATE lump |
| `DecorateLump.actors` | `list[DecorateActor]` — all actor definitions |
| `DecorateLump.editor_numbers` | `dict[int, DecorateActor]` — actors with a DoomEdNum |
| `DecorateLump.includes` | `list[str]` — `#include` file paths in declaration order |
| `DecorateLump.replacements` | `dict[str, str]` — maps replaced actor name → replacing actor name |
| `DecorateActor` | Dataclass with fields: `name`, `parent`, `doomednum`, `replaces`, `properties`, `flags`, `antiflags`, `states`; computed properties `health`, `radius`, `height`, `speed`, `is_monster`, `is_item` |
| `parse_decorate(text)` | Parse raw DECORATE text into a list of `DecorateActor` objects |
| `resolve_inheritance(actors)` | Fill inherited properties, flags, states, and doomednum through parent chains |

---

## Scanner

Scan maps for texture, flat, and thing-type usage. Useful for finding unused
assets or auditing resource dependencies.

```python
from wadlib.scanner import scan_usage, find_unused_textures, find_unused_flats
```

| Function / Class | Description |
|---|---|
| `scan_usage(wad)` | Scan all maps and return an aggregated `UsageReport` |
| `find_unused_textures(wad)` | Return `set[str]` of texture names defined in TEXTURE1/2 but never referenced |
| `find_unused_flats(wad)` | Return `set[str]` of flat names in F_START/F_END but never referenced |
| `UsageReport` | Dataclass with fields: `textures`, `flats`, `thing_types` (all `set`), `per_map` dict, and `total_unique_*` properties |
| `MapUsage` | Dataclass with fields: `name`, `textures`, `flats`, `thing_types`, `thing_count`, `linedef_count`, `sector_count` |

---

## Type System

Game-aware thing type catalogs providing names, categories, and sprite data
for Doom, Heretic, Hexen, and Strife. Supports DEHACKED custom thing types.

```python
from wadlib.types import (
    GameType, ThingCategory, detect_game,
    get_name, get_category, get_sprite_prefix, get_invisible_types,
)
```

| Function / Class | Description |
|---|---|
| `GameType` | Enum: `DOOM`, `HERETIC`, `HEXEN`, `STRIFE` |
| `ThingCategory` | Enum: `PLAYER`, `MONSTER`, `WEAPON`, `AMMO`, `HEALTH`, `ARMOR`, `KEY`, `POWERUP`, `DECORATION`, `UNKNOWN` |
| `detect_game(wad)` | Inspect a WAD and return the most likely `GameType` |
| `get_name(type_id, game, deh=None)` | Return the human-readable name for a thing type (e.g. `"Imp"`) |
| `get_category(type_id, game, deh=None)` | Return the `ThingCategory` for a thing type |
| `get_sprite_prefix(type_id, game)` | Return the 4-char sprite prefix (e.g. `"TROO"`) or `None` |
| `get_invisible_types(game)` | Return `frozenset[int]` of thing types with no visual representation |

---

## Data Classes

Binary map data structures from `wadlib.lumps`. All are `@dataclass` types
with a `to_bytes()` method for round-trip serialization.

| Class | Module | Fields |
|---|---|---|
| `Thing` | `things` | `x`, `y`, `direction`, `type`, `flags` (10 bytes) |
| `Vertex` | `vertices` | `x`, `y` (4 bytes) |
| `LineDefinition` | `lines` | `start_vertex`, `finish_vertex`, `flags`, `special_type`, `sector_tag`, `right_sidedef`, `left_sidedef` (14 bytes); `.generalized` returns `GeneralizedLinedef \| None` |
| `SideDef` | `sidedefs` | `x_offset`, `y_offset`, `upper_texture`, `lower_texture`, `middle_texture`, `sector` (30 bytes) |
| `Sector` | `sectors` | `floor_height`, `ceiling_height`, `floor_texture`, `ceiling_texture`, `light_level`, `special`, `tag` (26 bytes); `.special_name` returns human-readable special string |
| `Seg` | `segs` | `start_vertex`, `end_vertex`, `angle`, `linedef`, `direction`, `offset` (12 bytes) |
| `SubSector` | `segs` | `seg_count`, `first_seg` (4 bytes) |
| `Node` | `nodes` | `x`, `y`, `dx`, `dy`, right/left bounding boxes, `right_child`, `left_child` (28 bytes) |
| `HexenThing` | `hexen` | `tid`, `x`, `y`, `z`, `angle`, `type`, `flags`, `action`, `arg0`..`arg4` (20 bytes) |
| `HexenLineDef` | `hexen` | `start_vertex`, `finish_vertex`, `flags`, `special_type`, `arg0`..`arg4`, `right_sidedef`, `left_sidedef` (16 bytes) |

---

## UDMF

Universal Doom Map Format -- text-based map format used by ZDoom and GZDoom.

```python
from wadlib.lumps.udmf import (
    UdmfMap, UdmfThing, UdmfVertex, UdmfLinedef,
    UdmfSidedef, UdmfSector, parse_udmf, serialize_udmf,
)
```

| Class / Function | Description |
|---|---|
| `UdmfMap` | Parsed UDMF map with fields: `namespace`, `things`, `vertices`, `linedefs`, `sidedefs`, `sectors` |
| `UdmfThing` | UDMF thing with fields: `x`, `y`, `height` (float), `angle`, `type`, `id`, `props` dict |
| `UdmfVertex` | UDMF vertex with fields: `x`, `y` (float), `props` dict |
| `UdmfLinedef` | UDMF linedef with fields: `v1`, `v2`, `sidefront`, `sideback`, `special`, `id`, `props` dict |
| `UdmfSidedef` | UDMF sidedef with fields: `sector`, `texturetop`, `texturebottom`, `texturemiddle`, `offsetx`, `offsety`, `props` dict |
| `UdmfSector` | UDMF sector with fields: `heightfloor`, `heightceiling`, `texturefloor`, `textureceiling`, `lightlevel`, `special`, `id`, `props` dict |
| `UdmfParseError` | `ValueError` subclass raised by `parse_udmf(strict=True)` when no namespace is found |
| `parse_udmf(text, *, strict=False)` | Parse a UDMF TEXTMAP string into a `UdmfMap`; `strict=True` raises `UdmfParseError` on missing namespace |
| `serialize_udmf(udmf_map)` | Serialize a `UdmfMap` back to a UDMF TEXTMAP string |

All UDMF data classes store extended/unknown properties in a `props: dict[str, Any]`
field, preserving round-trip fidelity for custom source-port extensions.

---

## Demo

Parse Doom demo recordings (`.lmp` files). Supports both vanilla 4-byte tics
and longtics (5-byte, v1.91+) formats.

```python
from wadlib.lumps.demo import parse_demo, Demo, DemoHeader, DemoTic
```

| Class / Function | Description |
|---|---|
| `parse_demo(data)` | Parse raw demo bytes into a `Demo` object |
| `Demo` | Parsed demo with fields: `header` (`DemoHeader`), `tics` (list of per-frame player tic lists) |
| `Demo.duration_tics` | Total number of recorded frames |
| `Demo.duration_seconds` | Duration in seconds (at 35 Hz) |
| `Demo.player_path(player=0)` | Reconstruct approximate `(x, y)` positions from movement inputs |
| `DemoHeader` | Header with fields: `version`, `skill`, `episode`, `map`, `multiplayer_mode`, `respawn`, `fast`, `nomonsters`, `player_pov`, `players` |
| `DemoHeader.num_players` | Count of active players |
| `DemoHeader.skill_name` | Human-readable skill name (e.g. `"Ultra-Violence"`) |
| `DemoTic` | Single input frame with fields: `forwardmove`, `sidemove`, `angleturn`, `buttons` |
| `DemoTic.fire` | `True` if fire button pressed |
| `DemoTic.use` | `True` if use button pressed |
| `DemoTic.weapon` | Weapon change slot (0 = no change) |
