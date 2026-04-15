"""Tests for the SNDINFO lump parser."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.sndinfo import SndInfo, serialize_sndinfo
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# serialize_sndinfo — unit tests, no WAD needed
# ---------------------------------------------------------------------------


def test_serialize_sndinfo_basic() -> None:
    text = serialize_sndinfo({"weapons/pistol": "DSPISTOL"})
    assert "weapons/pistol DSPISTOL" in text
    assert text.endswith("\n")


def test_serialize_sndinfo_multiple() -> None:
    text = serialize_sndinfo({"a": "A", "b": "B"})
    assert "a A" in text
    assert "b B" in text


# ---------------------------------------------------------------------------
# SndInfo.sounds — synthetic WAD tests, no real WAD needed
# ---------------------------------------------------------------------------


def _make_sndinfo_wad(sndinfo_text: str) -> str:
    """Build a minimal PWAD with a SNDINFO lump and return its path."""
    data = sndinfo_text.encode("latin-1")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"SNDINFO\x00")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def test_sndinfo_sounds_parsed() -> None:
    path = _make_sndinfo_wad("weapons/pistol DSPISTOL\ndoors/open DSDOROPN\n")
    with WadFile(path) as wad:
        assert wad.sndinfo is not None
        sounds = wad.sndinfo.sounds
        assert sounds["weapons/pistol"] == "DSPISTOL"
        assert sounds["doors/open"] == "DSDOROPN"


def test_sndinfo_skips_comments_and_blanks() -> None:
    path = _make_sndinfo_wad("; comment\n\n$global weapons/pistol DSPISTOL\nfoo BAR\n")
    with WadFile(path) as wad:
        assert wad.sndinfo is not None
        sounds = wad.sndinfo.sounds
        assert "foo" in sounds
        assert "weapons/pistol" not in sounds


def test_sndinfo_values_uppercase() -> None:
    path = _make_sndinfo_wad("foo dslower\n")
    with WadFile(path) as wad:
        assert wad.sndinfo is not None
        assert wad.sndinfo.sounds["foo"] == "DSLOWER"


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


def test_doom1_sndinfo_is_none(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.sndinfo is None
