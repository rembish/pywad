# Practical How-To Guides

Working examples for common wadlib tasks. Every snippet is self-contained
and uses only public API.

## Reading a WAD File

Open a WAD with `WadFile` to inspect its contents. Properties like `maps`,
`flats`, and `sounds` are cached and PWAD-aware.

```python
from wadlib import WadFile

with WadFile("DOOM2.WAD") as wad:
    print(wad.wad_type)          # WadType.IWAD
    print(len(wad.maps))         # 32

    for m in wad.maps:
        print(f"{m.name}: {len(list(m.things))} things, "
              f"{len(list(m.lines))} linedefs, "
              f"{len(list(m.sectors))} sectors")

    print(len(wad.flats))        # floor/ceiling textures
    print(len(wad.sprites))      # sprite frames
    print(len(wad.sounds))       # sound effects

# Layer a PWAD on top of the base WAD
with WadFile.open("DOOM2.WAD", "SIGIL_II.WAD") as wad:
    for m in wad.maps:
        print(m, len(m.things), "things")
```

## Creating a WAD from Scratch

Use `WadWriter` to build a new WAD programmatically. Provide typed map data
objects and call `save()` to write the file.

```python
from wadlib import WadWriter
from wadlib.enums import WadType
from wadlib.lumps.things import Thing, Flags
from wadlib.lumps.vertices import Vertex

writer = WadWriter(WadType.PWAD)
writer.add_map(
    "MAP01",
    things=[
        Thing(x=0, y=0, angle=0, type=1, flags=Flags(7)),        # Player 1
        Thing(x=128, y=128, angle=90, type=3004, flags=Flags(7)), # Zombieman
    ],
    vertices=[
        Vertex(0, 0), Vertex(256, 0),
        Vertex(256, 256), Vertex(0, 256),
    ],
)
writer.add_lump("DEHACKED", b"Patch File for DeHackEd v3.0\n")
writer.save("my_map.wad")

# Or serialize to bytes without writing a file
wad_bytes = writer.to_bytes()
```

## Modifying an Existing WAD

`WadArchive` follows the `zipfile.ZipFile` pattern. Open in `"a"` mode to
replace or add lumps without rebuilding the entire WAD.

```python
from wadlib import WadArchive

# Read lumps
with WadArchive("mod.wad") as wad:
    print(wad.namelist())
    playpal = wad.read("PLAYPAL")

# Append mode: modify in place
with WadArchive("mod.wad", "a") as wad:
    wad.replace("PLAYPAL", new_palette_bytes)
    wad.writestr("CREDITS", b"Made with wadlib")
    wad.remove("ENDOOM")

# Create from scratch with namespace markers
with WadArchive("patch.wad", "w") as wad:
    wad.writestr("DEHACKED", deh_bytes)
    wad.writemarker("F_START")
    wad.writestr("MYFLOOR", flat_data)
    wad.writemarker("F_END")

# Extract every lump to a directory
with WadArchive("DOOM2.WAD") as wad:
    wad.extractall("output/")
```

## Converting Between WAD and pk3

`wad_to_pk3` exports lumps into a ZIP organised by category (flats/,
sprites/, sounds/, maps/, lumps/). `pk3_to_wad` reverses the process.

```python
from wadlib.pk3 import wad_to_pk3, pk3_to_wad, Pk3Archive

wad_to_pk3("DOOM2.WAD", "doom2.pk3")   # WAD -> pk3
pk3_to_wad("mod.pk3", "mod.wad")       # pk3 -> WAD

# Read a pk3 directly
with Pk3Archive("doom2.pk3") as pk3:
    print(pk3.namelist())               # ['flats/FLOOR0_1.lmp', ...]
    for entry in pk3.infolist():
        print(f"{entry.path}  {entry.size}B  cat={entry.category}")

# Create a pk3 from scratch
with Pk3Archive("custom.pk3", "w") as pk3:
    pk3.writestr("sounds/DSPISTOL.lmp", raw_dmx_bytes)
    pk3.writestr("flats/MYFLOOR.lmp", flat_bytes)
```

## Mounting as a Filesystem

Mount any WAD as a virtual directory with auto-conversion (flats to PNG,
sounds to WAV, etc.). Requires `pip install wadlib[fuse]`.

```bash
wadmount DOOM2.WAD /mnt/doom2                          # read-write, foreground
wadmount --readonly --background DOOM2.WAD /mnt/doom2   # read-only, background

ls /mnt/doom2/flats/       # *.png     ls /mnt/doom2/sounds/      # *.wav
ls /mnt/doom2/music/       # *.mid     ls /mnt/doom2/sprites/     # *.png

# Write support -- files auto-convert back to WAD format
cp pistol.wav /mnt/doom2/sounds/DSPISTOL.wav    # WAV -> DMX
cp floor.png  /mnt/doom2/flats/MYFLOOR.png      # PNG -> flat

fusermount -u /mnt/doom2   # unmount (saves changes)
```

```python
from wadlib.fuse import mount

# Programmatic mount -- blocks until unmounted
mount("DOOM2.WAD", "/mnt/doom2", foreground=True, writable=True)
```

## Working with Graphics

Decode Doom-format pictures and flats to PIL Images, render composite
textures, and encode standard images back to WAD format.

```python
from wadlib import WadFile
from wadlib.lumps.picture import encode_picture
from wadlib.lumps.flat import encode_flat
from wadlib.compositor import TextureCompositor
from PIL import Image

with WadFile("DOOM2.WAD") as wad:
    palette = wad.playpal.get_palette(0)

    # Sprites / Pictures -> PIL Image
    sprite = wad.sprites["POSSA1"]
    img = sprite.decode(palette)              # RGBA
    img.save("zombie.png")

    # PIL Image -> Doom picture bytes
    source = Image.open("custom_sprite.png")
    picture_bytes = encode_picture(source, palette)

    # Flats (64x64 floor/ceiling textures) -> PIL Image
    flat = wad.flats["FLOOR0_1"]
    img = flat.decode(palette)                # RGB, 64x64
    img.save("floor.png")

    # PIL Image -> flat bytes
    floor_img = Image.open("my_floor.png").resize((64, 64))
    flat_bytes = encode_flat(floor_img, palette)

    # Composite wall textures (patches assembled by TEXTURE1/2 definitions)
    comp = TextureCompositor(wad)
    wall = comp.render("BRICK7")              # palette-mode Image
    wall_rgba = comp.render_rgba("BRICK7")    # RGBA
    wall_rgba.save("brick7.png")
```

## Working with Sounds and Music

Convert between WAD audio formats (DMX, MUS) and standard WAV/MIDI in
both directions.

```python
from wadlib import WadFile
from wadlib.lumps.sound import wav_to_dmx
from wadlib.lumps.mid2mus import midi_to_mus

with WadFile("DOOM2.WAD") as wad:
    # DMX -> WAV
    pistol = wad.sounds["DSPISTOL"]
    print(f"{pistol.rate} Hz, {pistol.sample_count} samples")
    wav_bytes = pistol.to_wav()
    with open("pistol.wav", "wb") as f:
        f.write(wav_bytes)

    # MUS -> MIDI
    midi_bytes = wad.music["D_RUNNIN"].to_midi()
    with open("d_runnin.mid", "wb") as f:
        f.write(midi_bytes)

# WAV -> DMX
with open("pistol.wav", "rb") as f:
    dmx_bytes = wav_to_dmx(f.read())

# MIDI -> MUS
with open("e1m1.mid", "rb") as f:
    mus_bytes = midi_to_mus(f.read())

# wad.music detects format from magic bytes — modern source-port PWADs often
# ship OGG, MP3, or raw MIDI instead of MUS.  The returned type varies:
#   Mus       — MUS format; .to_midi() converts to MIDI bytes
#   MidiLump  — raw MIDI; .data holds the bytes unchanged
#   OggLump   — raw OGG; .data holds the bytes unchanged
#   Mp3Lump   — raw MP3; .data holds the bytes unchanged
with WadFile("mod.wad") as wad:
    for name, track in wad.music.items():
        fmt = type(track).__name__
        print(f"{name}: {fmt} ({track.byte_size} bytes)")
```

## Building a Colormap

Generate COLORMAP light-level tables from a palette, optionally with a
custom invulnerability tint colour.

```python
from wadlib import WadFile
from wadlib.lumps.colormap import build_colormap, hex_to_rgb, rgb_to_hex

with WadFile("DOOM2.WAD") as wad:
    palette = wad.playpal.get_palette(0)
    colormap_bytes = build_colormap(palette)                    # standard
    colormap_bytes = build_colormap(palette, invuln_tint="#FFD700")  # gold tint

# Hex colour utilities
r, g, b = hex_to_rgb("#FF8800")       # (255, 136, 0)
r, g, b = hex_to_rgb("F80")           # short form works too
hex_str = rgb_to_hex(255, 136, 0)     # "#FF8800"
```

## Validating WAD Data

Catch naming errors, format problems, and structural issues before they
cause hard-to-debug failures in a Doom engine.

```python
from wadlib.validate import validate_name, validate_lump, validate_wad

# Name validation
issues = validate_name("TOOLONGNAME")
# [<error: TOOLONGNAME: lump name too long (11 chars, max 8)>]

# Lump data validation -- checks record size, fixed sizes, picture headers
issues = validate_lump("THINGS", b"\x00" * 15)       # not a multiple of 10
issues = validate_lump("FLOOR1", data, is_flat=True)  # must be 4096 bytes
issues = validate_lump("POSSA1", data, is_picture=True)
issues = validate_lump("THINGS", data, hexen=True)    # Hexen 20-byte records

# Whole-WAD structural validation (namespace pairing, orphan lumps)
from wadlib import WadWriter
from wadlib.enums import WadType

writer = WadWriter(WadType.PWAD)
writer.add_marker("F_START")   # forgot F_END!
issues = validate_wad(writer)
# [<error: F_START: 'F_START' marker without matching 'F_END'>]

# WadArchive validates on write by default; pass validate=False to bypass
from wadlib import WadArchive
with WadArchive("strict.wad", "w") as wad:
    wad.writestr("THINGS", things_data)   # raises InvalidLumpError if bad
```

## Compatibility Levels

Detect which source-port features a WAD requires, check whether it can be
downgraded, and apply automatic conversions where possible.

```python
from wadlib import WadFile
from wadlib.compat import (
    detect_complevel, check_downgrade,
    convert_complevel, plan_downgrade, CompLevel,
)

with WadFile("mod.wad") as wad:
    level = detect_complevel(wad)
    print(f"Detected: {level.label}")            # e.g. "Boom"

    # What blocks a downgrade to vanilla?
    issues = check_downgrade(wad, CompLevel.VANILLA)
    for issue in issues:
        print(f"[{issue.current_level.label}] {issue.message}")

    # Detailed conversion plan
    actions = plan_downgrade(wad, CompLevel.VANILLA)
    for a in actions:
        tag = "auto" if a.auto else "MANUAL"
        print(f"  [{tag}] {a.description} (lossy={a.lossy})")

    # Apply auto-convertible steps and save
    result = convert_complevel(wad, CompLevel.VANILLA, "mod_vanilla.wad")
    for desc in result.applied:
        print(f"  Applied: {desc}")
    for s in result.skipped:
        print(f"  Skipped: {s.description}")
```

## Working with UDMF Maps

Parse, build, and serialize UDMF (Universal Doom Map Format) text-based
maps used by ZDoom and other modern source ports.

```python
from wadlib.lumps.udmf import (
    parse_udmf, serialize_udmf, UdmfMap,
    UdmfThing, UdmfVertex, UdmfLinedef, UdmfSidedef, UdmfSector,
)

# Parse an existing UDMF TEXTMAP
textmap_source = """
namespace = "zdoom";
thing { x = 64.0; y = -128.0; angle = 90; type = 1; }
vertex { x = 0.0; y = 0.0; }
vertex { x = 256.0; y = 0.0; }
linedef { v1 = 0; v2 = 1; sidefront = 0; }
sidedef { sector = 0; texturemiddle = "BRICK1"; }
sector { heightfloor = 0; heightceiling = 128;
         texturefloor = "FLAT1"; textureceiling = "CEIL3_5"; }
"""
udmf = parse_udmf(textmap_source)
print(f"{udmf.namespace}: {len(udmf.things)} things, {len(udmf.vertices)} verts")

# Build a UdmfMap from scratch
m = UdmfMap(namespace="zdoom")
m.things.append(UdmfThing(x=0.0, y=0.0, angle=90, type=1))
m.vertices.extend([
    UdmfVertex(x=0.0, y=0.0), UdmfVertex(x=512.0, y=0.0),
    UdmfVertex(x=512.0, y=512.0), UdmfVertex(x=0.0, y=512.0),
])
m.linedefs.extend([
    UdmfLinedef(v1=0, v2=1, sidefront=0),
    UdmfLinedef(v1=1, v2=2, sidefront=0),
    UdmfLinedef(v1=2, v2=3, sidefront=0),
    UdmfLinedef(v1=3, v2=0, sidefront=0),
])
m.sidedefs.append(UdmfSidedef(sector=0, texturemiddle="STARTAN2"))
m.sectors.append(UdmfSector(
    heightfloor=0, heightceiling=128,
    texturefloor="FLAT1", textureceiling="CEIL3_5", lightlevel=192,
))

# Serialize and write to a WAD
textmap_output = serialize_udmf(m)

from wadlib import WadWriter
from wadlib.enums import WadType

writer = WadWriter(WadType.PWAD)
writer.add_lump("MAP01", b"")
writer.add_lump("TEXTMAP", textmap_output.encode("utf-8"))
writer.add_lump("ENDMAP", b"")
writer.save("udmf_map.wad")
```

## Scanning Texture Usage

Find which textures and flats every map actually references, and identify
defined-but-unused assets.

```python
from wadlib import WadFile
from wadlib.scanner import scan_usage, find_unused_textures, find_unused_flats

with WadFile("mymod.wad") as wad:
    usage = scan_usage(wad)
    print(f"{usage.total_unique_textures} textures, "
          f"{usage.total_unique_flats} flats, "
          f"{usage.total_unique_thing_types} thing types")

    for map_name, mu in usage.per_map.items():
        print(f"  {map_name}: {mu.thing_count} things, "
              f"{mu.linedef_count} linedefs, {len(mu.textures)} textures")

    # Textures defined in TEXTURE1/2 but never placed on any wall
    unused = find_unused_textures(wad)
    print(f"{len(unused)} unused textures: {sorted(unused)[:10]}")

    # Flats between F_START/F_END but never used
    unused_f = find_unused_flats(wad)
    print(f"{len(unused_f)} unused flats")
```

## Parsing Demo Recordings

Decode `.lmp` demo files to inspect header metadata, compute duration, and
reconstruct approximate player movement paths.

```python
from wadlib.lumps.demo import parse_demo

with open("demo1.lmp", "rb") as f:
    demo = parse_demo(f.read())

hdr = demo.header
print(f"Version {hdr.version}, Skill: {hdr.skill_name}")
print(f"Map: E{hdr.episode}M{hdr.map}, Players: {hdr.num_players}")
print(f"Duration: {demo.duration_tics} tics ({demo.duration_seconds:.1f}s)")

# Approximate movement path for player 0
path = demo.player_path(player=0)
print(f"Path: {len(path)} points, start={path[0]}, end={path[-1]}")

# Inspect individual input frames
for i, frame in enumerate(demo.tics[:5]):
    tic = frame[0]
    print(f"  Tic {i}: fwd={tic.forwardmove} side={tic.sidemove} "
          f"turn={tic.angleturn} fire={tic.fire} use={tic.use}")
```

## Game Type Detection

Automatically identify which game a WAD targets and look up thing type
names and categories.

```python
from wadlib import WadFile
from wadlib.types import detect_game, get_category, get_name, ThingCategory

with WadFile("HERETIC.WAD") as wad:
    game = detect_game(wad)
    print(f"Detected: {game.value}")             # "heretic"

    name = get_name(1, game)                     # "Player 1 Start"
    cat = get_category(3004, game)               # ThingCategory.MONSTER

    # Categorise all things in the first map
    for thing in wad.maps[0].things:
        print(f"  {thing.type}: {get_name(thing.type, game)} "
              f"[{get_category(thing.type, game).name}]")

# Works with DEHACKED custom types too
with WadFile.open("DOOM2.WAD", "rekkr.wad") as wad:
    game = detect_game(wad)
    deh = wad.dehacked.custom_things if wad.dehacked else None

    for thing in wad.maps[0].things:
        print(f"  {thing.type}: {get_name(thing.type, game, deh=deh)} "
              f"({get_category(thing.type, game, deh=deh).name})")
```

## Reading DECORATE Actors

DECORATE lumps define custom actors for ZDoom-based mods. `WadFile.decorate`
returns a PWAD-aware `DecorateLump` (or `None` if the lump is absent).

```python
from wadlib import WadFile

with WadFile.open("DOOM2.WAD", "mod.wad") as wad:
    dec = wad.decorate
    if dec:
        for actor in dec.actors:
            print(f"{actor.name} (parent={actor.parent}, "
                  f"ednum={actor.doomednum}, "
                  f"radius={actor.radius}, height={actor.height})")

# Parse a raw DECORATE text string directly
from wadlib.lumps.decorate import parse_decorate

text = """
Actor MyMonster : Zombieman 1234 {
    Radius 20
    Height 56
    States { Spawn: POSS A 10 Loop }
}
"""
actors = parse_decorate(text)
print(actors[0].name)          # "MyMonster"
print(actors[0].doomednum) # 1234
print(actors[0].parent)        # "Zombieman"
```

## Working with LANGUAGE Strings

LANGUAGE lumps store localised UI strings for ZDoom mods. The lump is
partitioned into locale sections; combined headers like `[enu default]`
expand to both locales automatically.

```python
from wadlib import WadFile

with WadFile("mod.wad") as wad:
    lang = wad.language
    if lang:
        # Look up a string in the [enu] / [default] pool
        msg = lang.lookup("PICKUPMSG", default="You got something!")
        print(msg)

        # All locales as a nested dict
        for locale, strings in lang.all_locales.items():
            print(f"[{locale}] {len(strings)} strings")

        # Per-locale access
        french = lang.strings_for("fra")
        msg_fr = lang.lookup("PICKUPMSG", locale="fra")
```

## Decoding Boom Generalized Linedefs

Boom-compatible WADs use `special_type` values >= `0x2F80` to encode
floor/ceiling/door/lift effects in bitfields rather than a flat lookup table.

```python
from wadlib import WadFile

with WadFile("boom_mod.wad") as wad:
    for m in wad.maps:
        for line in m.lines:
            gen = line.generalized       # GeneralizedLinedef | None
            if gen:
                print(f"linedef {line.special_type:#06x}: "
                      f"{gen.category.name} / {gen.trigger.name} "
                      f"/ speed={gen.speed.name}")

# Decode manually
from wadlib.lumps.boom import decode_generalized, DOOM_SECTOR_SPECIALS

gen = decode_generalized(0x6003)
print(gen.category)  # GeneralizedCategory.FLOOR
print(gen.trigger)   # GeneralizedTrigger.SR
print(gen.speed)     # GeneralizedSpeed.SLOW

# Human-readable sector special
with WadFile("DOOM2.WAD") as wad:
    for sector in wad.maps[0].sectors:
        if sector.special:
            print(f"sector {sector.special}: {sector.special_name}")
```

## Shell Completion

Tab completion for all `wadcli` subcommands, options, and context-aware
arguments is provided for Bash and Zsh.

```bash
# Bash -- add to ~/.bashrc or copy to /etc/bash_completion.d/
source /path/to/wadlib/completion/wadcli.bash

# Zsh -- add to ~/.zshrc or copy to a directory in $fpath
source /path/to/wadlib/completion/wadcli.zsh
```

After sourcing, tab completion covers subcommands, file arguments (filtered
to `.wad`/`.deh`), export flags, and font names:

```bash
wadcli --wad DOOM2.WAD export <TAB>
# map  flat  sprite  texture  patch  sound  music  colormap  palette  font ...

wadcli --wad DOOM2.WAD export font <TAB>
# stcfn  fonta  fontb
```

---

## Rendering Maps

`MapRenderer` produces a PIL Image from any parsed map entry.  `RenderOptions`
controls scale, visibility, and output format.

```python
from wadlib import WadFile
from wadlib.renderer import MapRenderer, RenderOptions

with WadFile("DOOM2.WAD") as wad:
    m = wad.maps[0]  # MAP01

    # Minimal render: dark background, thing markers, no floors
    r = MapRenderer(m, wad=wad)
    r.render()
    r.save("map01.png")

    # Full-featured render
    opts = RenderOptions(
        show_floors=True,     # fill subsectors with the sector's floor flat
        show_sprites=True,    # draw actual WAD sprites at thing positions
        alpha=True,           # RGBA output; void is transparent instead of dark
        multiplayer=False,    # exclude MP-only things (default)
        scale=0.0,            # 0 = auto-fit to 4096 px on the longer axis
        thing_scale=1.0,      # multiply the base thing-marker radius
        palette_index=0,      # PLAYPAL index (0 = standard game palette)
    )
    r = MapRenderer(m, wad=wad, options=opts)
    img = r.render()     # returns PIL Image; also stored in r.image
    r.save("map01_full.png")
    r.show()             # display in the system image viewer
```

Thing markers use category colours:

| Category | Colour | Shape |
|---|---|---|
| Player | Cyan | Direction arrow |
| Monster | Red | Direction arrow |
| Weapon | Yellow | Dot |
| Ammo | Orange | Dot |
| Health | Green | Dot |
| Armor | Blue | Dot |
| Key | Magenta | Dot |
| Powerup | White | Dot |
| Decoration | Dark grey | Dot |
| Unknown | Very dark grey | Dot |

Linedefs use automap-style colours:

| Linedef type | Colour |
|---|---|
| Solid (impassable) wall | White |
| Passable floor/step change | Yellow |
| Passable ceiling-only change | Light grey |
| Secret sector boundary | Magenta |
| Door / trigger special | Cyan |
| Plain two-sided | Grey |

---

## Working with ZMAPINFO

`ZMAPINFO` is the ZDoom extended map-info lump.  It describes map titles,
music, sky textures, episode structure, cluster intermissions, and a default
map baseline.

```python
from wadlib import WadFile

with WadFile("mod.wad") as wad:
    zi = wad.zmapinfo   # ZMapInfoLump | None
    if zi is None:
        print("No ZMAPINFO lump found")
    else:
        # Iterate all map entries
        for entry in zi.maps:
            print(f"{entry.map_name}: {entry.title!r}")
            print(f"  music={entry.music}  sky={entry.sky1}")
            print(f"  next={entry.next}  secret={entry.secretnext}")
            if entry.par:
                print(f"  par={entry.par}s")
            if entry.cluster:
                print(f"  cluster={entry.cluster}")
            # Unrecognised keys land in entry.props dict
            for key, val in entry.props.items():
                print(f"  {key}={val!r}")

        # Look up a specific map
        e1m1 = zi.get_map("E1M1")
        if e1m1:
            print(e1m1.resolved_title())   # resolves LANGUAGE lookup if needed

        # Default map settings (applied to all maps unless overridden)
        dm = zi.defaultmap
        if dm:
            print(f"default music: {dm.music}")

        # Episode definitions
        for ep in zi.episodes:
            print(f"Episode: {ep.name!r}  starts={ep.map}  pic={ep.pic_name}")

        # Cluster intermission text
        for cluster in zi.clusters:
            print(f"Cluster {cluster.cluster_num}  music={cluster.music}")
            print(f"  exit: {cluster.exittext[:40]!r}...")
            print(f"  enter: {cluster.entertext[:40]!r}...")

# Serialize entries back to ZMAPINFO text
from wadlib.lumps.zmapinfo import serialize_zmapinfo
text = serialize_zmapinfo(zi.maps)
```

| Property | Type | Description |
|---|---|---|
| `zi.maps` | `list[ZMapInfoEntry]` | All map blocks in declaration order |
| `zi.episodes` | `list[ZMapInfoEpisode]` | Episode definitions |
| `zi.clusters` | `list[ZMapInfoCluster]` | Cluster (intermission) definitions |
| `zi.defaultmap` | `ZMapInfoEntry \| None` | Baseline settings inherited by all maps |
| `zi.get_map(name)` | `ZMapInfoEntry \| None` | Look up by map name (case-insensitive) |

---

## Reading DEHACKED Patches

`WadFile.dehacked` exposes an embedded DEHACKED lump.  Use `DehackedFile` to
load a standalone `.deh` file.  Both return a `DehackedLump` whose `.parsed`
property gives the fully structured `DehackedPatch`.

```python
from wadlib import WadFile

with WadFile("DOOM2.WAD") as wad:
    deh = wad.dehacked   # DehackedLump | None
    if deh:
        patch = deh.parsed

        print(f"Doom version: {patch.doom_version}")
        print(f"Patch format: {patch.patch_format}")

        # Custom thing types — things with an ID # = N line giving a DoomEdNum
        for type_id, thing in patch.things.items():
            print(f"  EdNum {type_id}: {thing.name!r}  hp={thing.hit_points}")

        # All thing-stat patches (keyed by internal Doom thing number)
        for idx, thing in patch.all_things.items():
            if thing.hit_points is not None:
                print(f"  Thing {idx}: hp={thing.hit_points}  speed={thing.speed}")

        # Frame / state patches
        for idx, frame in patch.frames.items():
            print(f"  Frame {idx}: sprite={frame.sprite_number}  dur={frame.duration}")

        # Weapon patches
        for idx, weapon in patch.weapons.items():
            print(f"  Weapon {idx}: ammo/shot={weapon.ammo_per_shot}")

        # Ammo patches
        for idx, ammo in patch.ammo.items():
            print(f"  Ammo {idx}: max={ammo.max_ammo}  per={ammo.per_ammo}")

        # Text string replacements
        for text in patch.texts:
            print(f"  {text.original!r} -> {text.replacement!r}")

        # BEX extended string replacements (keyed by logical name)
        for key, val in patch.bex_strings.items():
            print(f"  [BEX] {key} = {val!r}")

        # BEX cheat codes ([CHEATS] section)
        for name, code in patch.cheats.items():
            print(f"  cheat {name!r} = {code!r}")

        # PAR times (keyed by "E1M1" or "MAP01")
        for map_name, secs in patch.par_times.items():
            print(f"  PAR {map_name}: {secs}s")

        # Pointer blocks (frame_index -> codepointer_frame_index)
        for frame_idx, codep in patch.pointers.items():
            print(f"  Pointer frame {frame_idx}: codep={codep}")

# Load a standalone .deh file (same API as DehackedLump)
from wadlib.lumps.dehacked import DehackedFile

deh_file = DehackedFile("my_mod.deh")
patch = deh_file.parsed
for type_id, thing in patch.things.items():
    print(f"Custom thing {type_id}: {thing.name!r}")
```

`DehackedPatch` field summary:

| Field | Type | Contents |
|---|---|---|
| `doom_version` | `int \| None` | Engine version from the patch header |
| `patch_format` | `int \| None` | Patch format version |
| `things` | `dict[int, DehackedThing]` | Custom things only (those with a DoomEdNum) |
| `all_things` | `dict[int, DehackedThing]` | Every patched thing, keyed by internal index |
| `frames` | `dict[int, DehackedFrame]` | Frame/state patches |
| `weapons` | `dict[int, DehackedWeapon]` | Weapon patches |
| `ammo` | `dict[int, DehackedAmmo]` | Ammo capacity patches |
| `sounds` | `dict[int, DehackedSound]` | Sound remap patches |
| `misc` | `dict[int, DehackedMisc]` | Misc settings (initial health, etc.) |
| `texts` | `list[DehackedText]` | Text string replacements |
| `par_times` | `dict[str, int]` | PAR times in seconds per map |
| `bex_strings` | `dict[str, str]` | BEX extended string replacements |
| `bex_codeptr` | `dict[int, str]` | BEX codepointer names |
| `pointers` | `dict[int, int]` | Pointer block (frame → codepointer frame) |
| `cheats` | `dict[str, str]` | BEX `[CHEATS]` section |

---

## Working with ANIMDEFS

`ANIMDEFS` defines flat and texture animation sequences used by Hexen and
ZDoom-based source ports.  `wad.animdefs` returns an `AnimDefsLump`.

```python
from wadlib import WadFile

with WadFile("mod.wad") as wad:
    ad = wad.animdefs   # AnimDefsLump | None
    if ad:
        print(f"{len(ad.animations)} total animation sequences")
        print(f"  {len(ad.flats)} flat animations")
        print(f"  {len(ad.textures)} texture animations")

        for anim in ad.animations:
            timing = "random" if anim.is_random else "fixed"
            print(f"  [{anim.kind}] {anim.name}: {len(anim.frames)} frames ({timing})")

            for frame in anim.frames:
                if frame.min_tics == frame.max_tics:
                    print(f"    pic {frame.pic}: {frame.min_tics} tics")
                else:
                    print(f"    pic {frame.pic}: {frame.min_tics}–{frame.max_tics} tics")

        # resolve_frames() maps Hexen-style numeric pic indices to lump names.
        # Supply the full ordered flat or texture name list as the reference.
        flat_names = list(wad.flats.keys())

        for anim in ad.flats:
            names = anim.resolve_frames(flat_names)
            if names:
                print(f"  {anim.name}: {' -> '.join(names)}")
            # Returns None if the base name is absent or any index is out of bounds

        # For texture animations, use the TEXTURE1/TEXTURE2 name order
        tex_names = [t.name for t in (wad.texture1 or {}).textures] if wad.texture1 else []
        for anim in ad.textures:
            names = anim.resolve_frames(tex_names)
            if names:
                print(f"  texture {anim.name}: {names}")
```

| Property | Type | Description |
|---|---|---|
| `ad.animations` | `list[AnimDef]` | All animation sequences (flats + textures) |
| `ad.flats` | `list[AnimDef]` | Flat animations only |
| `ad.textures` | `list[AnimDef]` | Texture animations only |
| `anim.kind` | `"flat" \| "texture"` | Resource kind |
| `anim.name` | `str` | Base lump/texture name |
| `anim.frames` | `list[AnimFrame]` | Frame sequence |
| `anim.is_random` | `bool` | `True` if any frame has variable timing |
| `anim.resolve_frames(names)` | `list[str] \| None` | Resolve pic indices to lump names |
| `frame.pic` | `int` | 1-based index from the base name |
| `frame.min_tics` | `int` | Minimum display duration in game tics |
| `frame.max_tics` | `int` | Maximum duration (equals `min_tics` for fixed timing) |

---

## Strife Conversation Scripts

Strife stores NPC dialogue in binary `SCRIPTxx` lumps (one per map) and
optionally a `DIALOGUE` lump.  wadlib exposes these through `WadFile.dialogue`
and `WadFile.strife_scripts`.

```python
from wadlib import WadFile

with WadFile("STRIFE1.WAD") as wad:
    # Primary DIALOGUE lump (falls back to first SCRIPTxx if absent)
    conv = wad.dialogue   # ConversationLump | None

    # All conversation lumps — DIALOGUE plus every SCRIPTxx
    for lump_name, lump in wad.strife_scripts.items():
        print(f"{lump_name}: {len(lump.pages)} dialogue pages")

    if conv:
        for page in conv.pages:
            print(f"Speaker (thing type {page.speaker_id}): {page.name!r}")
            if page.voice:
                print(f"  Voice lump: {page.voice!r}")
            if page.back_pic:
                print(f"  Background: {page.back_pic!r}")
            print(f"  Text: {page.text[:80]!r}...")

            # active_choices skips the five always-present slots that are empty
            for choice in page.active_choices:
                print(f"  [{choice.text!r}] -> page {choice.next}")
                # Items required to take this choice
                for item_type, amount in zip(choice.need_items, choice.need_amounts):
                    if item_type:
                        print(f"    needs thing type {item_type} × {amount}")
                # Item given on success
                if choice.give_item:
                    print(f"    gives thing type {choice.give_item}")
                if choice.objective:
                    print(f"    sets objective page {choice.objective}")

            # What the NPC drops on death
            if page.drop_item:
                print(f"  Drops thing type {page.drop_item} on death")

            # Pre-conditions: items required before this page is shown
            for item in page.check_items:
                if item:
                    print(f"  Requires thing type {item} in inventory")

# Round-trip: re-serialize pages to binary (1 516 bytes per page)
from wadlib.lumps.strife_conversation import conversation_to_bytes
raw = conversation_to_bytes(conv.pages)
```

| Field | Type | Description |
|---|---|---|
| `page.speaker_id` | `int` | Thing type of the NPC (matches thing catalog) |
| `page.name` | `str` | Display name shown in the dialogue UI |
| `page.voice` | `str` | Audio lump name to play (empty = silent) |
| `page.back_pic` | `str` | Background flat or picture lump |
| `page.text` | `str` | Main dialogue text (up to 320 characters) |
| `page.choices` | `tuple[…]` | Exactly 5 `ConversationChoice` slots |
| `page.active_choices` | `list[ConversationChoice]` | Non-empty choices only |
| `page.drop_item` | `int` | Thing type dropped when NPC dies (0 = none) |
| `page.check_items` | `tuple[int, int, int]` | Items required to trigger this page |
| `page.jump_to` | `int` | 1-based index of page to jump to first (0 = show directly) |
| `choice.text` | `str` | Button label |
| `choice.text_ok` | `str` | Response when requirements are met |
| `choice.text_no` | `str` | Response when requirements are not met |
| `choice.next` | `int` | Next page index (0 = end conversation, −1 = close immediately) |
| `choice.give_item` | `int` | Thing type given on success (0 = none) |
| `choice.need_items` | `tuple[int, int, int]` | Required inventory item types |
| `choice.need_amounts` | `tuple[int, int, int]` | Required quantities |
| `choice.objective` | `int` | Objective log page to set (0 = none) |
