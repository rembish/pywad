"""Tests for MapRenderer and RenderOptions."""

from pathlib import Path

import pytest
from PIL import Image

from wadlib.renderer import MapRenderer, RenderOptions
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------


def test_renderer_returns_image(freedoom1_wad: WadFile) -> None:
    r = MapRenderer(freedoom1_wad.maps[0])
    img = r.render()
    assert isinstance(img, Image.Image)


def test_renderer_image_is_rgb(freedoom1_wad: WadFile) -> None:
    img = MapRenderer(freedoom1_wad.maps[0]).render()
    assert img.mode == "RGB"


def test_renderer_alpha_mode(freedoom1_wad: WadFile) -> None:
    opts = RenderOptions(alpha=True)
    img = MapRenderer(freedoom1_wad.maps[0], options=opts).render()
    assert img.mode == "RGBA"
    # Void areas outside the map should be fully transparent.
    pixels = img.getpixel((0, 0))
    assert isinstance(pixels, tuple) and pixels[3] == 0


def test_renderer_nontrivial_size(freedoom1_wad: WadFile) -> None:
    img = MapRenderer(freedoom1_wad.maps[0]).render()
    w, h = img.size
    assert w > 80 and h > 80


def test_renderer_not_blank(freedoom1_wad: WadFile) -> None:
    img = MapRenderer(freedoom1_wad.maps[0]).render()
    colours = set(img.getdata())
    assert len(colours) > 1


def test_renderer_save(freedoom1_wad: WadFile, tmp_path: Path) -> None:
    p = tmp_path / "e1m1.png"
    r = MapRenderer(freedoom1_wad.maps[0])
    r.render()
    r.save(str(p))
    assert p.exists() and p.stat().st_size > 0


# ---------------------------------------------------------------------------
# RenderOptions flags
# ---------------------------------------------------------------------------


def test_renderer_no_things(freedoom1_wad: WadFile) -> None:
    opts = RenderOptions(show_things=False)
    img = MapRenderer(freedoom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


def test_renderer_custom_scale(freedoom1_wad: WadFile) -> None:
    opts = RenderOptions(scale=0.1)
    img = MapRenderer(freedoom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


def test_renderer_floors_without_wad_skips_gracefully(freedoom1_wad: WadFile) -> None:
    """Floor rendering without a WadFile should not crash."""
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(freedoom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


@pytest.mark.slow
def test_renderer_floors_with_wad(freedoom1_wad: WadFile) -> None:
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(freedoom1_wad.maps[0], wad=freedoom1_wad, options=opts).render()
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"


@pytest.mark.slow
def test_renderer_floors_not_blank(freedoom1_wad: WadFile) -> None:
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(freedoom1_wad.maps[0], wad=freedoom1_wad, options=opts).render()
    colours = set(img.getdata())
    assert len(colours) > 5  # floor textures add many colours


# ---------------------------------------------------------------------------
# Cross-WAD smoke tests
# ---------------------------------------------------------------------------


def test_renderer_doom2(freedoom2_wad: WadFile) -> None:
    img = MapRenderer(freedoom2_wad.maps[0]).render()
    assert isinstance(img, Image.Image)


def test_renderer_hexen(hexen_wad: WadFile) -> None:
    img = MapRenderer(hexen_wad.maps[0]).render()
    assert isinstance(img, Image.Image)


def test_renderer_heretic(heretic_wad: WadFile) -> None:
    img = MapRenderer(heretic_wad.maps[0]).render()
    assert isinstance(img, Image.Image)
