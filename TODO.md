# TODO / Future ideas

Ideas collected over the course of development. Roughly ordered by scope.

---

## Format support

### pk3 / ZIP virtual filesystem
ZDoom/GZDoom use `.pk3` files (ZIP archives) as a replacement for WADs.
Implementing this requires:
- `Pk3File` class that opens a ZIP and presents a WAD-compatible API
- Namespace mapping: `flats/FOO.png` → flat `FOO`, `sprites/` → sprites, etc.
- `DirectoryEntry` abstraction to support both offset-based (WAD) and
  pre-loaded bytes (pk3 ZIP entries) — currently hardwired to file+offset
- PNG/TGA/JPG image decoding for flats, sprites, textures (Pillow already a dep)
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

### `wadcli check`
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

### `type: ignore[assignment]` in `attach_znodes`
`ZNodList[ZNodSeg/SubSector/Node/Vertex]` assigned to vanilla-typed fields
produces four `type: ignore[assignment]` suppressions.  Fix with Union types or
a shared `NodeLike` Protocol so mypy accepts both vanilla and ZNOD lumps in
those slots without suppression.

---

## Bigger ideas

### Web / interactive map viewer
A small Flask/FastAPI server that serves map renders and lets you pan/zoom,
click things to see their type, hover sectors to see their properties.

### Doom demo (`.lmp`) parser
Doom demo files record player input at tic resolution.  Parsing them would
let you replay or visualise routes through maps.

### DECORATE / ZScript stub parser
ZDoom's actor definition languages (DECORATE, ZScript) define custom things.
Even a minimal name-extraction pass would let `wadcli list things` show
meaningful names for custom actors in ZDoom PWADs.

### Packaging and publishing
- Publish to PyPI once API is stable
- GitHub Actions CI (lint + test on push) ✓ done (v0.0.49)
- Proper versioned docs (Sphinx or MkDocs)
