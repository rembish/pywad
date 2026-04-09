# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.30] - 2026-04-09

### Added

- `SndSeqLump` / `SndSeq` / `SndSeqCommand` (`wadlib.lumps.sndseq`) — parses the Hexen `SNDSEQ` lump; `.sequences` returns all named blocks; `.get(name)` looks up by name; each `SndSeq` exposes its list of `SndSeqCommand` (command, sound name, optional tic count)
- `WadFile.sndseq` cached property

## [0.0.29] - 2026-04-09

### Added

- `wadcli info` now shows Sprites, Sounds, Music, Colormap, ANIMDEFS, MAPINFO, and SNDINFO counts
- Hexen thing catalog entries in `doom_types.py`: Centaur, Slaughtaur, Dragon, Heresiarch, Dark Bishop, Death Wyvern, all 11 Hexen keys, Hexen armor pieces, powerups, Flechette (44 new entries total)

### Changed

- Heretic low-ID things (monsters, weapons, ammo) are skipped in the catalog — IDs overlap with Doom; the lookup is game-agnostic so Doom entries take precedence for conflicting IDs

## [0.0.28] - 2026-04-09

### Added

- `DmxSound.rate` and `DmxSound.sample_count` properties — callers no longer need to re-parse the DMX header
- `wadcli export colormap` — renders the COLORMAP lump as a 1024×136 PNG grid (256 palette entries × 34 light levels, coloured via PLAYPAL)
- `wadcli list animations` — lists all ANIMDEFS flat/texture sequences with frame count and timing
- `wadcli export animation` — renders an ANIMDEFS animation sequence as an animated GIF; supports both flats and textures; frame duration derived from ANIMDEFS tic values at 35 Hz

### Changed

- `wadcli list sounds` now uses `DmxSound.rate` / `DmxSound.sample_count` instead of re-parsing the DMX header inline
- `WadFile.sounds` scan now imports `_HEADER_SIZE` from `wadlib.lumps.sound` instead of duplicating the constant as a class attribute

## [0.0.27] - 2026-04-09

### Fixed

- `wadcli list maps` MUSIC column now works for all supported games:
  - Doom 1: `D_E1M1` naming (unchanged)
  - Heretic: `MUS_E1M1` naming (was returning empty)
  - Hexen: no MUS lump naming convention — falls back to `cd:N` from MAPINFO cdtrack
  - Doom 2: `D_RUNNIN` table (unchanged)
- MAPINFO entry resolved once per row (was looked up twice, once for title and once for music)

## [0.0.26] - 2026-04-09

### Added

- `ColormapLump` (`wadlib.lumps.colormap`) — 34-entry light-level remapping table; `get(index) -> bytes`, `apply(colormap_index, palette_index) -> int`, `count` property
- `SndInfo` (`wadlib.lumps.sndinfo`) — parses the `SNDINFO` text lump; exposes `.sounds` as `dict[str, str]` mapping logical name → uppercase WAD lump name (Hexen/Heretic)
- `MapInfoLump` / `MapInfoEntry` (`wadlib.lumps.mapinfo`) — parses Hexen `MAPINFO`; `MapInfoEntry` carries `map_num`, `title`, `warptrans`, `next`, `cluster`, `sky1`, `sky2`, `cdtrack`, `lightning`, `doublesky`, `fadetable`; `.get(map_num)` accessor
- `AnimDefsLump` / `AnimDef` / `AnimFrame` (`wadlib.lumps.animdefs`) — parses Hexen `ANIMDEFS`; `.animations`, `.flats`, `.textures` properties; `AnimFrame` records `pic`, `min_tics`, `max_tics`; `AnimDef.is_random` property
- `WadFile.colormap`, `.sndinfo`, `.mapinfo`, `.animdefs` cached properties
- `wadcli list maps` now shows TITLE (from MAPINFO when present) and MUSIC lump (for Doom 1/2 maps matching `D_E#M#` / Doom 2 conventional names)

## [0.0.25] - 2026-04-09

### Fixed

- `WadFile.sounds` now detects DMX lumps by magic bytes (`format==3`) instead of `DS`/`DP` name prefix — Hexen and Heretic sounds are now found correctly
- DMX `num_samples` field includes the 16-byte padding in its count; detection size check and `DmxSound.to_wav()` PCM slice corrected accordingly (previously exported WAV files contained 16 extra zero bytes)
- PC speaker lumps (format 0, `DP*`) are no longer included in `sounds` — they cannot be meaningfully converted to WAV

## [0.0.24] - 2026-04-09

### Added

- `DmxSound` lump decoder (`wadlib.lumps.sound`) — converts DMX PCM data to a RIFF WAV (mono, 8-bit unsigned); `to_wav() -> bytes`
- `Endoom` lump decoder (`wadlib.lumps.endoom`) — parses the 80×25 CGA text screen; `to_text() -> str` (plain ASCII) and `to_ansi() -> str` (ANSI escape colour codes)
- `WadFile.sounds` / `get_sound(name)` — collects `DS*`/`DP*` lumps by name
- `WadFile.sprites` / `get_sprite(name)` — collects lumps between `S_START`/`S_END` markers
- `WadFile.endoom` — returns the `ENDOOM` lump or `None`
- CLI commands: `export sound`, `export sprite`, `export endoom`, `list sounds`, `list sprites`

### Fixed

- `WadFile.music` now detects MUS lumps by `MUS\x1a` magic bytes instead of `D_`/`MUS_` name prefix — Hexen's arbitrarily named music lumps (e.g. `WINNOWR`, `JACHR`, `CHESS`) are now found correctly

### Changed

- `.gitignore` extended to cover `*.mid`, `*.wav`, `*.png`, `*.ansi` export artifacts

## [0.0.23] - 2026-04-09

### Added

- `Mus` lump decoder (`wadlib.lumps.mus`) — full MUS→SMF type-0 MIDI conversion (`to_midi() -> bytes`); channel mapping (MUS ch 15 → MIDI ch 9), 140 BPM / 70 ticks/quarter-note tempo
- `WadFile.music` / `get_music(name)` — returns all MUS lumps as `dict[str, Mus]`
- CLI restructured from flat hyphenated subcommands to a two-level grouped interface: `wadcli list <what>` and `wadcli export <what>`; bare invocation of any group now prints help
- `wadcli export music` — saves MUS lump as MIDI (default) or raw MUS bytes (`--raw`)
- `wadcli list music` — lists all music lumps with sizes
- `extract-lump` folded into `wadcli export lump`
- Subcommands sorted alphabetically within each group
- `--alpha` flag on `wadcli export map` — RGBA output with transparent void and 5 px black exterior outline
- Directional equilateral triangle markers for `PLAYER` and `MONSTER` things (replaces filled circle + arrow)
- 12 MUS tests

### Fixed

- Floor rendering rewritten: BSP node-tree walk with Sutherland-Hodgman polygon clipping derives each subsector's exact convex region, then clips against the subsector's own segs to prevent bleeding — achieves 237/237 subsectors on E1M1 without void bleed

## [0.0.22] - 2026-04-09

### Added

- `MapRenderer` (`wadlib.renderer`) — replaces `MapExporter`; `RenderOptions` dataclass (`scale`, `show_things`, `show_floors`, `palette_index`, `thing_scale`, `alpha`); per-category thing markers (triangles for player/monster, diamonds for keys, squares for pickups); optional BSP subsector floor-flat fill
- `ThingCategory` enum and 100-entry Doom 1/2 thing catalog (`wadlib.doom_types`)
- `MapExporter` kept as a `DeprecationWarning` shim wrapping `MapRenderer`
- `wadcli` entry point with 11 modular subcommands: `info`, `list-maps`, `list-lumps`, `list-textures`, `list-flats`, `list-patches`, `export-map`, `export-texture`, `export-flat`, `export-patch`, `extract-lump`
- 14 renderer tests, 14 doom_types tests, 3 exporter deprecation tests

## [0.0.21] - 2026-04-09

### Added

- `TextureCompositor` (`wadlib.compositor`) — blits patches from PNAMES onto a per-texture canvas using TEXTURE1/TEXTURE2 patch descriptors; produces PIL `RGBA` images with correct dimensions
- `compose(name) -> Image | None` for single texture lookup (case-insensitive via `TextureList.find`)
- `compose_all() -> dict[str, Image]` to render every texture in TEXTURE1 + TEXTURE2
- Optional `palette` constructor argument; defaults to PLAYPAL palette 0
- 10 new tests covering construction, dimensions, blank-check, unknown texture, custom palette, Doom 2

## [0.0.20] - 2026-04-09

### Added

- `Flat` lump decoder (`wadlib.lumps.flat`) — decodes raw 64x64 palette-indexed floor/ceiling data into a PIL `RGB` image
- `WadFile.flats` cached property — returns all flat lumps between `F_START`/`F_END` (and `FF_START`/`FF_END`) as `dict[str, Flat]`
- `WadFile.get_flat(name) -> Flat | None` convenience accessor (case-insensitive)
- 12 new tests

## [0.0.19] - 2026-04-09

### Added

- `Picture` lump decoder (`wadlib.lumps.picture`) — decodes Doom's column-based picture format into a PIL `RGBA` image; transparent gaps between posts become alpha=0 pixels
- `WadFile.get_picture(name) -> Picture | None` convenience accessor
- `pic_width`, `pic_height`, `left_offset`, `top_offset` properties
- 10 new tests covering dimensions, RGBA output, opaque pixel presence, per-channel bounds, and Doom 2 compatibility

## [0.0.18] - 2026-04-09

### Changed

- Project renamed from `pywad` to **`wadlib`** — `pywad` was already occupied on PyPI by an unrelated Selenium framework. All imports, package metadata, and tooling updated accordingly.

## [0.0.17] - 2026-04-09

### Added

- `PNames` lump reader (`wadlib.lumps.textures`) — parses the PNAMES lump; exposes `.names` (list of patch name strings) and `len()`
- `TextureList` lump reader — parses TEXTURE1/TEXTURE2 composite texture definitions; exposes `.textures` (list of `TextureDef`), `len()`, and `.find(name)` (case-insensitive lookup)
- `TextureDef` and `PatchDescriptor` dataclasses for structured access to texture/patch data
- `WadFile.pnames`, `WadFile.texture1`, `WadFile.texture2` cached properties
- 17 new tests covering PNAMES length, name types, TEXTURE1 entry count/dimensions/patches, find() hit/miss/case-insensitive

## [0.0.16] - 2026-04-09

### Added

- `PlayPal` lump reader (`wadlib.lumps.playpal`) — parses the PLAYPAL lump into up to 14 RGB palettes; supports `get_palette(index)`, iteration, and `len()`
- `WadFile.playpal` cached property — returns `PlayPal | None` for the first PLAYPAL lump in the directory
- 11 new tests covering palette count, colour bounds, iteration, and cross-WAD access

## [0.0.15] - 2026-04-09

### Changed

- `BaseMapEntry` lump attributes replaced `Any` with precise Union types: `things: Things | HexenThings | None`, `lines: Lines | HexenLineDefs | None`, and concrete types for all other lumps — mypy strict now catches type errors on lump access without casts

## [0.0.14] - 2026-04-09

### Added

- `WadFile.get_lump(name) -> BaseLump | None` — returns the first flat directory lump with the given name
- `WadFile.get_lumps(name) -> list[BaseLump]` — returns all flat directory lumps with the given name
- 7 new tests covering both accessors (hit, miss, raw data, multiple matches)

## [0.0.13] - 2026-04-09

### Fixed

- Shared file-descriptor hazard: `BaseLump` now buffers its entire lump into a private `io.BytesIO` on construction instead of seeking the WAD `fd` on every read — concurrent iteration (e.g. `zip(map.things, map.vertices)`) no longer interleaves seeks and corrupts both streams
- `Reject` and `BlockMap` updated the same way: data is read from the `fd` once during `__init__`; `BlockMap._parse()` lazy-loading removed
- Added `BaseLump.raw() -> bytes` helper
- Two regression tests: `test_zip_things_vertices_gives_correct_counts` and `test_parallel_iteration_values_unchanged`

## [0.0.12] - 2026-04-09

### Changed

- `MapExporter` rewritten: draws linedefs (white = one-sided/solid, grey = two-sided/passable) and things (red outlines); Y-axis is now correctly flipped (WAD uses math coords, PIL uses screen coords); auto-scales to fit in 4096px; `save(path)` method added

## [0.0.11] - 2026-04-09

### Added

- Hexen format support: `HexenThing` (20 bytes — adds `tid`, `z`, `action`, `arg0`-`arg4`) and `HexenLineDef` (16 bytes — replaces `special_type`/`sector_tag` with `special_type` + 5 args)
- Automatic format detection in `WadFile.maps`: lumps are now grouped per map first; if a `BEHAVIOR` lump is present the Hexen parsers are used for `THINGS` and `LINEDEFS`, otherwise Doom parsers are used
- Heretic works out of the box (Doom-compatible format, no detection needed)
- `heretic_wad` and `hexen_wad` session fixtures; `minimal_hexen_wad` unit fixture
- 21 new tests covering Heretic and Hexen WADs (127 total)

## [0.0.10] - 2026-04-09

### Added

- `REJECT` lump reader — lazy-loaded bitfield; `can_see(from, to, num_sectors)` query
- `BLOCKMAP` lump reader — lazy-loaded spatial index; exposes `origin_x/y`, `columns`, `rows`, `offsets`, `block_count`
- Refactored `WadFile.maps` to use a dispatch table instead of an `if/elif` chain — adding new lump types now requires a single dict entry

## [0.0.9] - 2026-04-09

### Added

- `NODES` lump parser — `Node` (28 bytes): partition line (x/y/dx/dy), right and left bounding boxes, right and left child indices. `BBox` helper dataclass. `SSECTOR_FLAG` (0x8000) and `right_is_subsector`/`left_is_subsector` properties for BSP traversal. 9 tests.

## [0.0.8] - 2026-04-09

### Added

- `SEGS` lump parser — `Seg(start_vertex, end_vertex, angle, linedef, direction, offset)` (12 bytes)
- `SSECTORS` lump parser — `SubSector(seg_count, first_seg)` (4 bytes)

## [0.0.7] - 2026-04-09

### Added

- `SECTORS` lump parser — `Sector(floor_height, ceiling_height, floor_texture, ceiling_texture, light_level, special, tag)` (26 bytes)

## [0.0.6] - 2026-04-09

### Added

- `SIDEDEFS` lump parser — `SideDef(x_offset, y_offset, upper_texture, lower_texture, middle_texture, sector)` with automatic bytes-to-str texture name decoding

## [0.0.5] - 2026-04-09

### Added

- pytest test suite: 60 tests covering header parsing, directory entries, map detection, lump attachment, Things/Vertices/LineDefs data, `BaseLump` seek/tell, and map boundaries; 88% branch coverage

### Fixed

- `BaseLump.__next__`: off-by-one — iterator stopped at `> _size` allowing one spurious read past EOF; corrected to `>= _size`
- `Thing.__post_init__`: struct unpacking produced a raw `int` for `flags`; coerce to `Flags` enum on construction

## [0.0.4] - 2026-04-09

### Added

- Modern project scaffolding: PEP 621 `pyproject.toml`, `Makefile` (`install`/`format`/`lint`/`typecheck`/`pylint`/`test`/`check`)
- ruff 0.4+ for linting and formatting
- mypy strict — passes with zero errors across all source files
- pylint 3.2+ — 10.00/10
- Full type annotations on all source files
- `.python-version` pinned to 3.12

## [0.0.3] - 2026-04-09

### Added

- `CHANGELOG.md`

## [0.0.2] - 2026-04-09

### Fixed

- `BaseLump.seek()`: `SEEK_CUR` branch compared `_rposition + offset` against `offset` instead of `_size`, and never updated `_rposition` on the happy path — relative seeking was broken whenever `_rposition > 0`
- `BaseMapEntry.boundaries`: crashed with `IndexError`/`TypeError` when `things` or `vertices` were `None` or empty; now falls back to `(Point(0,0), Point(0,0))`
- `MapEntry.__new__`: silently returned `None` for unrecognised map name formats; now raises `ValueError`

## [0.0.1] - 2023

### Added

- WAD header parsing: magic (`IWAD`/`PWAD`), lump count, directory offset
- Directory reading: 16-byte entries (offset, size, 8-char name)
- `WadFile` context manager with lazy-loaded `directory` and `maps` properties
- Map marker detection for Doom 1 (`E#M#`) and Doom 2 (`MAP##`) formats
- `THINGS` lump parser — `Thing(x, y, direction, type, flags)` with Doom/Boom/MBF flag enum
- `VERTEXES` lump parser — `Vertex(x, y)`
- `LINEDEFS` lump parser — `LineDefinition(start_vertex, finish_vertex, flags, special_type, sector_tag, right_sidedef, left_sidedef)`
- `BaseLump` abstraction with `seek`, `tell`, `read`, `read_row`, `read_item`, `__iter__`, `__len__`, `__getitem__`
- `MapExporter` — renders map Things as ellipses onto a PIL `Image`
- `MapData` enum covering all standard map lumps: `THINGS`, `LINEDEFS`, `SIDEDEFS`, `VERTEXES`, `SEGS`, `SSECTORS`, `NODES`, `SECTORS`, `REJECT`, `BLOCKMAP`, `BEHAVIOR`
- BSD 2-Clause licence
