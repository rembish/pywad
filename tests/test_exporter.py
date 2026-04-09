"""Tests for MapExporter."""

from pathlib import Path

from PIL import Image

from wadlib.exporter import MapExporter
from wadlib.wad import WadFile


def test_exporter_creates_image(doom1_wad: WadFile) -> None:
    exp = MapExporter(doom1_wad.maps[0])
    exp.process()
    assert isinstance(exp.im, Image.Image)


def test_exporter_image_is_rgb(doom1_wad: WadFile) -> None:
    exp = MapExporter(doom1_wad.maps[0])
    exp.process()
    assert exp.im.mode == "RGB"


def test_exporter_image_non_trivial_size(doom1_wad: WadFile) -> None:
    exp = MapExporter(doom1_wad.maps[0])
    w, h = exp.im.size
    assert w > 80 and h > 80


def test_exporter_image_not_blank(doom1_wad: WadFile) -> None:
    exp = MapExporter(doom1_wad.maps[0])
    exp.process()
    # After rendering, not all pixels should be the background colour
    pixels = set(exp.im.getdata())
    assert len(pixels) > 1


def test_exporter_save(doom1_wad: WadFile, tmp_path: Path) -> None:
    p = tmp_path / "e1m1.png"
    exp = MapExporter(doom1_wad.maps[0])
    exp.process()
    exp.save(str(p))
    assert p.exists()
    assert p.stat().st_size > 0


def test_exporter_custom_scale(doom1_wad: WadFile) -> None:
    exp = MapExporter(doom1_wad.maps[0], scale=0.1)
    exp.process()
    assert isinstance(exp.im, Image.Image)


def test_exporter_doom2(doom2_wad: WadFile) -> None:
    exp = MapExporter(doom2_wad.maps[0])
    exp.process()
    assert isinstance(exp.im, Image.Image)


def test_exporter_hexen(hexen_wad: WadFile) -> None:
    exp = MapExporter(hexen_wad.maps[0])
    exp.process()
    assert isinstance(exp.im, Image.Image)


def test_exporter_heretic(heretic_wad: WadFile) -> None:
    exp = MapExporter(heretic_wad.maps[0])
    exp.process()
    assert isinstance(exp.im, Image.Image)
