"""Tests for the Doom picture format decoder."""

from PIL import Image

from wadlib.lumps.picture import Picture
from wadlib.wad import WadFile


def _first_patch_name(wad: WadFile) -> str:
    assert wad.pnames is not None
    names = wad.pnames.names
    assert len(names) > 0
    return names[0]


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_get_picture_returns_picture(doom1_wad: WadFile) -> None:
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    assert isinstance(pic, Picture)


def test_get_picture_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_picture("DOESNOTEXIST") is None


def test_picture_has_nonzero_dimensions(doom1_wad: WadFile) -> None:
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    assert pic.pic_width > 0
    assert pic.pic_height > 0


def test_picture_offsets_are_ints(doom1_wad: WadFile) -> None:
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    assert isinstance(pic.left_offset, int)
    assert isinstance(pic.top_offset, int)


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------


def test_picture_decode_returns_rgba_image(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    img = pic.decode(palette)
    assert isinstance(img, Image.Image)
    assert img.mode == "RGBA"


def test_picture_decode_correct_size(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    img = pic.decode(palette)
    assert img.size == (pic.pic_width, pic.pic_height)


def test_picture_decode_has_opaque_pixels(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    img = pic.decode(palette)
    alphas = [img.getpixel((x, y))[3] for x in range(img.width) for y in range(img.height)]
    assert any(a == 255 for a in alphas), "decoded image has no opaque pixels"


def test_picture_pixel_colours_in_range(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    name = _first_patch_name(doom1_wad)
    pic = doom1_wad.get_picture(name)
    assert pic is not None
    img = pic.decode(palette)
    for x in range(img.width):
        for y in range(img.height):
            r, g, b, a = img.getpixel((x, y))
            assert 0 <= r <= 255
            assert 0 <= g <= 255
            assert 0 <= b <= 255
            assert a in (0, 255)


def test_picture_decode_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.playpal is not None
    palette = doom2_wad.playpal.get_palette(0)
    name = _first_patch_name(doom2_wad)
    pic = doom2_wad.get_picture(name)
    assert pic is not None
    img = pic.decode(palette)
    assert isinstance(img, Image.Image)
