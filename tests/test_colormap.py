"""Tests for COLORMAP lump."""
from wadlib.lumps.colormap import _COLORMAP_SIZE, _NUM_COLORMAPS, ColormapLump
from wadlib.wad import WadFile


def test_colormap_not_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.colormap is not None


def test_colormap_is_colormap_lump(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.colormap, ColormapLump)


def test_colormap_count(doom1_wad: WadFile) -> None:
    assert doom1_wad.colormap is not None
    assert doom1_wad.colormap.count == _NUM_COLORMAPS


def test_colormap_get_returns_256_bytes(doom1_wad: WadFile) -> None:
    assert doom1_wad.colormap is not None
    cm = doom1_wad.colormap.get(0)
    assert len(cm) == _COLORMAP_SIZE


def test_colormap_zero_is_near_identity(doom1_wad: WadFile) -> None:
    """Colormap 0 (full brightness) should be very close to the identity mapping."""
    assert doom1_wad.colormap is not None
    cm = doom1_wad.colormap.get(0)
    mismatches = sum(1 for i, b in enumerate(cm) if b != i)
    # Allow a small number of non-identity entries (e.g. transparent/special colours)
    assert mismatches < 20


def test_colormap_get_all_valid_indices(doom1_wad: WadFile) -> None:
    assert doom1_wad.colormap is not None
    for i in range(_NUM_COLORMAPS):
        cm = doom1_wad.colormap.get(i)
        assert len(cm) == _COLORMAP_SIZE
        assert all(0 <= b <= 255 for b in cm)


def test_colormap_apply_returns_int(doom1_wad: WadFile) -> None:
    assert doom1_wad.colormap is not None
    result = doom1_wad.colormap.apply(0, 42)
    assert isinstance(result, int)
    assert 0 <= result <= 255


def test_colormap_darkens(doom1_wad: WadFile) -> None:
    """Darker colormaps generally map to lower palette indices (darker colours)."""
    assert doom1_wad.colormap is not None
    bright = doom1_wad.colormap.get(0)
    # Use colormap 31 (near-black) for a clear darkening signal
    dark = doom1_wad.colormap.get(31)
    # Most mappings in a darker colormap point to darker (lower-index) colours
    darker_count = sum(1 for b, d in zip(bright, dark, strict=True) if d <= b)
    assert darker_count > 200  # loose threshold
