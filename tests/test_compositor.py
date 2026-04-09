"""Tests for TextureCompositor."""

from PIL import Image

from wadlib.compositor import TextureCompositor
from wadlib.wad import WadFile


def test_compositor_constructs(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    assert comp is not None


def test_compositor_compose_known_texture(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    img = comp.compose("STARTAN3")
    assert img is not None
    assert isinstance(img, Image.Image)


def test_compositor_compose_returns_rgba(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    img = comp.compose("STARTAN3")
    assert img is not None
    assert img.mode == "RGBA"


def test_compositor_compose_correct_dimensions(doom1_wad: WadFile) -> None:
    assert doom1_wad.texture1 is not None
    td = doom1_wad.texture1.find("STARTAN3")
    assert td is not None
    comp = TextureCompositor(doom1_wad)
    img = comp.compose("STARTAN3")
    assert img is not None
    assert img.size == (td.width, td.height)


def test_compositor_compose_unknown_returns_none(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    assert comp.compose("DOESNOTEXIST") is None


def test_compositor_compose_not_blank(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    img = comp.compose("STARTAN3")
    assert img is not None
    colours = set(img.getdata())
    assert len(colours) > 1


def test_compositor_compose_all_returns_dict(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    all_tex = comp.compose_all()
    assert isinstance(all_tex, dict)
    assert len(all_tex) > 0


def test_compositor_compose_all_values_are_images(doom1_wad: WadFile) -> None:
    comp = TextureCompositor(doom1_wad)
    for img in comp.compose_all().values():
        assert isinstance(img, Image.Image)


def test_compositor_custom_palette(doom1_wad: WadFile) -> None:
    assert doom1_wad.playpal is not None
    palette = doom1_wad.playpal.get_palette(0)
    comp = TextureCompositor(doom1_wad, palette=palette)
    img = comp.compose("STARTAN3")
    assert img is not None


def test_compositor_doom2(doom2_wad: WadFile) -> None:
    comp = TextureCompositor(doom2_wad)
    assert doom2_wad.texture1 is not None
    first_tex = doom2_wad.texture1.textures[0].name
    img = comp.compose(first_tex)
    assert img is not None
    assert isinstance(img, Image.Image)
