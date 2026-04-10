"""Tests for AnimDefsLump — ANIMDEFS lump parser."""

from __future__ import annotations

from wadlib.lumps.animdefs import AnimDef, AnimDefsLump
from wadlib.wad import WadFile


def test_animdefs_not_none(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None


def test_animdefs_is_animdefs_lump(hexen_wad: WadFile) -> None:
    assert isinstance(hexen_wad.animdefs, AnimDefsLump)


def test_animations_non_empty(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    assert len(hexen_wad.animdefs.animations) > 0


def test_all_entries_are_animdef(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    for anim in hexen_wad.animdefs.animations:
        assert isinstance(anim, AnimDef)


def test_flats_non_empty(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    assert len(hexen_wad.animdefs.flats) > 0


def test_textures_non_empty(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    assert len(hexen_wad.animdefs.textures) > 0


def test_all_kinds_valid(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    for anim in hexen_wad.animdefs.animations:
        assert anim.kind in ("flat", "texture")


def test_all_animations_have_frames(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    for anim in hexen_wad.animdefs.animations:
        assert len(anim.frames) > 0, f"{anim.name} has no frames"


def test_x_001_flat_fixed_timing(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    flat = next((a for a in hexen_wad.animdefs.flats if a.name.lower() == "x_001"), None)
    assert flat is not None, "x_001 flat not found"
    assert len(flat.frames) == 4
    for frame in flat.frames:
        assert frame.min_tics == 5
        assert frame.max_tics == 5


def test_x_005_flat_random_timing(hexen_wad: WadFile) -> None:
    assert hexen_wad.animdefs is not None
    flat = next((a for a in hexen_wad.animdefs.flats if a.name.lower() == "x_005"), None)
    assert flat is not None, "x_005 flat not found"
    assert flat.is_random


def test_doom1_animdefs_is_none(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.animdefs is None
