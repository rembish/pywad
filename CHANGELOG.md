# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.66] - 2026-04-10

### Fixed

- **`--sprites` shows PLAY sprite for Bloody Mess decorations**: thing type 10
  ("Bloody Mess") is a `DECORATION` but shares the `PLAY` sprite prefix with
  actual player starts.  `DECORATION` category things now always render as
  their marker dot regardless of `--sprites`, so decorative dead-player props
  no longer look like live player starts on the map.

## [0.0.65] - 2026-04-10

### Fixed

- **Extra player sprites in singleplayer renders**: Player 2/3/4 starts
  (thing types 2–4) carry no `NOT_SINGLEPLAYER` flag, so the flag-based
  filter introduced in v0.0.64 didn't hide them.  They are now explicitly
  excluded from singleplayer renders and only shown with `--multiplayer`.

## [0.0.64] - 2026-04-10

### Added

- `wadcli export map --multiplayer` — include multiplayer-only things
  (those with the `NOT_SINGLEPLAYER` flag, `0x0010`) in rendered maps.
  By default, only singleplayer things are rendered, matching what a solo
  player sees in-game.  Pass `--multiplayer` to also show cooperative player
  starts and other multiplayer-only entities.

## [0.0.63] - 2026-04-10

### Fixed

- **`--sprites` cache bug**: sprite lookup was keyed per-lump-name, so a miss
  on `{PREFIX}A0` was cached as `None` and returned immediately on all
  subsequent things of the same type — preventing the `A1` fallback from ever
  being tried.  Cache is now keyed by 4-char prefix so each type is resolved
  once correctly.
- **Deathmatch Start / Teleport Landing** (types 11 and 14) re-categorised
  from `PLAYER` to `DECORATION`.  They have no sprite and are map-editor
  markers, not renderable entities, so they were producing spurious blue
  direction triangles on every map.

## [0.0.62] - 2026-04-10

### Added

- `wadcli export map --sprites` — draw WAD sprites at thing positions instead
  of category marker shapes.  Wires the existing `RenderOptions.show_sprites`
  flag (added in v0.0.51) to the CLI.

## [0.0.61] - 2026-04-10

### Added

- `wadcli export sprite --all [DIR]` — batch-export every sprite lump to PNG
  files in a directory (default: `./`).  The positional `name` argument is now
  optional; omitting it without `--all` exits with a clear error message.

## [0.0.60] - 2026-04-10

### Changed

- **Automap line coloring**: linedefs are now classified and coloured like
  Doom's in-game automap:
  - White — one-sided (solid) walls
  - Yellow — two-sided with differing floor heights (steps/ledges)
  - Light grey — two-sided with only ceiling-height difference
  - Grey — ordinary passable two-sided lines
  - Magenta — secret-flagged lines (flag bit `0x0020`)
  - Cyan — lines with a special action (doors, lifts, triggers)

## [0.0.59] - 2026-04-10

### Added

- `wadcli export map --all [DIR]` — batch-export every map in a WAD to PNG
  files in a directory (default: `./`).  The positional `map` argument is now
  optional; omitting it without `--all` exits with a clear error message.

## [0.0.57] - 2026-04-10

### Changed

- **`BaseLump` typed via `Generic[T]`**: `read_item`, `__iter__`, `__next__`,
  `__getitem__`, and `get` now carry proper `T` / `T | None` return types
  instead of bare `Any`.
- **`PNames.names` and `TextureList.textures` → `@cached_property`**: avoids
  O(N²) re-parsing in `TextureCompositor.compose_all()`.
- **`MapLevel.attach_vertexes` → `attach_vertices`**: corrects the English
  spelling; dispatch table in `wad.py` updated accordingly.
- **`load_pwad()` preserves `load_deh()` override**: any external `.deh` file
  is saved before cache eviction and restored afterwards automatically.
- **`Picture` header cached**: four `@property` methods that each re-parsed the
  same 8-byte header unified into a single `@cached_property _header`.
- **`MapRenderer.im` / `.draw` made private** (`_im`, `_draw`): a new public
  `image` property exposes the canvas.  All call-sites (CLI, tests) updated.

## [0.0.56] - 2026-04-10

### Changed

- Coverage threshold lowered from 90% to **80%** (`--cov-fail-under=80`).
  GHA CI only has 3 WADs (blasphem, freedoom1, freedoom2); the 63 tests that
  require HEXEN.WAD, DOOM.WAD, or DOOM2.WAD skip, dropping CI coverage to
  ~85%.  80% is a conservative floor that passes in both environments.

## [0.0.55] - 2026-04-10

### Changed

- **Floor rendering O(N²) → O(N) speedup**: `MapRenderer._draw_floors()` now
  performs a single BSP tree traversal to collect all subsector polygons at once
  (`_collect_all_ssector_polys` / `_bsp_collect`) instead of a separate
  root-to-leaf walk per subsector.  MAP01 (698 subsectors, depth ≈ 10) goes from
  ~36 s to ~2 s per render in tests.
- Coverage threshold raised from 85% to **90%** (`--cov-fail-under=90` in
  `pyproject.toml`).  Total coverage is 90.04%.

### Added

- Tests for info.py stcfn-font / dehacked / many-maps-truncation paths
  (freedoom1.wad required)
- Tests for export_music.py Mus→MIDI and Mus raw paths (DOOM2.WAD required)
- `test_compositor_compose_all_minimal` — fast synthetic WAD with 1 texture
  covers `compose_all()` lines including `texture2 is None` branch
- `test_list_animations_*` — synthetic ANIMDEFS lump tests covering the full
  `list_animations.run()` code path

## [0.0.54] - 2026-04-10

### Added

- `test_cli_direct.py` — direct-call CLI tests (no subprocess) covering every
  `run()` function in all `wadcli` command modules; brings CLI coverage from
  ~10% to >80%
- `test_lumps_coverage.py` — targeted tests for previously uncovered library
  code: `language.py`, `sndseq.py`, `zmapinfo.py`, `dehacked.py`, `renderer.py`
  floor paths, `compositor.py` edge cases, and `wad.py` None-path accessors
- `--cov-fail-under=70` enforced in `pyproject.toml` — CI now fails below 70%

### Changed

- Overall test coverage raised from 55% to 85%
- Slow floor-rendering and compose-all tests in the new files marked
  `@pytest.mark.slow` so the default fast suite stays under 15 s

## [0.0.53] - 2026-04-10

### Added

- `tests/test_cli.py` — 38 subprocess-level integration tests covering every
  `wadcli` command group: `check` (clean exit 0 + bad-WAD exit 1 + `--json`),
  `diff` (identical WAD exits 0, different exits 1, JSON structure), `info`
  (text + JSON), `list` (maps/lumps/textures/flats/sprites/sounds/music/patches/stats,
  all with `--json` validation), `export` (map, flat, sound, music, texture,
  sprite, lump — each verifies the output file is created and non-empty)

## [0.0.52] - 2026-04-10

### Added

- GitHub Actions CI workflow (`.github/workflows/ci.yml`): runs `make check`
  (format, lint, mypy, pylint, fast tests) on Python 3.12 and 3.13 on every
  push and pull-request to `master`; a separate step runs the `slow` test
  subset (compositor and floor-renderer stress tests) using the committed
  freedoom WADs
- CI status badge in README

## [0.0.51] - 2026-04-10

### Added

- `RenderOptions.show_sprites` flag: when `True`, `MapRenderer` renders the
  actual WAD sprite at each thing's map position instead of the coloured
  category shape; falls back to shape if the sprite lump is missing or no
  WadFile/palette is available; sprite images are cached per lump so each
  unique sprite is decoded only once per render call
- `get_sprite_prefix(type_id)` in `doom_types` — maps Doom 1/2 thing type IDs
  to their 4-char WAD sprite lump prefix (covers players, all monsters, keys,
  weapons, ammo, health, armour, powerups, and common decorations)

## [0.0.50] - 2026-04-10

### Added

- `wadcli check` — sanity-checks a WAD for common authoring errors; checks all maps for:
  missing textures (sidedef upper/lower/middle not in TEXTURE1/TEXTURE2), missing flats
  (sector floor/ceiling not in F_START..F_END), out-of-range sidedef/vertex/sector
  references in linedefs and sidedefs, and duplicate map names across the PWAD stack;
  exits with code 1 when issues are found; supports `--json` for pipeline use

## [0.0.49] - 2026-04-10

### Fixed

- Eliminated four `type: ignore[assignment]` suppressions in `attach_znodes`:
  `BaseMapEntry.vertices/segs/ssectors/nodes` now declare union types that
  include both vanilla (`Vertices`, `Segs`, `SubSectors`, `Nodes`) and
  ZNOD (`ZNodList[ZNodVertex/Seg/SubSector/Node]`) variants; mypy accepts
  `attach_znodes` assignments without any suppression comments

### Changed

- `TODO.md` updated — marked ZNODES, light-shaded floors, `load_pwad`,
  `list stats`, `wadcli diff`, export palette/font, `--json`,
  OGG/MP3/MIDI music, `BaseLump` fd hazard, and cached-property
  invalidation as done

## [0.0.48] - 2026-04-10

### Added

- Committed `blasphem.wad` (Blasphemer 0.1.8, BSD-3 Clause) — a free/open-source
  Heretic IWAD replacement; Heretic format tests now run unconditionally without
  requiring the proprietary `HERETIC.WAD`
- `blasphemer_wad` session fixture in the test suite; all Heretic-format tests
  rewired from `heretic_wad` to `blasphemer_wad`

## [0.0.47] - 2026-04-10

### Added

- **ZNODES support** — maps compiled by ZDoom/GZDoom's node builder (XNOD uncompressed and
  ZNOD zlib-compressed variants) are now parsed automatically; the extended BSP nodes, segs,
  and subsectors replace the vanilla lumps and the extra vertices are merged into the map's vertex
  list so the floor renderer works on GZDoom-compiled maps unchanged
- `MapData.ZNODES` enum member recognises the ZNODES lump name in the map directory scan

### Fixed

- `MapRenderer._clip_by_segs`: changed `break` to `continue` when a seg lookup returns `None`
  (previously aborted the entire subsector clip at the first missing seg); also skip mini-segs
  (`linedef == 0xFFFF`) that carry no real wall information

## [0.0.46] - 2026-04-10

### Added

- `WadFile.load_pwad(path)` — dynamically layer a PWAD on top of an already-open WAD; invalidates
  all cached properties so the updated stack is reflected on next access

## [0.0.45] - 2026-04-10

### Changed

- `export map --floors` now shades each subsector's floor flat by its sector light level using the
  COLORMAP lump; dark rooms render noticeably darker than brightly lit ones

## [0.0.44] - 2026-04-10

### Added

- `wadcli diff <wad_a> <wad_b>` — compare two WADs and report added, removed, and changed lumps
  with byte sizes and deltas; exit code 1 when differences exist (useful in scripts); supports
  `--json` for machine-readable output

## [0.0.43] - 2026-04-10

### Added

- `wadcli list stats` — aggregate statistics across all maps: total and per-map
  thing/linedef/vertex/sector counts (with min/max/avg), secret sector count,
  and thing breakdown by category (monster, weapon, ammo, health, …); supports
  `--json` for pipeline use

## [0.0.42] - 2026-04-10

### Changed

- **CLI: global `--wad` / `--pwad` / `--deh` flags** — WAD arguments are now placed before the
  subcommand (`wadcli --wad DOOM.WAD list maps`) instead of after it; this lets you keep the WAD
  path constant while switching commands without retyping it
- **CLI: optional output paths on all `export` subcommands** — the output file argument is now
  optional; when omitted a default filename is derived from the lump/map name and format
  (e.g. `export map E1M1` → `E1M1.png`, `export music D_E1M1` → `D_E1M1.mid`)

### Added

- `wadcli export palette` — renders the PLAYPAL lump as a colour-swatch PNG
  (16 colours × 16 rows per palette); supports `--palette N` to export a single palette
- `wadcli export font` — renders a WAD font (`stcfn`, `fonta`, or `fontb`) as a sprite-sheet PNG
  with one glyph per cell and ASCII labels; supports `--cols N` and `--palette N`
- `--json` flag on `info` and all `list *` subcommands — outputs structured JSON suitable for
  shell pipelines (`wadcli --wad DOOM2.WAD info --json | jq .maps`)

## [0.0.40] - 2026-04-09

### Added

- `OggLump` and `Mp3Lump` lump types (`wadlib.lumps.ogg`) for OGG Vorbis and MP3 audio; each exposes `.save(path)` for extracting the raw audio
- `WadFile.music` now detects OGG (`OggS` magic) and MP3 (`ID3` tag or `\xff\xfb`/`\xff\xf3`/`\xff\xf2` sync bytes) alongside the existing MUS format; return type is `dict[str, Mus | OggLump | Mp3Lump]`
- `wadcli export music` handles all three formats: MUS lumps convert to MIDI (or raw with `--raw`), OGG/MP3 lumps write raw bytes directly

## [0.0.39] - 2026-04-10

### Fixed

- `list_maps`: replaced `object` parameter types with precise `MapInfoLump | None` / `ZMapInfoLump | None` / `ZMapInfoEntry | MapInfoEntry | None` unions; used `Mapping` for covariant music dict; all mypy errors resolved
- `export_colormap`: added `assert pixels is not None` to satisfy mypy's `PixelAccess | None` check
- `export_animation`: typed `flat_entries` as `dict[str, DirectoryEntry]`; split `img` variable into `frame_img` to avoid `Image | None` assignment error; added `assert palette is not None` guard

## [0.0.38] - 2026-04-10

### Fixed

- `WadFile.maps` now returns maps sorted in canonical order (E1M1…E4M9, then MAP01…MAP32) regardless of WAD directory order; PWADs like BTSX E1 that store maps non-sequentially previously listed MAP32 first

## [0.0.37] - 2026-04-10

### Added

- `LanguageLump` (`wadlib.lumps.language`) — parses ZDoom LANGUAGE lumps; `.strings` returns a `dict[str, str]` of all English-section entries keyed by uppercase ID; `.lookup(key)` resolves a single key with a fallback default
- `WadFile.language` cached property (PWAD-aware)
- `ZMapInfoEntry.title_lookup` — stores the LANGUAGE key when a map uses `lookup "KEY"` title syntax instead of a literal string
- `ZMapInfoEntry.par` — PAR time (seconds) parsed from the `par = N` block property
- `ZMapInfoEntry.resolved_title(language)` — convenience method that resolves lookup titles via a language strings dict
- `wadcli list maps` now resolves `lookup "KEY"` map titles via the LANGUAGE lump (e.g. BTSX E1 shows real track names instead of `lookup "HUSTR_N"`)

### Fixed

- ZMAPINFO title parsing: `lookup "KEY"` syntax no longer leaks into the displayed title

## [0.0.36] - 2026-04-10

### Added

- `DehackedFile` (`wadlib.lumps.dehacked`) — reads a standalone `.deh` file from disk; exposes the same API as `DehackedLump` (`par_times`, `doom_version`, `patch_format`, `raw()`)
- `WadFile.load_deh(path)` — loads an external `.deh` and injects it as the WAD's `dehacked` property, overriding any embedded DEHACKED lump
- `--deh PATH` option on every `wadcli` subcommand — applies a standalone DeHackEd patch alongside the loaded WAD

## [0.0.35] - 2026-04-09

### Added

- `--pwad PATH` option on every `wadcli` subcommand (repeatable); layers one or more PWADs on top of the base WAD using `WadFile.open()`
- `WadFile.maps` is now PWAD-aware: maps from all loaded WADs are merged, with PWAD maps overriding same-named base maps and new PWAD maps appended

### Fixed

- `wadcli export map --floors` with a PWAD (e.g. SIGIL II over DOOM2.WAD) now finds floor flat textures from the base IWAD; previously only base-WAD maps were searched

## [0.0.34] - 2026-04-09

### Added

- `DehackedLump` (`wadlib.lumps.dehacked`) — parses embedded DEHACKED lumps; exposes `par_times` (dict of map name → seconds), `doom_version`, and `patch_format`; both Doom-1 (`par E M secs`) and Doom-2 (`par MM secs`) PAR formats are supported
- `WadFile.dehacked` cached property (PWAD-aware)
- `wadcli info` now shows DEHACKED presence, Doom version, and PAR time count

## [0.0.33] - 2026-04-09

### Added

- `WadFile.stcfn` — Doom HUD font glyphs (STCFN033–STCFN127), PWAD-aware, keyed by ASCII ordinal
- `WadFile.fonta` — Heretic large font (FONTA01–FONTA59 between FONTA_S/FONTA_E), keyed by ASCII ordinal
- `WadFile.fontb` — Heretic small font (FONTB01–FONTB58 between FONTB_S/FONTB_E), keyed by ASCII ordinal
- `wadcli info` now shows font summary (name and glyph count for each present font)

## [0.0.32] - 2026-04-09

### Added

- PWAD layering: `WadFile.open(base, *pwads)` opens a base IWAD with one or more PWADs stacked on top; PWAD lumps shadow base-WAD lumps by name, mirroring Doom engine load order
- `WadFile.close()` and context-manager support now close all layered PWAD file handles
- All lump accessors (textures, flats, sprites, sounds, music, colormap, playpal, pnames, endoom, sndinfo, sndseq, mapinfo, zmapinfo, animdefs, maps) are PWAD-aware: single-lump properties use `_find_lump()` (PWAD-first); collection properties (flats, sprites, music, sounds) iterate base-first so PWAD entries overwrite base entries

### Fixed

- Orphaned `_animdefs_unused` dead code removed from `WadFile`
- Floors missing in SIGIL II renders: use `WadFile.open("DOOM2.WAD", "SIGIL_II.WAD")` so the renderer finds base-game flats when rendering PWAD maps

## [0.0.31] - 2026-04-09

### Added

- `ZMapInfoLump` / `ZMapInfoEntry` (`wadlib.lumps.zmapinfo`) — parses the ZDoom `ZMAPINFO` lump (brace-delimited format, `//` comments); extracts map name, title, music, next/secretnext, sky1, levelnum, cluster, titlepatch per map
- `WadFile.zmapinfo` cached property
- `wadcli info` now shows ZMAPINFO map count
- `wadcli list maps` uses ZMAPINFO (priority over MAPINFO) for title and direct music lump name; SIGIL and other ZDoom PWADs now show correct per-map music

### Fixed

- `wadcli info` MAPINFO/ZMAPINFO shows `none` instead of `0 maps` when lump is empty or absent

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
