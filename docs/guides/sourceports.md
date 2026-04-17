# Source Ports Guides

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
