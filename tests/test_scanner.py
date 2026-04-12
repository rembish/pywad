"""Tests for texture/flat usage scanner."""

from __future__ import annotations

import os

import pytest

from wadlib.scanner import (
    MapUsage,
    find_unused_flats,
    find_unused_textures,
    scan_usage,
)
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestScanUsage:
    def test_scan_produces_results(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            usage = scan_usage(wad)
            assert usage.total_unique_textures > 0
            assert usage.total_unique_flats > 0
            assert usage.total_unique_thing_types > 0

    def test_per_map_breakdown(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            usage = scan_usage(wad)
            assert "MAP01" in usage.per_map
            m1 = usage.per_map["MAP01"]
            assert isinstance(m1, MapUsage)
            assert m1.thing_count > 0
            assert m1.linedef_count > 0
            assert m1.sector_count > 0
            assert len(m1.textures) > 0
            assert len(m1.flats) > 0

    def test_all_maps_scanned(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            usage = scan_usage(wad)
            assert len(usage.per_map) == len(wad.maps)

    def test_no_dash_in_textures(self) -> None:
        """The '-' sentinel should not appear in used textures."""
        with WadFile(FREEDOOM2) as wad:
            usage = scan_usage(wad)
            assert "-" not in usage.textures
            assert "-" not in usage.flats


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestFindUnused:
    def test_find_unused_textures(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            unused = find_unused_textures(wad)
            # There should be some unused textures in any IWAD
            assert isinstance(unused, set)

    def test_find_unused_flats(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            unused = find_unused_flats(wad)
            assert isinstance(unused, set)
