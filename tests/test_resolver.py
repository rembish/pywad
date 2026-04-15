"""Tests for ResourceResolver — unified lookup across WAD and pk3 sources."""

from __future__ import annotations

import os
import tempfile

import pytest

from wadlib.pk3 import Pk3Archive
from wadlib.resolver import ResourceResolver
from wadlib.source import LumpSource, MemoryLumpSource
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Helpers — build minimal in-memory WAD and pk3 fixtures
# ---------------------------------------------------------------------------


def _make_pk3(entries: dict[str, bytes]) -> str:
    """Write a temporary pk3 file and return the path."""
    f = tempfile.NamedTemporaryFile(suffix=".pk3", delete=False)
    path = f.name
    f.close()
    with Pk3Archive(path, "w") as pk3:
        for name, data in entries.items():
            pk3.writestr(name, data)
    return path


# ---------------------------------------------------------------------------
# Unit tests — no real WAD files needed
# ---------------------------------------------------------------------------


class TestResourceResolverWithMemorySources:
    """Tests that use MemoryLumpSource directly — no file I/O needed."""

    def _resolver_from_lumps(
        self, *lump_specs: tuple[str, bytes]
    ) -> tuple[ResourceResolver, list[MemoryLumpSource]]:
        """Build a resolver backed by MemoryLumpSources via a minimal WadFile mock."""
        # We can't easily mock WadFile, so we exercise resolver logic at the
        # LumpSource level by subclassing ResourceResolver just for testing.
        # Actually, use a pk3-only or wad-only resolver and verify the contract.
        raise NotImplementedError  # helper not used — see tests below

    def test_repr(self) -> None:
        r = ResourceResolver()
        assert "sources=0" in repr(r)

    def test_len_empty(self) -> None:
        r = ResourceResolver()
        assert len(r) == 0

    def test_contains_false_when_empty(self) -> None:
        r = ResourceResolver()
        assert "PLAYPAL" not in r

    def test_read_returns_none_when_empty(self) -> None:
        r = ResourceResolver()
        assert r.read("PLAYPAL") is None

    def test_find_source_returns_none_when_empty(self) -> None:
        r = ResourceResolver()
        assert r.find_source("PLAYPAL") is None


class TestResourceResolverWithPk3:
    """Tests using a real (temporary) pk3 file."""

    def test_find_source_returns_memory_lump_source(self) -> None:
        path = _make_pk3({"lumps/MYDATA.lmp": b"\x01\x02\x03"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                src = r.find_source("MYDATA")
            assert src is not None
            assert isinstance(src, LumpSource)
            assert src.read_bytes() == b"\x01\x02\x03"
        finally:
            os.unlink(path)

    def test_find_source_case_insensitive(self) -> None:
        path = _make_pk3({"lumps/MYDATA.lmp": b"\xff"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert r.find_source("mydata") is not None
                assert r.find_source("MyData") is not None
        finally:
            os.unlink(path)

    def test_read_returns_bytes(self) -> None:
        payload = b"\xde\xad\xbe\xef"
        path = _make_pk3({"lumps/CHUNK.lmp": payload})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert r.read("CHUNK") == payload
        finally:
            os.unlink(path)

    def test_missing_resource_returns_none(self) -> None:
        path = _make_pk3({"lumps/PRESENT.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert r.find_source("MISSING") is None
                assert r.read("MISSING") is None
        finally:
            os.unlink(path)

    def test_contains_positive(self) -> None:
        path = _make_pk3({"lumps/THING.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert "THING" in r
        finally:
            os.unlink(path)

    def test_contains_negative(self) -> None:
        path = _make_pk3({"lumps/THING.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert "NOPE" not in r
        finally:
            os.unlink(path)

    def test_len_counts_sources(self) -> None:
        path = _make_pk3({"lumps/X.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert len(r) == 1
        finally:
            os.unlink(path)


class TestResourceResolverPriority:
    """First source wins — pk3-vs-pk3 priority check."""

    def test_first_pk3_wins(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"source_a"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"source_b"})
        try:
            with Pk3Archive(path_a) as pk3_a, Pk3Archive(path_b) as pk3_b:
                r = ResourceResolver(pk3_a, pk3_b)
                assert r.read("DATA") == b"source_a"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_second_source_used_when_first_missing(self) -> None:
        path_a = _make_pk3({"lumps/ALPHA.lmp": b"in_a"})
        path_b = _make_pk3({"lumps/BETA.lmp": b"in_b"})
        try:
            with Pk3Archive(path_a) as pk3_a, Pk3Archive(path_b) as pk3_b:
                r = ResourceResolver(pk3_a, pk3_b)
                assert r.read("ALPHA") == b"in_a"
                assert r.read("BETA") == b"in_b"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_len_with_multiple_sources(self) -> None:
        path_a = _make_pk3({"lumps/A.lmp": b"\x00"})
        path_b = _make_pk3({"lumps/B.lmp": b"\x00"})
        try:
            with Pk3Archive(path_a) as pk3_a, Pk3Archive(path_b) as pk3_b:
                r = ResourceResolver(pk3_a, pk3_b)
                assert len(r) == 2
        finally:
            os.unlink(path_a)
            os.unlink(path_b)


# ---------------------------------------------------------------------------
# Integration tests — require a real WAD file
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestResourceResolverWithRealWad:
    def test_find_playpal_in_wad(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            r = ResourceResolver(wad)
            src = r.find_source("PLAYPAL")
        assert src is not None
        assert isinstance(src, LumpSource)
        assert src.size > 0

    def test_read_playpal_bytes(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            r = ResourceResolver(wad)
            data = r.read("PLAYPAL")
        assert data is not None
        assert len(data) == 768 * 14  # 14 palettes × 256 colours × 3 bytes

    def test_missing_returns_none(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            r = ResourceResolver(wad)
            assert r.find_source("DOESNOTEXIST") is None

    def test_wad_pk3_priority(self) -> None:
        """When the same name is in both WAD and pk3, WAD wins (listed first)."""
        path = _make_pk3({"lumps/PLAYPAL.lmp": b"\xff" * 10})
        try:
            with WadFile(FREEDOOM2) as wad, Pk3Archive(path) as pk3:
                r = ResourceResolver(wad, pk3)
                data = r.read("PLAYPAL")
            # Should be real WAD data, not our 10-byte sentinel
            assert data is not None
            assert len(data) != 10
        finally:
            os.unlink(path)

    def test_wad_pk3_fallthrough(self) -> None:
        """A resource only in pk3 is returned when WAD doesn't have it."""
        payload = b"\xca\xfe\xba\xbe"
        path = _make_pk3({"lumps/MYMOD.lmp": payload})
        try:
            with WadFile(FREEDOOM2) as wad, Pk3Archive(path) as pk3:
                r = ResourceResolver(wad, pk3)
                assert r.read("MYMOD") == payload
        finally:
            os.unlink(path)
