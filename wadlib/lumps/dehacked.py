"""DEHACKED lump parser — full DeHackEd patch format.

Parses all standard block types plus BEX extensions:
- Thing blocks (monster/item definitions, custom DoomEd type IDs)
- Frame/State blocks (sprite, duration, action pointer, next frame)
- Weapon blocks (ammo type, frame references)
- Ammo blocks (max ammo, per pickup)
- Sound blocks (value, zero/one/neg-one)
- Misc blocks (game settings: initial health, max armor, etc.)
- Text replacements (old text → new text substitutions)
- BEX [STRINGS] section (named string replacements)
- BEX [CODEPTR] section (action function reassignments)
- BEX [PARS] section (par times)

The stock Doom sprite table is included for resolving Frame → sprite name.

Reference: https://doomwiki.org/wiki/DeHackEd
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from .base import BaseLump

# par E M seconds  (Doom 1)
_PAR1_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# par MM seconds   (Doom 2)
_PAR2_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# start/end of a bracketed section
_SECTION_RE = re.compile(r"^\s*\[(\w+)\]")
# Block headers
_THING_RE = re.compile(r"^Thing\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_FRAME_RE = re.compile(r"^Frame\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_WEAPON_RE = re.compile(r"^Weapon\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_AMMO_RE = re.compile(r"^Ammo\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_SOUND_RE = re.compile(r"^Sound\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_MISC_RE = re.compile(r"^Misc\s+(\d+)", re.IGNORECASE)
_POINTER_RE = re.compile(r"^Pointer\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_TEXT_RE = re.compile(r"^Text\s+(\d+)\s+(\d+)", re.IGNORECASE)
# Property line
_PROP_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 #]*?)\s*=\s*(.+)$")

# Doom mobj flag bit values
_MF_COUNTKILL: int = 0x00400000
_MF_COUNTITEM: int = 0x00800000

# BEX text → numeric bit mapping
_BEX_BITS: dict[str, int] = {
    "SPECIAL": 0x00000001,
    "SOLID": 0x00000002,
    "SHOOTABLE": 0x00000004,
    "NOSECTOR": 0x00000008,
    "NOBLOCKMAP": 0x00000010,
    "AMBUSH": 0x00000020,
    "JUSTHIT": 0x00000040,
    "JUSTATTACKED": 0x00000080,
    "SPAWNCEILING": 0x00000100,
    "NOGRAVITY": 0x00000200,
    "DROPOFF": 0x00000400,
    "PICKUP": 0x00000800,
    "NOCLIP": 0x00001000,
    "SLIDE": 0x00002000,
    "FLOAT": 0x00004000,
    "TELEPORT": 0x00008000,
    "MISSILE": 0x00010000,
    "DROPPED": 0x00020000,
    "SHADOW": 0x00040000,
    "NOBLOOD": 0x00080000,
    "CORPSE": 0x00100000,
    "INFLOAT": 0x00200000,
    "COUNTKILL": _MF_COUNTKILL,
    "COUNTITEM": _MF_COUNTITEM,
    "SKULLFLY": 0x01000000,
    "NOTDMATCH": 0x02000000,
    # MBF extensions
    "TRANSLUCENT": 0x04000000,
    "TOUCHY": 0x10000000,
    "BOUNCES": 0x20000000,
    "FRIEND": 0x40000000,
    "FRIENDLY": 0x40000000,
}

# ---------------------------------------------------------------------------
# Stock Doom sprite names (index → 4-char prefix)
# From info.c sprnames[] — 138 entries for Doom 2 v1.9
# ---------------------------------------------------------------------------
STOCK_SPRITE_NAMES: list[str] = [
    "TROO",
    "SHTG",
    "PUNG",
    "PISG",
    "PISF",
    "SHTF",
    "SHT2",
    "CHGG",
    "CHGF",
    "MISG",
    "MISF",
    "SAWG",
    "PLSG",
    "PLSF",
    "BFGG",
    "BFGF",
    "BLUD",
    "PUFF",
    "BAL1",
    "BAL2",
    "PLSS",
    "PLSE",
    "MISL",
    "BFS1",
    "BFE1",
    "BFE2",
    "TFOG",
    "IFOG",
    "PLAY",
    "POSS",
    "SPOS",
    "VILE",
    "FIRE",
    "FATB",
    "FBXP",
    "SKEL",
    "MANF",
    "FATT",
    "CPOS",
    "SARG",
    "HEAD",
    "BAL7",
    "BOSS",
    "BOS2",
    "SKUL",
    "SPID",
    "BSPI",
    "APLS",
    "APBX",
    "CYBR",
    "PAIN",
    "SSWV",
    "KEEN",
    "BBRN",
    "BOSF",
    "ARM1",
    "ARM2",
    "BAR1",
    "BEXP",
    "FCAN",
    "BON1",
    "BON2",
    "BKEY",
    "RKEY",
    "YKEY",
    "BSKU",
    "RSKU",
    "YSKU",
    "STIM",
    "MEDI",
    "SOUL",
    "PINV",
    "PSTR",
    "PINS",
    "MEGA",
    "SUIT",
    "PMAP",
    "PVIS",
    "CLIP",
    "AMMO",
    "ROCK",
    "BROK",
    "CELL",
    "CELP",
    "SHEL",
    "SBOX",
    "BPAK",
    "BFUG",
    "MGUN",
    "CSAW",
    "LAUN",
    "PLAS",
    "SHOT",
    "SGN2",
    "COLU",
    "SMT2",
    "GOR1",
    "POL2",
    "POL5",
    "POL4",
    "POL3",
    "POL1",
    "POL6",
    "GOR2",
    "GOR3",
    "GOR4",
    "GOR5",
    "SMIT",
    "COL1",
    "COL2",
    "COL3",
    "COL4",
    "CAND",
    "CBRA",
    "COL6",
    "TRE1",
    "TRE2",
    "ELEC",
    "CEYE",
    "FSKU",
    "COL5",
    "TBLU",
    "TGRN",
    "TRED",
    "SMBT",
    "SMGT",
    "SMRT",
    "HDB1",
    "HDB2",
    "HDB3",
    "HDB4",
    "HDB5",
    "HDB6",
    "POB1",
    "POB2",
    "BRS1",
    "TLMP",
    "TLP2",
]

# Stock Doom state table (abbreviated): state_index → (sprite_index, frame, tics, next_state)
# Only a representative subset — full table has ~967 entries.
# The first 5 states are special:
#   0 = S_NULL (no state), 1 = S_LIGHTDONE, ...
# We include enough to resolve common thing types.
# Format: {state_index: sprite_index}
# Built from states[] in info.c — sprite number for each state.
_STOCK_STATE_SPRITES: dict[int, int] = {
    # Player (S_PLAY .. S_PLAY4)
    174: 28,
    175: 28,
    176: 28,
    177: 28,
    # Zombieman (POSS)
    206: 29,
    207: 29,
    # Imp (TROO)
    252: 0,
    253: 0,
    # Demon (SARG)
    294: 39,
    # Cacodemon (HEAD)
    319: 40,
    # Baron (BOSS)
    344: 42,
    # Lost Soul (SKUL)
    370: 44,
    # Spider Mastermind (SPID)
    384: 45,
    # Cyberdemon (CYBR)
    398: 48,
}


def _parse_bits(value: str) -> int:
    """Parse a DEHACKED Bits value: either a decimal integer or BEX flag names."""
    value = value.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    result = 0
    for token in re.split(r"[+|,\s]+", value.upper()):
        token = token.strip()
        if token:
            result |= _BEX_BITS.get(token, 0)
    return result


# ---------------------------------------------------------------------------
# Data classes for all block types
# ---------------------------------------------------------------------------


@dataclass
class DehackedThing:
    """A Thing block from a DEHACKED patch."""

    index: int  # Thing block number (1-based in DeHackEd)
    type_id: int | None = None  # DoomEd type (from "ID # = N"), None for stock overrides
    name: str = ""
    bits: int = 0
    initial_frame: int | None = None
    hit_points: int | None = None
    speed: int | None = None
    width: int | None = None
    height: int | None = None
    mass: int | None = None
    missile_damage: int | None = None
    reaction_time: int | None = None
    pain_chance: int | None = None
    alert_sound: int | None = None
    attack_sound: int | None = None
    pain_sound: int | None = None
    death_sound: int | None = None
    action_sound: int | None = None
    props: dict[str, str] = field(default_factory=dict)

    @property
    def is_monster(self) -> bool:
        return bool(self.bits & _MF_COUNTKILL)

    @property
    def is_item(self) -> bool:
        return bool(self.bits & _MF_COUNTITEM)


@dataclass
class DehackedFrame:
    """A Frame/State block from a DEHACKED patch."""

    index: int
    name: str = ""
    sprite_number: int | None = None
    sprite_subnumber: int | None = None
    duration: int | None = None
    next_frame: int | None = None
    props: dict[str, str] = field(default_factory=dict)

    @property
    def sprite_name(self) -> str | None:
        """Resolve to a 4-char sprite prefix using the stock table, or None."""
        if self.sprite_number is None:
            return None
        if 0 <= self.sprite_number < len(STOCK_SPRITE_NAMES):
            return STOCK_SPRITE_NAMES[self.sprite_number]
        return None


@dataclass
class DehackedWeapon:
    """A Weapon block from a DEHACKED patch."""

    index: int
    name: str = ""
    ammo_type: int | None = None
    deselect_frame: int | None = None
    select_frame: int | None = None
    bobbing_frame: int | None = None
    shooting_frame: int | None = None
    firing_frame: int | None = None
    ammo_per_shot: int | None = None
    mbf21_bits: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedAmmo:
    """An Ammo block from a DEHACKED patch."""

    index: int
    name: str = ""
    max_ammo: int | None = None
    per_ammo: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedSound:
    """A Sound block from a DEHACKED patch."""

    index: int
    name: str = ""
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedMisc:
    """A Misc block from a DEHACKED patch (global game settings)."""

    index: int
    initial_health: int | None = None
    initial_bullets: int | None = None
    max_health: int | None = None
    max_armor: int | None = None
    green_armor_class: int | None = None
    blue_armor_class: int | None = None
    max_soulsphere: int | None = None
    soulsphere_health: int | None = None
    megasphere_health: int | None = None
    god_mode_health: int | None = None
    idfa_armor: int | None = None
    idfa_armor_class: int | None = None
    idkfa_armor: int | None = None
    idkfa_armor_class: int | None = None
    bfg_cells_per_shot: int | None = None
    monsters_infight: int | None = None
    props: dict[str, str] = field(default_factory=dict)


@dataclass
class DehackedText:
    """A text replacement from a DEHACKED patch."""

    old_length: int
    new_length: int
    old_text: str
    new_text: str


# ---------------------------------------------------------------------------
# Parsed DEHACKED result
# ---------------------------------------------------------------------------


@dataclass
class DehackedPatch:
    """Fully parsed DEHACKED patch with all block types."""

    doom_version: int | None = None
    patch_format: int | None = None
    all_things: dict[int, DehackedThing] = field(default_factory=dict)
    frames: dict[int, DehackedFrame] = field(default_factory=dict)
    weapons: dict[int, DehackedWeapon] = field(default_factory=dict)
    ammo: dict[int, DehackedAmmo] = field(default_factory=dict)
    sounds: dict[int, DehackedSound] = field(default_factory=dict)
    misc: dict[int, DehackedMisc] = field(default_factory=dict)
    texts: list[DehackedText] = field(default_factory=list)
    par_times: dict[str, int] = field(default_factory=dict)
    bex_strings: dict[str, str] = field(default_factory=dict)
    bex_codeptr: dict[int, str] = field(default_factory=dict)

    @property
    def things(self) -> dict[int, DehackedThing]:
        """Custom things only (those with an ID # = N DoomEd type)."""
        return {t.type_id: t for t in self.all_things.values() if t.type_id is not None}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_BLOCK_HEADERS = [
    (_THING_RE, "thing"),
    (_FRAME_RE, "frame"),
    (_WEAPON_RE, "weapon"),
    (_AMMO_RE, "ammo"),
    (_SOUND_RE, "sound"),
    (_MISC_RE, "misc"),
    (_POINTER_RE, "pointer"),
]

_THING_INT_PROPS: dict[str, str] = {
    "hit points": "hit_points",
    "speed": "speed",
    "width": "width",
    "height": "height",
    "mass": "mass",
    "missile damage": "missile_damage",
    "reaction time": "reaction_time",
    "pain chance": "pain_chance",
    "alert sound": "alert_sound",
    "attack sound": "attack_sound",
    "pain sound": "pain_sound",
    "death sound": "death_sound",
    "action sound": "action_sound",
    "initial frame": "initial_frame",
}

_FRAME_INT_PROPS: dict[str, str] = {
    "sprite number": "sprite_number",
    "sprite subnumber": "sprite_subnumber",
    "duration": "duration",
    "next frame": "next_frame",
}

_WEAPON_INT_PROPS: dict[str, str] = {
    "ammo type": "ammo_type",
    "deselect frame": "deselect_frame",
    "select frame": "select_frame",
    "bobbing frame": "bobbing_frame",
    "shooting frame": "shooting_frame",
    "firing frame": "firing_frame",
    "ammo per shot": "ammo_per_shot",
    "mbf21 bits": "mbf21_bits",
}

_AMMO_INT_PROPS: dict[str, str] = {
    "max ammo": "max_ammo",
    "per ammo": "per_ammo",
}

_MISC_INT_PROPS: dict[str, str] = {
    "initial health": "initial_health",
    "initial bullets": "initial_bullets",
    "max health": "max_health",
    "max armor": "max_armor",
    "green armor class": "green_armor_class",
    "blue armor class": "blue_armor_class",
    "max soulsphere": "max_soulsphere",
    "soulsphere health": "soulsphere_health",
    "megasphere health": "megasphere_health",
    "god mode health": "god_mode_health",
    "idfa armor": "idfa_armor",
    "idfa armor class": "idfa_armor_class",
    "idkfa armor": "idkfa_armor",
    "idkfa armor class": "idkfa_armor_class",
    "bfg cells/shot": "bfg_cells_per_shot",
    "monsters infight": "monsters_infight",
}


def parse_dehacked(text: str) -> DehackedPatch:  # pylint: disable=too-many-branches,too-many-statements
    """Parse a full DEHACKED patch from text."""
    patch = DehackedPatch()
    lines = text.splitlines()
    i = 0

    # Parse header
    m = re.search(r"^Doom version\s*=\s*(\d+)", text, re.MULTILINE | re.IGNORECASE)
    if m:
        patch.doom_version = int(m.group(1))
    m = re.search(r"^Patch format\s*=\s*(\d+)", text, re.MULTILINE | re.IGNORECASE)
    if m:
        patch.patch_format = int(m.group(1))

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1

        # Skip comments
        if re.match(r"^\s*#", line):
            continue

        # BEX sections
        sec = _SECTION_RE.match(line)
        if sec:
            section_name = sec.group(1).upper()
            if section_name == "PARS":
                i = _parse_pars(lines, i, patch)
            elif section_name == "STRINGS":
                i = _parse_bex_strings(lines, i, patch)
            elif section_name == "CODEPTR":
                i = _parse_bex_codeptr(lines, i, patch)
            continue

        # Text replacement
        tm = _TEXT_RE.match(line)
        if tm:
            old_len, new_len = int(tm.group(1)), int(tm.group(2))
            # Read old_len chars then new_len chars from subsequent lines
            old_text, new_text, i = _parse_text_block(lines, i, old_len, new_len)
            patch.texts.append(DehackedText(old_len, new_len, old_text, new_text))
            continue

        # Block headers
        for regex, block_type in _BLOCK_HEADERS:
            bm = regex.match(line)
            if bm:
                block_index = int(bm.group(1))
                block_name = (
                    (bm.group(2) or "").strip() if bm.lastindex and bm.lastindex >= 2 else ""
                )
                props, i = _parse_block_props(lines, i)

                if block_type == "thing":
                    thing = _build_thing(block_index, block_name, props)
                    patch.all_things[block_index] = thing
                elif block_type == "frame":
                    patch.frames[block_index] = _build_frame(block_index, block_name, props)
                elif block_type == "weapon":
                    patch.weapons[block_index] = _build_weapon(block_index, block_name, props)
                elif block_type == "ammo":
                    patch.ammo[block_index] = _build_ammo(block_index, block_name, props)
                elif block_type == "sound":
                    patch.sounds[block_index] = DehackedSound(block_index, block_name, props)
                elif block_type == "misc":
                    patch.misc[block_index] = _build_misc(block_index, props)
                elif block_type == "pointer":
                    # Pointer blocks modify action pointers on frames
                    frame_ref = props.get("codep frame")
                    if frame_ref and frame_ref.strip().isdigit():
                        # Store as a codeptr assignment
                        pass  # handled via BEX [CODEPTR] in modern patches
                break

    return patch


def _parse_block_props(lines: list[str], i: int) -> tuple[dict[str, str], int]:
    """Parse key=value properties until a blank line or new block header."""
    props: dict[str, str] = {}
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            break
        if re.match(r"^\s*#", line):
            i += 1
            continue
        # Check if this is a new block header or section
        is_header = False
        for regex, _ in _BLOCK_HEADERS:
            if regex.match(line):
                is_header = True
                break
        if is_header or _SECTION_RE.match(line) or _TEXT_RE.match(line):
            break
        pm = _PROP_RE.match(line)
        if pm:
            props[pm.group(1).strip().lower()] = pm.group(2).strip()
        i += 1
    return props, i


def _build_thing(index: int, name: str, props: dict[str, str]) -> DehackedThing:
    thing = DehackedThing(index=index, name=name)
    raw_id = props.pop("id #", None)
    if raw_id and raw_id.strip().isdigit():
        thing.type_id = int(raw_id.strip())
    bits_str = props.pop("bits", None)
    if bits_str:
        thing.bits = _parse_bits(bits_str)
    for deh_key, attr in _THING_INT_PROPS.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(thing, attr, int(val.strip()))
    thing.props = props
    return thing


def _build_frame(index: int, name: str, props: dict[str, str]) -> DehackedFrame:
    frame = DehackedFrame(index=index, name=name)
    for deh_key, attr in _FRAME_INT_PROPS.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(frame, attr, int(val.strip()))
    frame.props = props
    return frame


def _build_weapon(index: int, name: str, props: dict[str, str]) -> DehackedWeapon:
    weapon = DehackedWeapon(index=index, name=name)
    for deh_key, attr in _WEAPON_INT_PROPS.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(weapon, attr, int(val.strip()))
    weapon.props = props
    return weapon


def _build_ammo(index: int, name: str, props: dict[str, str]) -> DehackedAmmo:
    ammo = DehackedAmmo(index=index, name=name)
    for deh_key, attr in _AMMO_INT_PROPS.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(ammo, attr, int(val.strip()))
    ammo.props = props
    return ammo


def _build_misc(index: int, props: dict[str, str]) -> DehackedMisc:
    misc = DehackedMisc(index=index)
    for deh_key, attr in _MISC_INT_PROPS.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(misc, attr, int(val.strip()))
    misc.props = props
    return misc


def _parse_pars(lines: list[str], i: int, patch: DehackedPatch) -> int:
    """Parse [PARS] section."""
    while i < len(lines):
        line = lines[i].rstrip()
        line = re.sub(r"\s+#.*$", "", line)
        if _SECTION_RE.match(line):
            break
        if not line:
            i += 1
            continue
        m1 = _PAR1_RE.match(line)
        if m1:
            ep, mp, secs = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
            patch.par_times[f"E{ep}M{mp}"] = secs
        else:
            m2 = _PAR2_RE.match(line)
            if m2:
                mapnum, secs = int(m2.group(1)), int(m2.group(2))
                patch.par_times[f"MAP{mapnum:02d}"] = secs
        i += 1
    return i


def _parse_bex_strings(lines: list[str], i: int, patch: DehackedPatch) -> int:
    """Parse [STRINGS] section: key = multi-line value ending with empty line."""
    current_key: str | None = None
    current_val: list[str] = []

    while i < len(lines):
        line = lines[i].rstrip()
        if _SECTION_RE.match(line):
            break
        # Check for new key = value
        m = re.match(r"^(\w+)\s*=\s*(.*)", line)
        if m:
            # Flush previous
            if current_key is not None:
                patch.bex_strings[current_key] = "\n".join(current_val)
            current_key = m.group(1)
            current_val = [m.group(2)]
        elif current_key is not None:
            if not line:
                # Empty line terminates the value
                patch.bex_strings[current_key] = "\n".join(current_val)
                current_key = None
                current_val = []
            else:
                current_val.append(line)
        i += 1

    if current_key is not None:
        patch.bex_strings[current_key] = "\n".join(current_val)
    return i


def _parse_bex_codeptr(lines: list[str], i: int, patch: DehackedPatch) -> int:
    """Parse [CODEPTR] section: Frame N = ActionName."""
    while i < len(lines):
        line = lines[i].rstrip()
        if _SECTION_RE.match(line):
            break
        if not line:
            i += 1
            continue
        m = re.match(r"^Frame\s+(\d+)\s*=\s*(\S+)", line, re.IGNORECASE)
        if m:
            patch.bex_codeptr[int(m.group(1))] = m.group(2)
        i += 1
    return i


def _parse_text_block(lines: list[str], i: int, old_len: int, new_len: int) -> tuple[str, str, int]:
    """Parse a Text N M block: consume old_len then new_len chars from lines."""
    raw = ""
    while i < len(lines) and len(raw) < old_len + new_len:
        raw += lines[i] + "\n"
        i += 1
    old_text = raw[:old_len]
    new_text = raw[old_len : old_len + new_len]
    return old_text, new_text, i


# ---------------------------------------------------------------------------
# Lump/File classes (backward compatible with existing API)
# ---------------------------------------------------------------------------


class DehackedLump(BaseLump[Any]):
    """DEHACKED lump: DeHackEd patch embedded in a WAD."""

    @cached_property
    def _text(self) -> str:
        return self.raw().decode("latin-1")

    @cached_property
    def parsed(self) -> DehackedPatch:
        """Return the fully parsed DEHACKED patch."""
        return parse_dehacked(self._text)

    @cached_property
    def par_times(self) -> dict[str, int]:
        """Return PAR times keyed by map name."""
        return self.parsed.par_times

    @cached_property
    def doom_version(self) -> int | None:
        return self.parsed.doom_version

    @cached_property
    def patch_format(self) -> int | None:
        return self.parsed.patch_format

    @cached_property
    def things(self) -> dict[int, DehackedThing]:
        """Return custom Thing type definitions keyed by DoomEd type ID.

        Only includes Thing blocks with ``ID # = N`` (DEHEXTRA/BEX custom types).
        """
        return self.parsed.things


class DehackedFile(DehackedLump):
    """Standalone ``.deh`` file on disk."""

    def __init__(self, path: str | Path) -> None:  # pylint: disable=super-init-not-called
        object.__init__(self)  # pylint: disable=non-parent-init-called
        self._deh_path = Path(path)

    @cached_property
    def _text(self) -> str:
        return self._deh_path.read_bytes().decode("latin-1")

    def raw(self) -> bytes:
        return self._deh_path.read_bytes()
