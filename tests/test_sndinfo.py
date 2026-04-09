"""Tests for the SNDINFO lump parser."""
from __future__ import annotations

from wadlib.lumps.sndinfo import SndInfo
from wadlib.wad import WadFile


def test_hexen_sndinfo_not_none(hexen_wad: WadFile) -> None:
    assert hexen_wad.sndinfo is not None


def test_hexen_sndinfo_type(hexen_wad: WadFile) -> None:
    assert isinstance(hexen_wad.sndinfo, SndInfo)


def test_hexen_sndinfo_sounds_nonempty(hexen_wad: WadFile) -> None:
    assert hexen_wad.sndinfo is not None
    sounds = hexen_wad.sndinfo.sounds
    assert isinstance(sounds, dict)
    assert len(sounds) > 0


def test_hexen_sndinfo_values_uppercase(hexen_wad: WadFile) -> None:
    assert hexen_wad.sndinfo is not None
    for value in hexen_wad.sndinfo.sounds.values():
        assert value == value.upper(), f"Expected uppercase lump name, got: {value!r}"


def test_hexen_sndinfo_known_mapping(hexen_wad: WadFile) -> None:
    assert hexen_wad.sndinfo is not None
    sounds = hexen_wad.sndinfo.sounds
    assert sounds.get("PlayerFighterNormalDeath") == "FGTDDTH"


def test_doom1_sndinfo_is_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.sndinfo is None
