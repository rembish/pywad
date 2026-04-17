# Assets Guides

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
