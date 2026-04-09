"""Tests for the PLAYPAL lump reader."""

from pywad.lumps.playpal import _NUM_PALETTES, _PALETTE_SIZE, PlayPal
from pywad.wad import WadFile


def test_playpal_not_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None


def test_playpal_is_playpal_type(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.playpal, PlayPal)


def test_playpal_num_palettes(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    assert doom1_wad.playpal.num_palettes == _NUM_PALETTES


def test_playpal_len(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    assert len(doom1_wad.playpal) == _NUM_PALETTES


def test_playpal_palette_zero_has_256_entries(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    pal = doom1_wad.playpal.get_palette(0)
    assert len(pal) == 256


def test_playpal_palette_entries_are_rgb_tuples(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    pal = doom1_wad.playpal.get_palette(0)
    for r, g, b in pal:
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


def test_playpal_get_palette_out_of_range(doom1_wad: WadFile) -> None:
    import pytest

    assert doom1_wad.playpal is not None
    with pytest.raises(IndexError):
        doom1_wad.playpal.get_palette(100)


def test_playpal_iteration_yields_palettes(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palettes = list(doom1_wad.playpal)
    assert len(palettes) == _NUM_PALETTES
    for pal in palettes:
        assert len(pal) == 256


def test_playpal_palettes_differ(doom1_wad: WadFile) -> None:
    """Palettes should not all be identical (pain/pickup tints differ)."""
    assert doom1_wad.playpal is not None
    pal0 = doom1_wad.playpal.get_palette(0)
    pal1 = doom1_wad.playpal.get_palette(1)
    assert pal0 != pal1


def test_playpal_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.playpal is not None
    assert len(doom2_wad.playpal) == _NUM_PALETTES


def test_playpal_size_constant() -> None:
    assert _PALETTE_SIZE == 256 * 3
