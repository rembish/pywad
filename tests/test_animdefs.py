"""Tests for AnimDefsLump — ANIMDEFS lump parser."""

from __future__ import annotations

from wadlib.lumps.animdefs import AnimDef, AnimDefsLump, AnimFrame
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


# ---------------------------------------------------------------------------
# AnimDef.resolve_frames — frame-index-to-name resolution (Step 8)
# ---------------------------------------------------------------------------


def _anim(kind: str, name: str, *pics: int, tics: int = 8) -> AnimDef:
    """Build a test AnimDef with fixed-timing frames."""
    return AnimDef(
        kind=kind,  # type: ignore[arg-type]
        name=name,
        frames=[AnimFrame(pic=p, min_tics=tics, max_tics=tics) for p in pics],
    )


class TestResolveFrames:
    """Unit tests for AnimDef.resolve_frames()."""

    def test_basic_three_frame_flat(self) -> None:
        flat_names = ["NUKAGE1", "NUKAGE2", "NUKAGE3", "BLOOD1"]
        anim = _anim("flat", "NUKAGE1", 1, 2, 3)
        assert anim.resolve_frames(flat_names) == ["NUKAGE1", "NUKAGE2", "NUKAGE3"]

    def test_single_frame_returns_base_name(self) -> None:
        anim = _anim("flat", "SLIME01", 1)
        names = ["SLIME01", "SLIME02"]
        assert anim.resolve_frames(names) == ["SLIME01"]

    def test_base_not_in_list_returns_none(self) -> None:
        anim = _anim("flat", "MISSING", 1, 2)
        assert anim.resolve_frames(["FLAT01", "FLAT02"]) is None

    def test_frame_index_out_of_bounds_returns_none(self) -> None:
        anim = _anim("flat", "FLAT01", 1, 2, 99)  # pic 99 way out of range
        assert anim.resolve_frames(["FLAT01", "FLAT02"]) is None

    def test_case_insensitive_base_lookup(self) -> None:
        anim = _anim("flat", "nukage1", 1, 2)
        names = ["NUKAGE1", "NUKAGE2"]
        assert anim.resolve_frames(names) == ["NUKAGE1", "NUKAGE2"]

    def test_base_at_middle_of_list(self) -> None:
        anim = _anim("flat", "B", 1, 2)
        names = ["A", "B", "C", "D"]
        assert anim.resolve_frames(names) == ["B", "C"]

    def test_empty_frames_returns_empty_list(self) -> None:
        anim = AnimDef(kind="flat", name="FLAT01", frames=[])
        assert anim.resolve_frames(["FLAT01", "FLAT02"]) == []

    def test_texture_animation(self) -> None:
        tex_names = ["ANIMTEX1", "ANIMTEX2", "ANIMTEX3"]
        anim = _anim("texture", "ANIMTEX1", 1, 2, 3)
        assert anim.resolve_frames(tex_names) == ["ANIMTEX1", "ANIMTEX2", "ANIMTEX3"]

    def test_pic_one_always_maps_to_base(self) -> None:
        names = ["X_001", "X_002", "X_003", "X_004"]
        anim = _anim("flat", "X_001", 1)
        result = anim.resolve_frames(names)
        assert result == ["X_001"]

    def test_random_timing_frames_resolved_by_pic(self) -> None:
        """resolve_frames uses pic index, ignoring timing randomness."""
        anim = AnimDef(
            kind="flat",
            name="BLOOD1",
            frames=[
                AnimFrame(pic=1, min_tics=3, max_tics=8),
                AnimFrame(pic=2, min_tics=3, max_tics=8),
            ],
        )
        names = ["BLOOD1", "BLOOD2", "BLOOD3"]
        assert anim.resolve_frames(names) == ["BLOOD1", "BLOOD2"]
