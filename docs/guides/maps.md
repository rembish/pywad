# Maps Guides

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
