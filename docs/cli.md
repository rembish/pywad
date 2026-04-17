# CLI Reference

`wadcli` is the command-line interface for inspecting, validating, converting, and exporting content from WAD and PK3 files.

## Global Flags

| Flag | Description |
|------|-------------|
| `--wad <path>` | Primary WAD file. Required for most commands. |
| `--pwad <path>` | Layer a PWAD on top of the primary WAD. Repeatable; last PWAD wins for duplicate lumps. |
| `--json` | Output JSON instead of human-readable text. Supported by most commands. |

```bash
# Load a base WAD with two PWADs and output JSON
wadcli --wad DOOM2.WAD --pwad mymap.wad --pwad fixes.wad --json info
```

---

## Top-Level Commands

### `info`

Show WAD header information, total lump count, map list, and format summary.

```bash
wadcli --wad DOOM2.WAD info
wadcli --wad DOOM2.WAD --json info
```

### `check`

Validate a WAD for common authoring errors: missing textures and flats, bad namespace markers, duplicate map names, and PNAMES mismatches.

```bash
wadcli --wad mymap.wad check
wadcli --wad DOOM2.WAD --pwad mymap.wad check
```

### `diff`

Compare two WADs and report added, removed, and changed lumps.

```bash
wadcli --wad DOOM2.WAD diff DOOM2_patched.WAD
wadcli --wad original.wad --json diff updated.wad
```

### `complevel`

Detect the compatibility level of the WAD: Vanilla, Boom, MBF, MBF21, ZDoom, or UDMF.

```bash
wadcli --wad mymap.wad complevel
```

### `convert pk3`

Convert a WAD to a PK3 archive using namespace-aware directory mapping.

```bash
wadcli --wad DOOM2.WAD convert pk3 DOOM2.pk3
```

### `convert complevel`

Downgrade a WAD to a lower compatibility level and write the result to a new file.

```bash
wadcli --wad mymap.wad convert complevel boom out.wad
```

---

## `list` Subcommands

List content from various WAD lumps. All subcommands support `--json`.

```bash
wadcli --wad DOOM2.WAD list <sub>
```

### `maps`

List all maps with thing, linedef, and sector counts. Shows ZMAPINFO title if present.

```bash
wadcli --wad DOOM2.WAD list maps
```

### `lumps`

List all directory entries with their size and offset.

```bash
wadcli --wad DOOM2.WAD list lumps
```

### `actors`

List DECORATE actor definitions: name, parent class, and DoomEdNum.

```bash
wadcli --wad mymod.wad list actors
```

### `animations`

List ANIMDEFS flat and texture animation sequences.

```bash
wadcli --wad mymod.wad list animations
```

### `flats`

List all flat names found between `F_START` and `F_END` markers.

```bash
wadcli --wad DOOM2.WAD list flats
```

### `language`

List strings from the `LANGUAGE` lump. Defaults to the `enu` locale; use `--locale` to select another.

```bash
wadcli --wad mymod.wad list language
wadcli --wad mymod.wad list language --locale deu
```

### `mapinfo`

List map entries from `MAPINFO` or `ZMAPINFO`.

```bash
wadcli --wad mymod.wad list mapinfo
```

### `music`

List music lumps with detected format and size.

```bash
wadcli --wad DOOM2.WAD list music
```

### `patches`

List patch names from `PNAMES`.

```bash
wadcli --wad DOOM2.WAD list patches
```

### `scripts`

List ACS scripts found in `BEHAVIOR` lumps across all maps.

```bash
wadcli --wad mymod.wad list scripts
```

### `sndseq`

List sound sequence definitions from `SNDSEQ`.

```bash
wadcli --wad mymod.wad list sndseq
```

### `sounds`

List DMX sound lumps with sample rate and length.

```bash
wadcli --wad DOOM2.WAD list sounds
```

### `sprites`

List sprite lumps with pixel dimensions.

```bash
wadcli --wad DOOM2.WAD list sprites
```

### `stats`

Show aggregate statistics across all maps: thing counts by category, total linedefs, sector count, secret count, and more.

```bash
wadcli --wad DOOM2.WAD list stats
wadcli --wad DOOM2.WAD --pwad mymap.wad list stats
```

### `textures`

List composite texture names and patch counts from `TEXTURE1` and `TEXTURE2`.

```bash
wadcli --wad DOOM2.WAD list textures
```

---

## `export` Subcommands

Export or render WAD content to external files. All subcommands support `--json` for metadata output where applicable.

```bash
wadcli --wad DOOM2.WAD export <sub> [args]
```

### `animation`

Render an ANIMDEFS animation sequence as an animated GIF.

```bash
wadcli --wad mymod.wad export animation FIREBLU anim.gif
```

### `colormap`

Render the `COLORMAP` lump as a PNG grid (34 light levels × 256 colours).

```bash
wadcli --wad DOOM2.WAD export colormap colormap.png
```

### `endoom`

Export the `ENDOOM` lump as a rendered ANSI image or plain text. Output path is optional; use `--text` for plain text.

```bash
wadcli --wad DOOM2.WAD export endoom endoom.png
wadcli --wad DOOM2.WAD export endoom --text endoom.txt
wadcli --wad DOOM2.WAD export endoom --text
```

### `flat`

Render a floor or ceiling flat to PNG.

```bash
wadcli --wad DOOM2.WAD export flat FLOOR4_8 floor.png
```

### `font`

Render a WAD font as a sprite-sheet PNG. Supported font names: `stcfn`, `fonta`, `fontb`.

```bash
wadcli --wad DOOM2.WAD export font stcfn font.png
```

### `lump`

Dump raw lump bytes to a file.

```bash
wadcli --wad DOOM2.WAD export lump GENMIDI genmidi.lmp
```

### `map`

Render a map to PNG. Supports `--floors`, `--sprites`, `--alpha`, `--multiplayer`, `--scale`, and `--pwad`.

```bash
wadcli --wad DOOM2.WAD export map MAP01 map01.png
wadcli --wad DOOM2.WAD export map MAP01 map01.png --floors --sprites --scale 2
```

### `music`

Export a music lump to a file. MUS lumps are converted to MIDI (`.mid`); MIDI, OGG, and MP3 lumps pass through unchanged.

```bash
wadcli --wad DOOM2.WAD export music D_RUNNIN track.mid
wadcli --wad mymod.wad export music D_TITLE title.ogg
```

### `obj`

Export a map as a 3D Wavefront OBJ mesh with materials.

```bash
wadcli --wad DOOM2.WAD export obj MAP01 map01.obj
```

### `palette`

Render `PLAYPAL` as a colour swatch PNG (14 palettes × 256 colours).

```bash
wadcli --wad DOOM2.WAD export palette playpal.png
```

### `patch`

Render any Doom-format picture or patch to PNG.

```bash
wadcli --wad DOOM2.WAD export patch TITLEPIC title.png
```

### `sound`

Export a DMX sound lump as a WAV file. Use `--raw` to dump raw DMX bytes instead.

```bash
wadcli --wad DOOM2.WAD export sound DSPISTOL pistol.wav
wadcli --wad DOOM2.WAD export sound DSPISTOL pistol.dmx --raw
```

### `sprite`

Render a sprite frame to PNG.

```bash
wadcli --wad DOOM2.WAD export sprite TROO_A1 trooper.png
```

### `texture`

Render a composite wall texture to PNG.

```bash
wadcli --wad DOOM2.WAD export texture STARTAN3 startan3.png
```

---

## `scan` Subcommands

Scan WAD content for cross-referencing and usage analysis.

```bash
wadcli --wad DOOM2.WAD scan <sub>
```

### `textures`

Report which textures and flats each map references. Flags unused assets defined in `TEXTURE1`/`TEXTURE2` or between `F_START`/`F_END` markers.

```bash
wadcli --wad DOOM2.WAD scan textures
wadcli --wad DOOM2.WAD --pwad mymap.wad scan textures
wadcli --wad mymap.wad --json scan textures
```
