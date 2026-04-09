"""Tests for flat (floor/ceiling texture) lump decoder."""

from PIL import Image

from wadlib.lumps.flat import FLAT_BYTES, FLAT_SIZE, Flat
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# WadFile.flats enumeration
# ---------------------------------------------------------------------------


def test_flats_returns_dict(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.flats, dict)


def test_flats_nonempty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.flats) > 0


def test_flats_values_are_flat(doom1_wad: WadFile) -> None:
    for flat in doom1_wad.flats.values():
        assert isinstance(flat, Flat)


def test_flats_doom2(doom2_wad: WadFile) -> None:
    assert len(doom2_wad.flats) > 0


# ---------------------------------------------------------------------------
# get_flat
# ---------------------------------------------------------------------------


def test_get_flat_known(doom1_wad: WadFile) -> None:
    # FLOOR0_1 is in every Doom 1 WAD
    flat = doom1_wad.get_flat("FLOOR0_1")
    assert flat is not None
    assert isinstance(flat, Flat)


def test_get_flat_case_insensitive(doom1_wad: WadFile) -> None:
    upper = doom1_wad.get_flat("FLOOR0_1")
    lower = doom1_wad.get_flat("floor0_1")
    assert upper is not None
    assert lower is not None


def test_get_flat_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_flat("DOESNOTEXIST") is None


# ---------------------------------------------------------------------------
# Flat.decode
# ---------------------------------------------------------------------------


def test_flat_decode_returns_rgb_image(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    flat = doom1_wad.get_flat("FLOOR0_1")
    assert flat is not None
    img = flat.decode(palette)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"


def test_flat_decode_correct_size(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    flat = doom1_wad.get_flat("FLOOR0_1")
    assert flat is not None
    img = flat.decode(palette)
    assert img.size == (FLAT_SIZE, FLAT_SIZE)


def test_flat_decode_pixel_colours_in_range(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    flat = doom1_wad.get_flat("FLOOR0_1")
    assert flat is not None
    img = flat.decode(palette)
    for x in range(img.width):
        for y in range(img.height):
            r, g, b = img.getpixel((x, y))
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255


def test_flat_size_constant() -> None:
    assert FLAT_BYTES == FLAT_SIZE * FLAT_SIZE == 4096
