"""DEHACKED text parser — converts raw patch text into structured data."""

from __future__ import annotations

import re

from .data import parse_bits
from .types import (
    DehackedAmmo,
    DehackedFrame,
    DehackedMisc,
    DehackedPatch,
    DehackedSound,
    DehackedText,
    DehackedThing,
    DehackedWeapon,
)

# Regex patterns
_PAR1_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
_PAR2_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*\[(\w+)\]")
_THING_RE = re.compile(r"^Thing\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_FRAME_RE = re.compile(r"^Frame\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_WEAPON_RE = re.compile(r"^Weapon\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_AMMO_RE = re.compile(r"^Ammo\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_SOUND_RE = re.compile(r"^Sound\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_MISC_RE = re.compile(r"^Misc\s+(\d+)", re.IGNORECASE)
_POINTER_RE = re.compile(r"^Pointer\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
_TEXT_RE = re.compile(r"^Text\s+(\d+)\s+(\d+)", re.IGNORECASE)
_PROP_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 #]*?)\s*=\s*(.+)$")

_BLOCK_HEADERS = [
    (_THING_RE, "thing"),
    (_FRAME_RE, "frame"),
    (_WEAPON_RE, "weapon"),
    (_AMMO_RE, "ammo"),
    (_SOUND_RE, "sound"),
    (_MISC_RE, "misc"),
    (_POINTER_RE, "pointer"),
]

# Property name -> dataclass attribute mappings
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

    m = re.search(r"^Doom version\s*=\s*(\d+)", text, re.MULTILINE | re.IGNORECASE)
    if m:
        patch.doom_version = int(m.group(1))
    m = re.search(r"^Patch format\s*=\s*(\d+)", text, re.MULTILINE | re.IGNORECASE)
    if m:
        patch.patch_format = int(m.group(1))

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1

        if re.match(r"^\s*#", line):
            continue

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

        tm = _TEXT_RE.match(line)
        if tm:
            old_len, new_len = int(tm.group(1)), int(tm.group(2))
            old_text, new_text, i = _parse_text_block(lines, i, old_len, new_len)
            patch.texts.append(DehackedText(old_len, new_len, old_text, new_text))
            continue

        for regex, block_type in _BLOCK_HEADERS:
            bm = regex.match(line)
            if bm:
                block_index = int(bm.group(1))
                block_name = (
                    (bm.group(2) or "").strip() if bm.lastindex and bm.lastindex >= 2 else ""
                )
                props, i = _parse_block_props(lines, i)
                _dispatch_block(patch, block_type, block_index, block_name, props)
                break

    return patch


def _dispatch_block(
    patch: DehackedPatch, block_type: str, index: int, name: str, props: dict[str, str]
) -> None:
    if block_type == "thing":
        patch.all_things[index] = _build_thing(index, name, props)
    elif block_type == "frame":
        patch.frames[index] = _build_frame(index, name, props)
    elif block_type == "weapon":
        patch.weapons[index] = _build_weapon(index, name, props)
    elif block_type == "ammo":
        patch.ammo[index] = _build_ammo(index, name, props)
    elif block_type == "sound":
        patch.sounds[index] = DehackedSound(index, name, props)
    elif block_type == "misc":
        patch.misc[index] = _build_misc(index, props)


def _parse_block_props(lines: list[str], i: int) -> tuple[dict[str, str], int]:
    props: dict[str, str] = {}
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            break
        if re.match(r"^\s*#", line):
            i += 1
            continue
        is_header = any(regex.match(line) for regex, _ in _BLOCK_HEADERS)
        if is_header or _SECTION_RE.match(line) or _TEXT_RE.match(line):
            break
        pm = _PROP_RE.match(line)
        if pm:
            props[pm.group(1).strip().lower()] = pm.group(2).strip()
        i += 1
    return props, i


def _set_int_props(obj: object, props: dict[str, str], mapping: dict[str, str]) -> None:
    for deh_key, attr in mapping.items():
        val = props.pop(deh_key, None)
        if val and val.strip().lstrip("-").isdigit():
            setattr(obj, attr, int(val.strip()))


def _build_thing(index: int, name: str, props: dict[str, str]) -> DehackedThing:
    thing = DehackedThing(index=index, name=name)
    raw_id = props.pop("id #", None)
    if raw_id and raw_id.strip().isdigit():
        thing.type_id = int(raw_id.strip())
    bits_str = props.pop("bits", None)
    if bits_str:
        thing.bits = parse_bits(bits_str)
    _set_int_props(thing, props, _THING_INT_PROPS)
    thing.props = props
    return thing


def _build_frame(index: int, name: str, props: dict[str, str]) -> DehackedFrame:
    frame = DehackedFrame(index=index, name=name)
    _set_int_props(frame, props, _FRAME_INT_PROPS)
    frame.props = props
    return frame


def _build_weapon(index: int, name: str, props: dict[str, str]) -> DehackedWeapon:
    weapon = DehackedWeapon(index=index, name=name)
    _set_int_props(weapon, props, _WEAPON_INT_PROPS)
    weapon.props = props
    return weapon


def _build_ammo(index: int, name: str, props: dict[str, str]) -> DehackedAmmo:
    ammo_obj = DehackedAmmo(index=index, name=name)
    _set_int_props(ammo_obj, props, _AMMO_INT_PROPS)
    ammo_obj.props = props
    return ammo_obj


def _build_misc(index: int, props: dict[str, str]) -> DehackedMisc:
    misc = DehackedMisc(index=index)
    _set_int_props(misc, props, _MISC_INT_PROPS)
    misc.props = props
    return misc


def _parse_pars(lines: list[str], i: int, patch: DehackedPatch) -> int:
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
    current_key: str | None = None
    current_val: list[str] = []

    while i < len(lines):
        line = lines[i].rstrip()
        if _SECTION_RE.match(line):
            break
        m = re.match(r"^(\w+)\s*=\s*(.*)", line)
        if m:
            if current_key is not None:
                patch.bex_strings[current_key] = "\n".join(current_val)
            current_key = m.group(1)
            current_val = [m.group(2)]
        elif current_key is not None:
            if not line:
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
    raw = ""
    while i < len(lines) and len(raw) < old_len + new_len:
        raw += lines[i] + "\n"
        i += 1
    old_text = raw[:old_len]
    new_text = raw[old_len : old_len + new_len]
    return old_text, new_text, i
