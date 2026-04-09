"""Tests for MapRenderer and RenderOptions."""

from pathlib import Path

from PIL import Image

from wadlib.renderer import MapRenderer, RenderOptions
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------


def test_renderer_returns_image(doom1_wad: WadFile) -> None:
    r = MapRenderer(doom1_wad.maps[0])
    img = r.render()
    assert isinstance(img, Image.Image)


def test_renderer_image_is_rgb(doom1_wad: WadFile) -> None:
    img = MapRenderer(doom1_wad.maps[0]).render()
    assert img.mode == "RGB"


def test_renderer_nontrivial_size(doom1_wad: WadFile) -> None:
    img = MapRenderer(doom1_wad.maps[0]).render()
    w, h = img.size
    assert w > 80 and h > 80


def test_renderer_not_blank(doom1_wad: WadFile) -> None:
    img = MapRenderer(doom1_wad.maps[0]).render()
    colours = set(img.getdata())
    assert len(colours) > 1


def test_renderer_save(doom1_wad: WadFile, tmp_path: Path) -> None:
    p = tmp_path / "e1m1.png"
    r = MapRenderer(doom1_wad.maps[0])
    r.render()
    r.save(str(p))
    assert p.exists() and p.stat().st_size > 0


# ---------------------------------------------------------------------------
# RenderOptions flags
# ---------------------------------------------------------------------------


def test_renderer_no_things(doom1_wad: WadFile) -> None:
    opts = RenderOptions(show_things=False)
    img = MapRenderer(doom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


def test_renderer_custom_scale(doom1_wad: WadFile) -> None:
    opts = RenderOptions(scale=0.1)
    img = MapRenderer(doom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


def test_renderer_floors_without_wad_skips_gracefully(doom1_wad: WadFile) -> None:
    """Floor rendering without a WadFile should not crash."""
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(doom1_wad.maps[0], options=opts).render()
    assert isinstance(img, Image.Image)


def test_renderer_floors_with_wad(doom1_wad: WadFile) -> None:
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(doom1_wad.maps[0], wad=doom1_wad, options=opts).render()
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"


def test_renderer_floors_not_blank(doom1_wad: WadFile) -> None:
    opts = RenderOptions(show_floors=True)
    img = MapRenderer(doom1_wad.maps[0], wad=doom1_wad, options=opts).render()
    colours = set(img.getdata())
    assert len(colours) > 5  # floor textures add many colours


# ---------------------------------------------------------------------------
# Cross-WAD smoke tests
# ---------------------------------------------------------------------------


def test_renderer_doom2(doom2_wad: WadFile) -> None:
    img = MapRenderer(doom2_wad.maps[0]).render()
    assert isinstance(img, Image.Image)


def test_renderer_hexen(hexen_wad: WadFile) -> None:
    img = MapRenderer(hexen_wad.maps[0]).render()
    assert isinstance(img, Image.Image)


def test_renderer_heretic(heretic_wad: WadFile) -> None:
    img = MapRenderer(heretic_wad.maps[0]).render()
    assert isinstance(img, Image.Image)
