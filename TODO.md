# TODO / Future ideas

Ideas collected over the course of development. Roughly ordered by scope.

---

## Post-stabilization roadmap

This section is for the next feature direction after the current correctness,
docs, and fuzzing cleanup lands. It intentionally skips the short-term fixes
already in progress.

### Resource stack / `ResourceResolver` v2
The next large feature should be a first-class resource stack rather than another
standalone lump parser. Modern Doom content is defined by load order and lookup
rules as much as by file formats: IWAD + PWAD layers, duplicate names, PK3 paths,
PK3 namespaces, truncated WAD-style lump names, shadowing, filters, and embedded
maps.

Target goals:
- One resolver that can combine WAD, PWAD, PK3, and in-memory sources.
- Explicit constructors for both priority order and Doom load order:
  - `ResourceResolver.priority_order(*sources)` where first match wins.
  - `ResourceResolver.doom_load_order(base, *patches)` where later patches
    shadow earlier/base resources.
- A resource metadata object, e.g. `ResourceRef`, with:
  - canonical name
  - original path or lump name
  - source path/archive identity
  - source index/load-order index
  - directory or ZIP entry index
  - size
  - namespace/category (`flats`, `sprites`, `sounds`, `maps`, etc.)
  - lookup kind (`wad-name`, `pk3-path`, `pk3-lump-name`)
  - raw byte loader
  - collision/shadowing information
- Public APIs that make shadowing and collisions inspectable:
  - `find(name) -> ResourceRef | None`
  - `find_all(name) -> list[ResourceRef]`
  - `read(name) -> bytes | None`
  - `iter_resources(category=None)`
  - `shadowed(name)` / `collisions()`
- Keep PK3 path lookup canonical. WAD-style 8-character lump-name lookup over
  PK3 entries should be available, but clearly marked as lossy when names collide.

Acceptance tests should cover:
- duplicate lumps inside one WAD
- IWAD + one PWAD + two PWADs with override order
- WAD + PK3 mixed lookup
- PK3 entries that collide after uppercasing/truncation
- path-preserving PK3 lookup
- `find_all()` returning shadowed resources in deterministic order

### Unified map assembly over generic resources
Once resource lookup is source-agnostic, map assembly should work over generic
ordered resources rather than only WAD directory entries.

Formats to support through the same map-facing API:
- classic WAD map markers followed by map lumps
- Hexen-format maps with BEHAVIOR
- UDMF maps with `TEXTMAP` / `ENDMAP`
- PK3 decomposed maps such as `maps/MAP01/THINGS.lmp`
- PK3 embedded WAD maps such as `maps/MAP01.wad`

The output should preserve origin metadata so callers can tell whether a map
came from the base WAD, a PWAD, an embedded WAD inside a PK3, or decomposed PK3
map files.

### Validation and diagnostics layer
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

### Modern source-port parser maturity
After the resolver and diagnostics foundation is in place, improve modern text
format support incrementally. The goal should be "accurate metadata extraction"
before attempting anything like a source-port runtime.

Good next targets:
- UDMF: stricter tokenization, escaped strings, better malformed-input errors,
  namespace-specific validation, and semantic checks.
- TEXTURES: more complete ZDoom texture definitions, patch transforms, scaling,
  offsets, and graceful handling of unsupported clauses.
- ZMAPINFO / MAPINFO: richer map metadata, episodes, clusters, skies, music,
  next-map links, and compatibility flags.
- DECORATE: better include handling, replacement relationships, inheritance-aware
  metadata where possible, and clearer unsupported-expression reporting.
- ANIMDEFS: connect parsed animation definitions to texture/flat lookup and
  compositing APIs.

Full ZScript execution or full DECORATE behavior simulation should stay out of
scope unless the project deliberately becomes a source-port analysis engine.

### Release-shape documentation
Before a broader release, document the split between classic-WAD stability and
modern source-port coverage.

Suggested positioning:
- stable/mature: classic WAD reading, writing, inspection, maps, textures,
  palettes, sounds, music, and common CLI export workflows
- beta: source-port metadata, UDMF, PK3, DECORATE, ZMAPINFO, compatibility
  conversion, and FUSE
- explicitly unsupported or partial: full ZScript, full engine behavior,
  source-port runtime semantics

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
- Embedded WAD-format maps inside `maps/MAP01.wad` entries

### UDMF map format ✓ done (v0.0.89)
Universal Doom Map Format (text-based, used by myhouse.pk3 and most modern maps).
`MapData` now includes `TEXTMAP`/`ENDMAP`; UDMF maps attach to `WadFile.maps`
as `map_entry.udmf` (`UdmfLump`).  Full property parsing (vertices, linedefs,
sidedefs, sectors, things) via `UdmfLump`.

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

### Thing sprites on map
Render actual sprite frames (first rotation, front-facing) at thing positions
instead of coloured circles, giving a "screenshot from above" feel.

### Automap-style rendering mode
A thin-line automap renderer (à la the in-game automap) with secret-line
highlighting, keyed doors, etc.

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

### DECORATE / ZScript stub parser ✓ done (v0.0.89+)
`wadlib/lumps/decorate.py` provides `parse_decorate`, `DecorateActor`
(name, parent, doomednum, properties, flags, states), and `DecorateLump`.
`wadcli list actors` surfaces all actors with their DoomEdNums.
Not yet covered: full ZScript, inheritance resolution, expression evaluation.

### Packaging and publishing
- Publish to PyPI once API is stable
- GitHub Actions CI (lint + test on push) ✓ done (v0.0.49)
- Proper versioned docs (Sphinx or MkDocs)
