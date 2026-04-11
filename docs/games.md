# Game-Specific Reference

wadlib supports the classic id Tech 1 games and their derivatives, with
game-aware thing type catalogs, format detection, and source port
compatibility handling.

---

## Supported Games

### Doom / Doom II

- **Map format:** Binary (10-byte things, 14-byte linedefs)
- **Map naming:** `E1M1`--`E4M9` (Doom / Ultimate Doom), `MAP01`--`MAP32` (Doom II)
- **Thing types:** 124 entries (monsters, weapons, ammo, decorations, powerups)
- **Key lumps:** `PLAYPAL` (14 palettes), `COLORMAP` (34 light-level tables),
  `PNAMES` (patch name list), `TEXTURE1`/`TEXTURE2` (composite wall textures)
- **Audio:** MUS music format (`D_E1M1`, etc.), DMX digitised sounds (`DS*` lumps)
- **Graphics:** Doom picture format (column-based, palette-indexed), 64x64 raw flats
- **HUD font:** `STCFN` glyphs keyed by ASCII ordinal
- **IWAD files:** `DOOM.WAD`, `DOOM2.WAD`

```python
from wadlib import WadFile

with WadFile("DOOM2.WAD") as wad:
    print(len(wad.maps))           # 32
    print(wad.maps[0])             # MAP01
    print(len(wad.maps[0].things)) # thing count for MAP01
    pal = wad.playpal.get_palette(0)
    tex = wad.texture1              # TextureList from TEXTURE1
```

### Heretic

- **Map format:** Same binary format as Doom (10-byte things, 14-byte linedefs)
- **Thing types:** 96 entries -- IDs are **incompatible** with Doom
  (e.g. type 5 = Fire Gargoyle in Heretic, Blue Keycard in Doom)
- **Detection heuristic:** Presence of `IMPX` sprite prefix in WAD sprite namespace
- **Fonts:** `FONTA` (large) and `FONTB` (small) bitmap fonts
- **Unique keys:** Green Key, Blue Key, Yellow Key (types 73, 79, 80)
- **Unique weapons:** Dragon Claw, Ethereal Crossbow, Firemace, Phoenix Rod,
  Hellstaff, Gauntlets of the Necromancer
- **Monsters:** Fire Gargoyle, Iron Lich, D'Sparil, Maulotaur, Disciple,
  Nitrogolem, Undead Warrior, Weredragon, Sabreclaw, Ophidian, and ghost variants
- **IWAD file:** `HERETIC.WAD`

```python
from wadlib import WadFile

with WadFile("HERETIC.WAD") as wad:
    print(wad.fonta)   # dict[int, Picture] -- large font glyphs
    print(wad.fontb)   # dict[int, Picture] -- small font glyphs
```

### Hexen

- **Map format:** Extended binary -- 20-byte things, 16-byte linedefs
  - Things add: `tid` (thing ID for ACS), `z` (height offset), `action`
    (special number), `arg0`--`arg4`
  - Linedefs add: `special_type`, `arg0`--`arg4` (replaces sector tag)
- **Detection heuristic:** Things in map data have `arg0` attribute (Hexen thing format)
- **Thing types:** 242 entries (monsters, 3-class weapons, puzzle items, keys,
  mana, extensive decorations)
- **Key lumps:** `BEHAVIOR` (compiled ACS bytecode), `SNDSEQ` (sound sequence
  scripts), `MAPINFO` (map titles, music, sky textures)
- **Puzzle items:** Yorick's Skull, Heart of D'Sparil, Ruby/Emerald/Sapphire
  Planets, Clock Gears, Flame Mask, Glaive Seal, Holy Relic, and more
- **Player classes:** Fighter (start 1), Cleric (start 2), Mage (start 3),
  plus player starts 5--8 via types 9100--9103
- **IWAD file:** `HEXEN.WAD`

```python
from wadlib.lumps.hexen import HexenThing, HexenLineDef

# Hexen things have extra fields compared to Doom things:
# tid, x, y, z, angle, type, flags, action, arg0..arg4
t = HexenThing(tid=1, x=0, y=0, z=0, angle=0, type=107,
               flags=7, action=0, arg0=0, arg1=0, arg2=0, arg3=0, arg4=0)
raw = t.to_bytes()   # 20 bytes
```

### Strife

- **Map format:** Standard Doom binary format (10-byte things, 14-byte linedefs)
- **Thing types:** 262 entries -- the largest catalog of any supported game
- **Detection heuristic:** Presence of `AGRD` sprite prefix (Acolyte Guard)
- **Quest NPCs:** Macil, Bar Keeper, Armorer, Medic, Weapon Smith, Surgery Crab,
  Oracle -- categorised as decorations (friendly/non-combat)
- **Acolyte variants:** 10 colour variants (Tan, Shadow, Red, Rust, Gray, Dark Green,
  Gold, Blue, Light Green, Acolyte-to-Be) -- all use `AGRD` sprite
- **Peasant variants:** 22 variants -- all use `PEAS` sprite
- **Rebel variants:** 6 variants -- all use `HMN1` sprite
- **Multiple key types:** 16 keys including Silver, Brass, Gold, Oracle Key,
  Order Key, ID Badge, Passcard, Crystal Keys, Chapel Key, Factory Key, and more
- **Currency system:** Coin, Gold (10), Gold (25), Gold (50)
- **IWAD file:** `STRIFE1.WAD`

---

## Source Port Compatibility

wadlib detects and tracks compatibility levels through the `CompLevel` enum,
ordered from most restrictive to most permissive.

### Vanilla Doom

- 16-bit indices for all map structures
- Basic linedef specials (0--141)
- 64KB maximum `BLOCKMAP` size
- Static limits: 32768 segs/subsectors/nodes/vertices/linedefs/sidedefs, 256 sectors
- Standard `DEHACKED` patches for minor behaviour tweaks

### Boom

- **Generalized linedefs:** linedef specials >= `0x2F80` encode trigger/effect
  combinations in bitfields
- **`ANIMATED` lump:** Binary animation definitions (replaces hardcoded flat/texture
  animation sequences)
- **`SWITCHES` lump:** Binary switch texture pair definitions
- **Extended thing flags:** `NOT_DEATHMATCH` (bit 5, `0x0020`),
  `NOT_COOP` (bit 6, `0x0040`)
- **Extended `DEHACKED`** with longer string replacements

### MBF / MBF21

- **`FRIENDLY` thing flag** (bit 7, `0x0080`) -- monsters that fight on the
  player's side
- **Helper Dog** (thing type 888, sprite `DOGS`) -- recognised automatically
  without a `DEHACKED` declaration
- **MBF codepointers** for custom actor behaviour
- **MBF21** adds extended thing/linedef flags and new codepointers

### ZDoom / GZDoom

- **`ZMAPINFO`** -- extended map information (string map names, music, sky textures)
- **`ZNODES`** -- compressed extended BSP nodes
- **`SNDINFO`** -- sound name-to-lump mappings
- **`LANGUAGE`** -- string localisation tables
- **`DECORATE`** -- actor definitions with new DoomEdNums
- **`ZSCRIPT`** -- advanced scripting (ZScript actors)
- **`GLDEFS`** -- dynamic light definitions
- **`TEXTURES` lump** -- ZDoom-format composite texture definitions
- **pk3 archives** -- ZIP-based WAD packages

### UDMF

- **Text-based maps** via `TEXTMAP` lump (replaces all binary map lumps)
- **Floating-point coordinates** (no integer truncation)
- **Unlimited custom properties** per map element
- **`ENDMAP` marker** terminates the TEXTMAP block

---

## Game Detection

wadlib automatically identifies which game a WAD targets using fast heuristics
that inspect map data structure and sprite namespaces -- no full map loading
required.

```python
from wadlib import WadFile
from wadlib.types import detect_game, GameType

with WadFile("HEXEN.WAD") as wad:
    game = detect_game(wad)
    print(game)             # GameType.HEXEN
    print(game.value)       # "hexen"
```

Detection logic (checked in order):

| Check | Result |
|---|---|
| Any map thing has `arg0` attribute (20-byte Hexen thing format) | `GameType.HEXEN` |
| Sprite namespace contains `AGRD` prefix | `GameType.STRIFE` |
| Sprite namespace contains `IMPX` prefix | `GameType.HERETIC` |
| None of the above | `GameType.DOOM` |

Once detected, the game type selects the correct thing type catalog for
name lookups, category classification, and sprite prefix resolution:

```python
from wadlib.types import detect_game, get_name, get_category, get_sprite_prefix

with WadFile("HERETIC.WAD") as wad:
    game = detect_game(wad)              # GameType.HERETIC
    print(get_name(5, game))             # "Fire Gargoyle"
    print(get_category(5, game))         # ThingCategory.MONSTER
    print(get_sprite_prefix(5, game))    # "IMPX"

    # Same type ID in Doom means something completely different:
    print(get_name(5, GameType.DOOM))    # "Blue Keycard"
    print(get_category(5, GameType.DOOM))# ThingCategory.KEY
```

---

## Compatibility Level Hierarchy

The `CompLevel` enum is an `IntEnum` -- levels are directly comparable with
standard operators. Higher values are more permissive.

```python
from wadlib.compat import CompLevel

# Ordering (strictest -> most permissive):
# VANILLA(0) < LIMIT_REMOVING(1) < BOOM(2) < MBF(3) < MBF21(4) < ZDOOM(5) < UDMF(6)

assert CompLevel.VANILLA < CompLevel.BOOM
assert CompLevel.UDMF > CompLevel.ZDOOM
```

| Value | Name | Label | Description |
|---|---|---|---|
| 0 | `VANILLA` | Vanilla Doom | Original engine limits, 16-bit indices, basic linedef specials |
| 1 | `LIMIT_REMOVING` | Limit-removing | Vanilla format with static limits removed |
| 2 | `BOOM` | Boom | Generalized linedefs, ANIMATED/SWITCHES, NOT_DM/NOT_COOP flags |
| 3 | `MBF` | MBF | FRIENDLY flag, Helper Dog (888), MBF codepointers |
| 4 | `MBF21` | MBF21 | Extended thing/linedef flags, new codepointers |
| 5 | `ZDOOM` | ZDoom | ZMAPINFO, ZNODES, SNDINFO, DECORATE, LANGUAGE, GLDEFS |
| 6 | `UDMF` | UDMF | Text-based TEXTMAP maps, floating-point coords, unlimited properties |

Detect and convert between levels:

```python
from wadlib import WadFile
from wadlib.compat import detect_complevel, check_downgrade, convert_complevel, CompLevel

with WadFile("mod.wad") as wad:
    level = detect_complevel(wad)
    print(f"Detected: {level.label}")         # e.g. "Boom"

    # Check what prevents downgrading to vanilla
    issues = check_downgrade(wad, CompLevel.VANILLA)
    for issue in issues:
        print(f"  [{issue.current_level.label}] {issue.message}")

    # Auto-convert where possible (strips lumps, clears flags)
    result = convert_complevel(wad, CompLevel.VANILLA, "vanilla_mod.wad")
    print(f"Applied: {result.applied}")
    print(f"Skipped: {[a.description for a in result.skipped]}")
```

---

## Thing Type Coverage

| Game | Catalog entries | Key sprite prefixes | IWAD |
|---|---|---|---|
| Doom / Doom II | 124 | `POSS`, `TROO`, `SARG`, `BOSS`, `CYBR`, `PLAY` | `DOOM.WAD` / `DOOM2.WAD` |
| Heretic | 96 | `IMPX`, `HEAD`, `MNTR`, `SRCR`, `WZRD`, `KNIG` | `HERETIC.WAD` |
| Hexen | 242 | `CENT`, `BISH`, `ETTN`, `FDMN`, `KORX`, `SORC` | `HEXEN.WAD` |
| Strife | 262 | `AGRD`, `PEAS`, `HMN1`, `ROB1`, `ROB2`, `ALN1` | `STRIFE1.WAD` |

### PWAD Custom Types (DEHEXTRA / MBF21)

PWADs that define new monsters or decorations beyond the base game's catalog
embed definitions in a `DEHACKED` lump using the `ID # = N` extension.  wadlib
reads these automatically -- custom things render with the correct colour on
map exports rather than appearing as blank grey dots.

| PWAD | Custom types detected |
|---|---|
| REKKR | 633, 654, 666, 668, 699, 750, ... (15 types) |
| Eviternity | 140--144, 4901--4902 (7 types) |

MBF-standard type 888 (Helper Dog, sprite `DOGS`) is recognised without
requiring a `DEHACKED` declaration.

---

## Category System

Every thing type is classified into one of ten categories via `ThingCategory`:

| Category | Typical use | Example (Doom) |
|---|---|---|
| `PLAYER` | Player spawn points | Player 1--4 Start |
| `MONSTER` | Hostile actors | Imp, Cyberdemon, Baron of Hell |
| `WEAPON` | Pickup weapons | Shotgun, BFG 9000, Super Shotgun |
| `AMMO` | Ammunition pickups | Ammo Clip, Box of Rockets |
| `HEALTH` | Health items | Stimpack, Medikit, Soulsphere |
| `ARMOR` | Armor items | Green Armor, Blue Armor, Armor Bonus |
| `KEY` | Key pickups | Blue Keycard, Red Skull Key |
| `POWERUP` | Power-up items | Invulnerability, Berserk Pack |
| `DECORATION` | Scenery and markers | Barrel, Candle, Teleport Landing |
| `UNKNOWN` | Unrecognised type IDs | Any ID not in the current game's catalog |

```python
from wadlib.types import get_category, ThingCategory, GameType

cat = get_category(3001, GameType.DOOM)      # ThingCategory.MONSTER ("Imp")
cat = get_category(3001, GameType.HEXEN)      # ThingCategory.DECORATION ("Polyobject Start Spot")
cat = get_category(99999, GameType.DOOM)      # ThingCategory.UNKNOWN
```
