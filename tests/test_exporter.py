"""Tests for MapExporter backward-compatibility shim (deprecated)."""

import warnings
from pathlib import Path

from PIL import Image

from wadlib.exporter import MapExporter
from wadlib.wad import WadFile


def test_exporter_emits_deprecation_warning(freedoom1_wad: WadFile) -> None:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        MapExporter(freedoom1_wad.maps[0])
        assert any(issubclass(warning.category, DeprecationWarning) for warning in w)


def test_exporter_still_creates_image(freedoom1_wad: WadFile) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        exp = MapExporter(freedoom1_wad.maps[0])
        exp.process()
        assert isinstance(exp.im, Image.Image)


def test_exporter_save_still_works(freedoom1_wad: WadFile, tmp_path: Path) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        p = tmp_path / "e1m1.png"
        exp = MapExporter(freedoom1_wad.maps[0])
        exp.process()
        exp.save(str(p))
        assert p.exists()
        assert p.stat().st_size > 0
