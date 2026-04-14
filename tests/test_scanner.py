"""Tests for texture/flat usage scanner."""

from __future__ import annotations

import os

import pytest

from wadlib.scanner import (
    MapUsage,
    UsageReport,
    find_unused_flats,
    find_unused_textures,
    scan_usage,
)
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Module-scoped fixture — scan_usage is expensive; run it once for all tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _freedoom2_scan() -> tuple[UsageReport, int]:
    """(scan_result, map_count) — computed once per test session."""
    if not _has_wad(FREEDOOM2):
        pytest.skip("freedoom2.wad not available")
    with WadFile(FREEDOOM2) as wad:
        return scan_usage(wad), len(wad.maps)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestScanUsage:
    def test_scan_produces_results(self, _freedoom2_scan: tuple[UsageReport, int]) -> None:
        usage, _ = _freedoom2_scan
        assert usage.total_unique_textures > 0
        assert usage.total_unique_flats > 0
        assert usage.total_unique_thing_types > 0

    def test_per_map_breakdown(self, _freedoom2_scan: tuple[UsageReport, int]) -> None:
        usage, _ = _freedoom2_scan
        assert "MAP01" in usage.per_map
        m1 = usage.per_map["MAP01"]
        assert isinstance(m1, MapUsage)
        assert m1.thing_count > 0
        assert m1.linedef_count > 0
        assert m1.sector_count > 0
        assert len(m1.textures) > 0
        assert len(m1.flats) > 0

    def test_all_maps_scanned(self, _freedoom2_scan: tuple[UsageReport, int]) -> None:
        usage, map_count = _freedoom2_scan
        assert len(usage.per_map) == map_count

    def test_no_dash_in_textures(self, _freedoom2_scan: tuple[UsageReport, int]) -> None:
        """The '-' sentinel should not appear in used textures."""
        usage, _ = _freedoom2_scan
        assert "-" not in usage.textures
        assert "-" not in usage.flats


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestFindUnused:
    def test_find_unused_textures(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            unused = find_unused_textures(wad)
            assert isinstance(unused, set)

    def test_find_unused_flats(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            unused = find_unused_flats(wad)
            assert isinstance(unused, set)
