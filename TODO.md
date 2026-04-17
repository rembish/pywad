# TODO / Future ideas

Ideas collected over the course of development. Roughly ordered by scope.

---

## Post-stabilization roadmap

This section is for the next feature direction after the current correctness,
docs, and fuzzing cleanup lands. It intentionally skips the short-term fixes
already in progress.

### Resource stack / `ResourceResolver` v2 ✓ done (v0.2.4 – v0.3.6)

All planned resolver APIs are implemented:
- `ResourceResolver(WAD | PK3, ...)` — priority-order constructor (first wins).
- `ResourceResolver.doom_load_order(base, *patches)` — last patch wins.
- `find_all(name) -> list[ResourceRef]` — collision-complete; all matches,
  highest priority first.
- `ResourceRef` frozen dataclass: `name`, `archive`, `source`, `read_bytes()`,
  `size`, `namespace`, `kind`, `load_order_index`, `origin_path`, `directory_index`,
  `origin` property.
- `iter_resources(category=None)` — iterate unique resources; canonical category
  aliases applied (`sfx/` → `sounds`, `flat/` → `flats`, etc.).
- `shadowed(name)` / `collisions()` — shadowing and collision inspection.
  `collisions()` correctly excludes map-local lump names (THINGS, LINEDEFS,
  etc.) that appear once per map in multi-map WADs.
- `Pk3Entry.category` returns canonical category names via `_CATEGORY_ALIASES`.
- `ResourceRef.origin_path` / `directory_index` / `origin` — exact source
  identity for PK3 paths and WAD directory positions (v0.3.6).

### Unified map assembly over generic resources ✓ done (v0.3.1)

`Pk3Archive.maps` supports both embedded WAD maps and decomposed
`maps/MAP01/*.lmp` layouts.  `ResourceResolver.maps()` merges maps across WAD
and PK3 sources with priority order and origin metadata.  `WadFile.from_bytes()`
enables embedded WAD maps inside PK3 archives.  `attach_map_lumps()` works over
generic `LumpSource` objects.

### Validation and diagnostics layer ✓ done (v0.3.2)
After resource resolution is reliable, add a structured analysis API that goes
beyond the current writer-side validation and CLI checks.

Possible API shape:
- `analyze(wad_or_resolver) -> ValidationReport`
- `ValidationReport.errors`
- `ValidationReport.warnings`
- `ValidationReport.unsupported_features`
- JSON-serializable report objects for CLI and tooling use

Useful checks:
- missing textures, flats, patches, sprites, sounds, and music
- invalid map references: linedef vertices, sidedef sectors, sector references
- PNAMES patch indices that point nowhere
- duplicate/colliding resources and shadowed resources
- PK3 resources that collide under WAD-style names
- unsupported source-port features detected in ZMAPINFO, DECORATE, UDMF, or
  DEHACKED
- compatibility-level diagnostics: vanilla, limit-removing, Boom, MBF, MBF21,
  ZDoom, UDMF

The CLI can layer on this as `wadcli check --strict` or richer JSON output, but
the core report should live in the library first.

### Modern source-port parser maturity ✓ done (v0.3.3–v0.3.5)
After the resolver and diagnostics foundation is in place, improve modern text
format support incrementally. The goal should be "accurate metadata extraction"
before attempting anything like a source-port runtime.

Completed in v0.3.3:
- ZMAPINFO: episode/cluster/defaultmap blocks, `props` catch-all for unknown map
  keys, defaultmap baseline inheritance.
- UDMF: `UdmfParseError` exception, `strict` mode for missing namespace.
- TEXTURES: `TexturesPatch.translation`, `.blend`, `.raw_props`; serialiser updated.
- DECORATE: `_INCLUDE_RE` multiline fix; `DecorateLump.includes` and `.replacements`.

Completed in v0.3.3–v0.3.5:
- DECORATE: `#include` path handling and `replaces` mapping — fully implemented.

Completed in v0.3.7:
- TEXTURES: `TexturesDef.raw_props` captures unknown texture-level clauses;
  serialiser emits them before the patch list.
- UDMF: `UdmfMap.warnings` list populated during parse: unknown namespace,
  vertex missing x/y, linedef missing v1/v2/sidefront.
- DEHACKED: Pointer blocks now stored in `DehackedPatch.pointers`
  (pointer_index → codep_frame_index); `[CHEATS]` BEX section parsed into
  `DehackedPatch.cheats`.

Remaining / future:
- UDMF: namespace-specific semantic checks — started in v0.4.0 (required
  fields, cross-reference integrity, namespace-specific field warnings for
  z-height vertices and arg0-arg4 things). Full per-namespace field allowlists
  and deeper semantic validation remain future work.
- ANIMDEFS: `AnimDef.resolve_frames(ordered_names)` added in v0.4.0 — maps
  numeric pic indices to lump names given a caller-supplied ordered name list.
  Compositor integration (frame index → active texture at a given game tick)
  remains future work.

Full ZScript execution or full DECORATE behavior simulation should stay out of
scope unless the project deliberately becomes a source-port analysis engine.

### Release-shape documentation ✓ done
The README now includes a "Stability and coverage" table documenting the split:
- stable/mature: classic WAD reading, writing, maps, textures, audio, CLI
- beta: UDMF, PK3, ZMAPINFO, DECORATE, LANGUAGE, compatibility analysis, FUSE
- not supported: ZScript, ACS execution, source-port runtime semantics

### Synthetic fast-gate fixtures for CLI slow paths
Several CLI commands (`export_obj`, IWAD smoke tests) are currently covered only
by real-IWAD tests gated behind `pytest -m slow`.  If public CI needs those
branches exercised without proprietary data, small synthetic WAD fixtures could
stand in as fast-running gates.  Low priority until the CI bottleneck is felt.

---

## Format support

### pk3 / ZIP virtual filesystem
ZDoom/GZDoom use `.pk3` files (ZIP archives) as a replacement for WADs.
Implementing this requires:
- `Pk3File` class that opens a ZIP and presents a WAD-compatible API ✓ done (v0.1.3)
- Namespace mapping: `flats/FOO.png` → flat `FOO`, `sprites/` → sprites, etc. ✓ done (v0.1.3)
- `LumpSource` protocol to support both offset-based (WAD) and pre-loaded bytes
  (pk3 ZIP entries) — `MemoryLumpSource` decouples `BaseLump` from WAD fd ✓ done (v0.1.6)
- PNG/TGA/JPG image decoding for flats, sprites, textures ✓ done (v0.1.9)
- Embedded WAD-format maps inside `maps/MAP01.wad` entries ✓ done (v0.3.1)

### UDMF map format ✓ done (v0.0.89, tokenizer hardened v0.2.2)
Universal Doom Map Format (text-based, used by myhouse.pk3 and most modern maps).
`MapData` now includes `TEXTMAP`/`ENDMAP`; UDMF maps attach to `WadFile.maps`
as `map_entry.udmf` (`UdmfLump`).  Full property parsing (vertices, linedefs,
sidedefs, sectors, things) via `UdmfLump`.
Tokenizer hardened in v0.2.2: hex integer literals (`0xFF`, `0x1A`) and escaped
quotes inside strings (`\"`, `\\`) are now handled correctly.
Not yet covered: stricter namespace-specific validation, semantic checks.

### ZNODES compressed BSP ✓ done (v0.0.47)
Modern PWADs may use `ZNODES` instead of `NODES`/`SSECTORS`/`SEGS`.
Format: 4-byte magic (`XNOD` uncompressed, `ZNOD` zlib-compressed) followed by
extended vertex list, subsector array, seg array, node array with 32-bit child
indices.  Needed for correct rendering of GZDoom-compiled maps.

### OGG/MP3/MIDI music ✓ done (v0.0.40–0.0.41)
Source-port PWADs often ship `D_*` lumps as OGG, MP3, or raw MIDI instead of MUS.
Content-based detection (magic bytes) — exposed via `wad.music` alongside MUS lumps.

---

## Parsing / decoding

### Full DEHACKED parsing ✓ largely done (v0.0.89+)
The parser now covers: PAR times, thing stat overrides (hit points, speed,
damage, flags), frame/state patches, weapon patches, ammo patches, sound
remaps, text string replacements, custom thing ID extensions (DEHEXTRA /
MBF21).  Not yet covered: cheat code changes, state machine simulation,
sprite/frame sequence validation.

### TEXTURE lump: animated texture support via ANIMDEFS
`ANIMDEFS` maps sequences of flats/textures into animation cycles.  The
compositor could accept a frame index and return the correct lump for that tick.

### COLORMAP: sector light rendering ✓ done (v0.0.45)
The `ColormapLump` already decodes the 34 remapping tables.  The renderer
uses sector light levels + colormap to shade floor/ceiling colours.

### PC speaker sound (format 0)
DMX format-0 lumps are PC-speaker beep sequences, not PCM.  A basic
synthesiser (triangle or square wave per note) would let `to_wav()` produce
audio for these.

---

## Renderer improvements

### Texture-mapped walls (3D-ish overhead view)
The flat renderer fills floors; an analogous pass could fill each wall seg
with its upper/lower/middle texture, making the overhead view feel more like
an isometric screenshot than a schematic.

### Light-shaded floors ✓ done (v0.0.45)
Sector `light_level` + COLORMAP used to tint floor pixels at render time,
approximating in-game lighting.

### Thing sprites on map ✓ done
`RenderOptions.show_sprites = True` enables sprite rendering via
`MapRenderer._get_sprite_image()`.  Falls back to category shape when the
sprite lump is not found.  Requires a WadFile with PLAYPAL.

### Automap-style rendering mode ✓ done
`MapRenderer._linedef_colour()` assigns automap-style colours to all linedefs:
solid wall (white), passable step (yellow), passable ceiling-only (light grey),
secret (magenta), door/trigger special (cyan), plain two-sided (grey).
`RenderOptions.alpha = True` adds a black outline pass on exterior walls.

---

## CLI / tooling

### `wadcli diff` ✓ done (v0.0.44)
Compare two WADs (or a WAD+PWAD pair) and report added/removed/changed lumps,
useful for understanding what a PWAD actually modifies.

### `wadcli export font` ✓ done (v0.0.42)
Export a font (STCFN, FONTA, FONTB) as a sprite sheet PNG — one glyph per
cell, labeled with the character, suitable for previewing HUD fonts.

### `wadcli export palette` ✓ done (v0.0.42)
Export PLAYPAL as a visual swatch PNG (14 palettes × 256 colours).

### `wadcli list stats` ✓ done (v0.0.43)
Aggregate statistics across all maps: total things, total linedefs, sector
area distribution, thing type breakdown, secret count, etc.

### `wadcli check` ✓ done (v0.0.53)
Sanity-check a WAD for common authoring errors: missing textures, missing
flats, unreachable sectors, duplicate map names, etc.

### `--json` output flag ✓ done (v0.0.42)
Add `--json` to `info`, `list maps`, `list lumps`, etc. so wadlib can be
used in shell pipelines and scripts.

---

## API quality

### Type-safe map lump attributes ✓ done (v0.0.42+)
`BaseMapEntry` uses properly typed `Optional[Things]`, `Optional[Nodes]`, etc.
attributes; `mypy --strict` passes throughout the map layer.

### `BaseLump` shared `fd` hazard ✓ done (v0.0.42)
`BaseLump.__init__` now buffers the entire lump into a `BytesIO` on construction,
making each lump completely independent of the shared WAD file descriptor.

### `cached_property` invalidation for PWAD mutation ✓ done (v0.0.46)
`WadFile.load_pwad()` invalidates all cached properties so the updated PWAD
stack is reflected on next access.

### `type: ignore[assignment]` in `attach_znodes` ✓ done
`ZNodList[ZNodSeg/SubSector/Node/Vertex]` assigned to vanilla-typed fields
previously required four `type: ignore[assignment]` suppressions.  Resolved
via Union types; `mypy --strict` now passes with zero suppressions in the
znodes/map layer.

---

## Bigger ideas

### Web / interactive map viewer
A small Flask/FastAPI server that serves map renders and lets you pan/zoom,
click things to see their type, hover sectors to see their properties.

### Doom demo (`.lmp`) parser ✓ done (v0.0.89+)
`wadlib/lumps/demo.py` provides `parse_demo`, `Demo`, `DemoHeader`, `DemoTic`,
and `Demo.player_path()` for reconstructing approximate player movement from
recorded inputs.  Round-trip `to_bytes()` serialisation is also supported.

### DECORATE / ZScript stub parser ✓ done (v0.0.89+, inheritance v0.2.2, includes v0.3.3)
`wadlib/lumps/decorate.py` provides `parse_decorate`, `DecorateActor`
(name, parent, doomednum, properties, flags, states), and `DecorateLump`.
`wadcli list actors` surfaces all actors with their DoomEdNums.
`resolve_inheritance(actors)` added in v0.2.2: fills inherited properties, flags,
antiflags, states, and doomednum from parent chains; cycles are detected and broken.
`DecorateLump.includes` and `.replacements` implemented in v0.3.3.
Not yet covered: full ZScript, expression evaluation.

### Strife DIALOGUE / SCRIPTxx real-IWAD smoke tests ✓ done
`ConversationLump` / `ConversationPage` / `ConversationChoice` are tested
with synthetic binary fixtures and real-world slow smoke tests.  Retail
`STRIFE1.WAD` stores conversation data in `SCRIPTxx` lumps; source-port/demo
material may use `DIALOGUE` / `CONVERSATION`.  `WadFile.dialogue` exposes the
primary conversation lump and `WadFile.strife_scripts` enumerates all Strife
conversation lumps.

Real-world coverage requires `STRIFE1.WAD` or `VOICES.WAD` fixtures (both
proprietary — Rogue Entertainment / Velocity 1996).  These are gated behind
`pytest -m slow` and are never committed.

No freely redistributable Strife IWAD exists as of 2026-04:
- **Animosity** is an in-progress community project (analogous to Freedoom
  for Doom) but has not yet produced a playable IWAD.
- `STRIFE0.WAD` (demo) has ambiguous redistribution status.

### Packaging and publishing
- `pyproject.toml` published as v0.4.1 (name, version, description, readme,
  license, keywords, classifiers, dependencies, scripts, URLs all set). v0.4.1
  intentionally supersedes the incorrect v0.4.0 PyPI package.
- GitHub Actions CI (lint + test on push) ✓ done (v0.0.49)
- Proper docs site (MkDocs Material + GitHub Pages) ✓ done (v0.4.1) — auto-deploys
  on every push to master; `make docs` / `make docs-serve` for local preview.
  Multi-version docs (hosting v0.4.x alongside future v0.5.x, etc.) remain future work.
