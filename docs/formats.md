# WAD File Format Guide

This document describes the binary formats used by Doom-engine games and
understood by wadlib.  It is written for developers who want to understand
what is inside a WAD file, not just how to call the library.

---

## WAD binary structure

A WAD (Where's All the Data?) file has three sections laid out sequentially:

```
Offset  Size  Description
------  ----  -----------
0       4     Magic: "IWAD" or "PWAD" (ASCII)
4       4     Number of lumps (int32 LE)
8       4     Directory offset (int32 LE) -- byte position of the directory
12      ...   Lump data (variable length, no alignment)
...     ...   Directory entries
```

**IWAD** (Internal WAD) is the main game data file shipped by the publisher.
**PWAD** (Patch WAD) is a mod that overrides or extends an IWAD.

### Header

The header is exactly 12 bytes:

| Field | Type | Description |
|---|---|---|
| `magic` | `char[4]` | `"IWAD"` or `"PWAD"` |
| `numlumps` | `int32` | Total number of directory entries |
| `diroffset` | `int32` | Byte offset of the directory table |

wadlib reads this with `struct.unpack("<4sII", ...)`.

### Directory

The directory is an array of 16-byte entries, one per lump:

| Field | Type | Description |
|---|---|---|
| `offset` | `int32` | Byte offset of the lump data from the start of the file |
| `size` | `int32` | Size of the lump in bytes (0 for markers) |
| `name` | `char[8]` | Lump name, null-padded ASCII, uppercase |

Lump names are at most 8 characters.  Valid characters are `A-Z`, `0-9`,
`[`, `]`, `-`, `_`, and `\`.  Names are always uppercase.

### Lumps

A lump is just a blob of bytes at a given offset.  The directory tells you
where each lump starts and how large it is.  There is no internal framing
or compression in vanilla WAD files -- the format of each lump's contents
depends entirely on its name and context.

Zero-length lumps (size = 0) serve as **markers** -- they carry no data
but their position in the directory is meaningful.

---

## Lump types

### Map data lumps

A map is introduced by a marker lump whose name follows one of two
patterns:

- **Doom 1 / Heretic**: `ExMy` (e.g. `E1M1`, `E3M7`)
- **Doom 2 / Hexen / Strife**: `MAPxx` (e.g. `MAP01`, `MAP32`)

The marker is a zero-length lump.  Immediately after it come the map's
data lumps, always in the same conventional order:

| Lump | Record size | Description |
|---|---|---|
| `THINGS` | 10 bytes (Doom) / 20 bytes (Hexen) | Objects placed on the map |
| `LINEDEFS` | 14 bytes (Doom) / 16 bytes (Hexen) | Wall segments connecting vertices |
| `SIDEDEFS` | 30 bytes | Visual properties of each side of a linedef |
| `VERTEXES` | 4 bytes | 2D coordinate pairs |
| `SEGS` | 12 bytes | BSP subsegments of linedefs |
| `SSECTORS` | 4 bytes | Groups of segs forming convex sub-regions |
| `NODES` | 28 bytes | BSP tree nodes |
| `SECTORS` | 26 bytes | Floor/ceiling regions |
| `REJECT` | variable | Sector-to-sector visibility matrix |
| `BLOCKMAP` | variable | Spatial grid for collision detection |
| `BEHAVIOR` | variable | Compiled ACS scripts (Hexen format only) |

Each lump is an array of fixed-size records (except REJECT and BLOCKMAP).

#### THINGS (Doom format -- 10 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     int16   x position
2       2     int16   y position
4       2     uint16  angle (degrees, 0 = east, 90 = north)
6       2     uint16  thing type (DoomEd number)
8       2     uint16  flags (skill/multiplayer bits)
```

Flags:

| Bit | Meaning |
|---|---|
| 0x0001 | Appears on skill 1-2 |
| 0x0002 | Appears on skill 3 |
| 0x0004 | Appears on skill 4-5 |
| 0x0008 | Deaf (ambush) |
| 0x0010 | Not in single player |
| 0x0020 | Not in deathmatch (Boom) |
| 0x0040 | Not in co-op (Boom) |
| 0x0080 | Friendly (MBF) |

#### THINGS (Hexen format -- 20 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     int16   thing ID (for ACS scripts)
2       2     int16   x position
4       2     int16   y position
6       2     int16   z position (height above floor)
8       2     uint16  angle
10      2     uint16  thing type
12      2     uint16  flags
14      1     uint8   action special
15      1     uint8   arg0
16      1     uint8   arg1
17      1     uint8   arg2
18      1     uint8   arg3
19      1     uint8   arg4
```

A `BEHAVIOR` lump in the same map block signals that the map uses
Hexen format.

#### VERTEXES (4 bytes per record)

```
Offset  Size  Type   Field
------  ----  -----  -----
0       2     int16  x
2       2     int16  y
```

#### LINEDEFS (Doom format -- 14 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  start vertex index
2       2     uint16  end vertex index
4       2     uint16  flags
6       2     uint16  special type (action)
8       2     uint16  sector tag
10      2     int16   right sidedef index (-1 = none)
12      2     int16   left sidedef index (-1 = none)
```

#### LINEDEFS (Hexen format -- 16 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  start vertex index
2       2     uint16  end vertex index
4       2     uint16  flags
6       1     uint8   special type
7       1     uint8   arg0
8       1     uint8   arg1
9       1     uint8   arg2
10      1     uint8   arg3
11      1     uint8   arg4
12      2     int16   right sidedef index
14      2     int16   left sidedef index
```

#### SIDEDEFS (30 bytes per record)

```
Offset  Size  Type     Field
------  ----  -------  -----
0       2     int16    x offset
2       2     int16    y offset
4       8     char[8]  upper texture name
12      8     char[8]  lower texture name
20      8     char[8]  middle texture name
28      2     uint16   sector index
```

Texture names are null-padded ASCII.  A name of `"-"` (or all nulls)
means no texture.

#### SECTORS (26 bytes per record)

```
Offset  Size  Type     Field
------  ----  -------  -----
0       2     int16    floor height
2       2     int16    ceiling height
4       8     char[8]  floor texture name (flat)
12      8     char[8]  ceiling texture name (flat)
20      2     uint16   light level (0-255)
22      2     uint16   special type (damage, blink, etc.)
24      2     uint16   tag (for triggered actions)
```

#### SEGS (12 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  start vertex index
2       2     uint16  end vertex index
4       2     uint16  angle (binary angle measurement)
6       2     uint16  linedef index
8       2     uint16  direction (0 = same as linedef, 1 = opposite)
10      2     int16   offset (distance along linedef)
```

#### SSECTORS (4 bytes per record)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  number of segs
2       2     uint16  index of first seg
```

#### NODES (28 bytes per record)

The BSP (Binary Space Partition) tree used for rendering.

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     int16   partition line x
2       2     int16   partition line y
4       2     int16   partition line dx
6       2     int16   partition line dy
8       8     int16x4 right child bounding box (top, bottom, left, right)
16      8     int16x4 left child bounding box
24      2     uint16  right child index
26      2     uint16  left child index
```

If bit 15 (`0x8000`) of a child index is set, the remaining bits are
a subsector index.  Otherwise it is another node index.

---

## Namespace markers

Certain lump types are grouped between paired marker lumps that define
a **namespace**.  The markers themselves are zero-length lumps.

| Namespace | Start marker | End marker | Contents |
|---|---|---|---|
| Flats | `F_START` | `F_END` | Floor/ceiling textures (64x64 raw) |
| Sprites | `S_START` | `S_END` | Sprite frames (picture format) |
| Patches | `P_START` | `P_END` | Wall texture patches (picture format) |

PWADs may use alternate marker names with doubled letters:
`FF_START`/`FF_END`, `SS_START`/`SS_END`, `PP_START`/`PP_END`.
The engine merges these into the corresponding base namespace.

Heretic fonts use their own markers: `FONTA_S`/`FONTA_E` and
`FONTB_S`/`FONTB_E`.

---

## Picture format (column-based RLE)

The Doom picture format is used for sprites, weapon graphics, menu art,
and wall patches.  It stores images as columns of palette indices with
run-length encoding for transparency.

### Header (8 bytes)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  width (pixels)
2       2     uint16  height (pixels)
4       2     int16   left offset (hotspot x)
6       2     int16   top offset (hotspot y)
```

The offsets define the sprite's origin point relative to its position
in the game world.  For a sprite placed at world coordinate (x, y),
the engine draws the image so that pixel (left_offset, top_offset) is
at the screen position corresponding to (x, y).

### Column offset table

Immediately after the header is an array of `width` uint32 values.  Each
is an absolute byte offset (from the start of the lump) pointing to the
column data for that x-coordinate.

### Column data (posts)

Each column is a sequence of **posts** -- runs of opaque pixels separated
by transparent gaps:

```
[1] topdelta  (uint8)  -- y-coordinate to start drawing (0xFF = end of column)
[1] length    (uint8)  -- number of pixels in this post
[1] padding   (uint8)  -- unused byte (read and discarded)
[length] pixel data    -- palette indices (one byte each)
[1] padding   (uint8)  -- unused byte
```

The column ends when a topdelta of `0xFF` is read.  Pixels not covered
by any post are fully transparent.

This format is space-efficient for sprites with large transparent areas
(like the gaps between a monster's legs) because only opaque runs are
stored.

---

## Flat format (64x64 raw)

Flats are the simplest graphic format: exactly 4096 bytes of raw palette
indices, stored in row-major order (left to right, top to bottom).  There
is no header.

```
Byte 0    = pixel at (0, 0)
Byte 1    = pixel at (1, 0)
...
Byte 63   = pixel at (63, 0)
Byte 64   = pixel at (0, 1)
...
Byte 4095 = pixel at (63, 63)
```

Flats live between `F_START`/`F_END` markers and are always 64x64.
The size must be exactly 4096 bytes.

---

## DMX sound format

Doom uses the DMX library's digitized sound format for sound effects.

### Header (8 bytes)

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     uint16  format (always 3 for PCM)
2       2     uint16  sample rate in Hz (typically 11025)
4       4     uint32  number of samples (includes 16 bytes of padding)
```

### Data

After the header come 16 bytes of padding (silence -- value `0x80` for
unsigned 8-bit audio), followed by the actual PCM sample data.  Each
sample is one byte, unsigned 8-bit (`0x80` = silence, `0x00` = negative
peak, `0xFF` = positive peak).

The actual number of PCM samples is `num_samples - 16`.

Sound effect lump names conventionally start with `DS` (e.g. `DSPISTOL`,
`DSBAREXP`).

---

## MUS music format

MUS is a compact MIDI variant invented by id Software.  It is simpler
than Standard MIDI but carries equivalent musical information.

### Header (variable)

```
Offset  Size  Type     Field
------  ----  -------  -----
0       4     char[4]  magic: "MUS\x1A"
4       2     uint16   score length (bytes of event data)
6       2     uint16   score start offset (from start of lump)
8       2     uint16   primary channel count
10      2     uint16   secondary channel count
12      2     uint16   number of instruments
14      2     uint16   padding (always 0)
16      ...   uint16[] instrument list (one per instrument)
```

### Channel mapping

MUS uses 16 channels (0-15).  MUS channel 15 is percussion, which maps
to MIDI channel 9 (drums).  MUS channels 0-8 map to MIDI channels 0-8.
MUS channels 9-14 map to MIDI channels 10-15.

### Events

Events are encoded as single-byte descriptors followed by 0-2 data bytes:

```
Bit 7:    "last" flag -- if set, a delay follows this event
Bits 4-6: event type (0-6)
Bits 0-3: MUS channel number
```

Event types:

| Type | Name | Data bytes | Description |
|---|---|---|---|
| 0 | Release note | 1 (note) | Note off |
| 1 | Play note | 1-2 (note, [volume]) | Note on; bit 7 of note = volume follows |
| 2 | Pitch wheel | 1 (bend 0-255) | Pitch bend |
| 3 | System event | 1 (controller) | All sounds off, reset, all notes off |
| 4 | Controller | 2 (ctrl, value) | Program change (ctrl=0), volume, pan, etc. |
| 6 | Score end | 0 | End of song |

When the "last" flag is set, a variable-length delay (same encoding as
MIDI VLQ) follows the event data.  The delay is measured in ticks.

### Timing

MUS timing uses 70 ticks per quarter note at 140 BPM, giving a tempo of
approximately 428,571 microseconds per quarter note.

---

## PLAYPAL

The PLAYPAL lump contains the game's color palettes.  There are 14
palettes, each consisting of 256 RGB triples (768 bytes per palette,
10,752 bytes total).

```
Palette 0:   Normal game palette (the "real" colors)
Palettes 1-8:  Pain/pickup flash tints (red, yellow, green shifts)
Palettes 9-13: Radiation suit green tint (progressive)
```

Each color is 3 bytes: red, green, blue (0-255 each).

```
Byte 0   = palette 0, color 0, red
Byte 1   = palette 0, color 0, green
Byte 2   = palette 0, color 0, blue
Byte 3   = palette 0, color 1, red
...
Byte 767 = palette 0, color 255, blue
Byte 768 = palette 1, color 0, red
...
```

All graphics in a WAD file store palette indices, not RGB values.
You need the PLAYPAL to convert those indices to actual colors.

---

## COLORMAP

The COLORMAP lump contains 34 tables of 256 bytes each (8,704 bytes
total).  Each table maps a palette index to another palette index,
implementing light diminishing.

```
Table 0:   Full brightness (identity mapping)
Table 1:   Slightly darker
...
Table 31:  Nearly black
Table 32:  Invulnerability effect (greyscale remap)
Table 33:  All-black (some engines use as extra dark)
```

To find the darkened version of palette index `p` at light level `n`:

```python
darkened_index = colormap_data[n * 256 + p]
```

---

## PNAMES and TEXTURE1/TEXTURE2

These lumps define composite wall textures built from multiple patches.

### PNAMES

An ordered list of patch names used by the texture definitions:

```
Offset  Size  Type     Field
------  ----  -------  -----
0       4     int32    number of patches
4       8     char[8]  patch name 0
12      8     char[8]  patch name 1
...
```

### TEXTURE1 / TEXTURE2

Composite texture definitions.  TEXTURE2 exists only in Doom 1 (it holds
textures for the shareware episode).

```
Offset  Size  Type    Field
------  ----  ------  -----
0       4     int32   number of textures
4       4xN   int32[] byte offsets to each texture definition (from start of lump)
```

Each texture definition at the given offset:

```
Offset  Size  Type     Field
------  ----  -------  -----
0       8     char[8]  texture name
8       4     int32    masked (unused)
12      2     uint16   width
14      2     uint16   height
16      4     int32    column directory (unused)
20      2     int16    patch count
22      ...   patches  patch descriptors (10 bytes each)
```

Each patch descriptor:

```
Offset  Size  Type    Field
------  ----  ------  -----
0       2     int16   origin x (where to draw this patch)
2       2     int16   origin y
4       2     int16   patch index (into PNAMES)
6       2     int16   step dir (unused)
8       2     int16   colormap (unused)
```

A composite texture is assembled by drawing each patch at its origin
coordinates onto a canvas of the specified width and height.

---

## pk3 (ZIP) format

Modern source ports (GZDoom, ZDoom, Zandronum) support pk3 files, which
are standard ZIP archives with files organised by directory:

```
flats/FLOOR0_1.png       floor/ceiling textures
sprites/TROOA1.png       sprite graphics
sounds/DSPISTOL.wav      sound effects
music/D_RUNNIN.mid       music tracks
maps/MAP01.wad           embedded WAD with map geometry
patches/WALL00_1.png     wall texture patches
textures/BRICK7.png      standalone textures
lumps/PLAYPAL.lmp        raw lump data
```

pk3 files use standard ZIP compression (usually DEFLATE).  The directory
structure replaces WAD namespace markers -- files in `flats/` are flats,
files in `sprites/` are sprites, and so on.

Unlike WAD lumps, pk3 files can use standard image formats (PNG) and
standard audio formats (WAV, OGG, MP3, MIDI) directly, without
Doom-specific encoding.

wadlib provides `wad_to_pk3()` and `pk3_to_wad()` for converting between
the two formats.
