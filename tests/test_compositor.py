"""Tests for TextureCompositor."""

import pytest
from PIL import Image

from wadlib.compositor import TextureCompositor
from wadlib.wad import WadFile


def test_compositor_constructs(freedoom1_wad: WadFile) -> None:
    comp = TextureCompositor(freedoom1_wad)
    assert comp is not None


def test_compositor_compose_known_texture(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.texture1 is not None
    name = freedoom1_wad.texture1.textures[0].name
    comp = TextureCompositor(freedoom1_wad)
    img = comp.compose(name)
    assert img is not None
    assert isinstance(img, Image.Image)


def test_compositor_compose_returns_rgba(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.texture1 is not None
    name = freedoom1_wad.texture1.textures[0].name
    comp = TextureCompositor(freedoom1_wad)
    img = comp.compose(name)
    assert img is not None
    assert img.mode == "RGBA"


def test_compositor_compose_correct_dimensions(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.texture1 is not None
    td = freedoom1_wad.texture1.textures[0]
    comp = TextureCompositor(freedoom1_wad)
    img = comp.compose(td.name)
    assert img is not None
    assert img.size == (td.width, td.height)


def test_compositor_compose_unknown_returns_none(freedoom1_wad: WadFile) -> None:
    comp = TextureCompositor(freedoom1_wad)
    assert comp.compose("DOESNOTEXIST") is None


def test_compositor_compose_not_blank(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.texture1 is not None
    name = freedoom1_wad.texture1.textures[0].name
    comp = TextureCompositor(freedoom1_wad)
    img = comp.compose(name)
    assert img is not None
    colours = set(img.getdata())
    assert len(colours) > 1


@pytest.mark.slow
def test_compositor_compose_all_returns_dict(freedoom1_wad: WadFile) -> None:
    comp = TextureCompositor(freedoom1_wad)
    all_tex = comp.compose_all()
    assert isinstance(all_tex, dict)
    assert len(all_tex) > 0


@pytest.mark.slow
def test_compositor_compose_all_values_are_images(freedoom1_wad: WadFile) -> None:
    comp = TextureCompositor(freedoom1_wad)
    for img in comp.compose_all().values():
        assert isinstance(img, Image.Image)


def test_compositor_custom_palette(freedoom1_wad: WadFile) -> None:
    assert freedoom1_wad.playpal is not None
    assert freedoom1_wad.texture1 is not None
    palette = freedoom1_wad.playpal.get_palette(0)
    comp = TextureCompositor(freedoom1_wad, palette=palette)
    name = freedoom1_wad.texture1.textures[0].name
    img = comp.compose(name)
    assert img is not None


def test_compositor_doom2(freedoom2_wad: WadFile) -> None:
    comp = TextureCompositor(freedoom2_wad)
    assert freedoom2_wad.texture1 is not None
    first_tex = freedoom2_wad.texture1.textures[0].name
    img = comp.compose(first_tex)
    assert img is not None
    assert isinstance(img, Image.Image)
