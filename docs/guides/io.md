# I/O Guides

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
