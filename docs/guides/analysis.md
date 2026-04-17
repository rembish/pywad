# Analysis Guides

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
