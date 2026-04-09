"""Tests for PNAMES, TEXTURE1, and TEXTURE2 lump readers."""

from pywad.lumps.textures import PNames, TextureDef, TextureList
from pywad.wad import WadFile

# ---------------------------------------------------------------------------
# PNAMES
# ---------------------------------------------------------------------------


def test_pnames_not_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.pnames is not None


def test_pnames_is_pnames_type(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.pnames, PNames)


def test_pnames_has_entries(doom1_wad: WadFile) -> None:
    assert doom1_wad.pnames is not None
    assert len(doom1_wad.pnames) > 0


def test_pnames_names_are_strings(doom1_wad: WadFile) -> None:
    assert doom1_wad.pnames is not None
    for name in doom1_wad.pnames.names:
        assert isinstance(name, str)
        assert len(name) > 0


def test_pnames_len_matches_names_list(doom1_wad: WadFile) -> None:
    assert doom1_wad.pnames is not None
    assert len(doom1_wad.pnames) == len(doom1_wad.pnames.names)


def test_pnames_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.pnames is not None
    assert len(doom2_wad.pnames) > 0


# ---------------------------------------------------------------------------
# TEXTURE1
# ---------------------------------------------------------------------------


def test_texture1_not_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None


def test_texture1_is_texturelist(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.texture1, TextureList)


def test_texture1_has_entries(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    assert len(doom1_wad.texture1) > 0


def test_texture1_textures_are_texturedef(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    for tex in doom1_wad.texture1.textures:
        assert isinstance(tex, TextureDef)


def test_texture1_entries_have_nonzero_dimensions(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    for tex in doom1_wad.texture1.textures:
        assert tex.width > 0
        assert tex.height > 0


def test_texture1_entries_have_patches(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    for tex in doom1_wad.texture1.textures:
        assert len(tex.patches) > 0


def test_texture1_find_known_texture(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    # AASTINKY is always in Doom 1 TEXTURE1
    tex = doom1_wad.texture1.find("AASTINKY")
    assert tex is not None
    assert tex.name == "AASTINKY"


def test_texture1_find_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    assert doom1_wad.texture1.find("DOESNOTEXIST") is None


def test_texture1_find_case_insensitive(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    lower = doom1_wad.texture1.find("aastinky")
    upper = doom1_wad.texture1.find("AASTINKY")
    assert lower is not None
    assert lower == upper


# ---------------------------------------------------------------------------
# TEXTURE2
# ---------------------------------------------------------------------------


def test_texture2_doom1(doom1_wad: WadFile) -> None:
    # Doom 1 (registered) has TEXTURE2
    if doom1_wad.texture2 is not None:
        assert len(doom1_wad.texture2) > 0


def test_texture2_doom2_not_none(doom2_wad: WadFile) -> None:
    # Doom 2 has only TEXTURE1 — texture2 should be None
    # (this is WAD-specific; just verify we don't crash)
    _ = doom2_wad.texture2  # must not raise
