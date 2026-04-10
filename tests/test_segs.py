"""Tests for SEGS and SSECTORS lumps."""

from struct import calcsize

from wadlib.lumps.segs import SEG_FORMAT, SSECTOR_FORMAT, Seg, SubSector
from wadlib.wad import WadFile


def test_seg_format_size() -> None:
    assert calcsize(SEG_FORMAT) == 12


def test_ssector_format_size() -> None:
    assert calcsize(SSECTOR_FORMAT) == 4


def test_segs_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].segs is not None


def test_ssectors_attached(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.maps[0].ssectors is not None


def test_segs_non_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.maps[0].segs) > 0


def test_ssectors_non_empty(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.maps[0].ssectors) > 0


def test_seg_is_seg(freedoom1_wad: WadFile) -> None:
    s = freedoom1_wad.maps[0].segs[0]
    assert isinstance(s, Seg)


def test_ssector_is_subsector(freedoom1_wad: WadFile) -> None:
    ss = freedoom1_wad.maps[0].ssectors[0]
    assert isinstance(ss, SubSector)


def test_seg_direction_is_0_or_1(freedoom1_wad: WadFile) -> None:
    for seg in freedoom1_wad.maps[0].segs:
        assert seg.direction in (0, 1)


def test_ssector_first_seg_in_range(freedoom1_wad: WadFile) -> None:
    segs = freedoom1_wad.maps[0].segs
    for ss in freedoom1_wad.maps[0].ssectors:
        assert ss.first_seg + ss.seg_count <= len(segs)
