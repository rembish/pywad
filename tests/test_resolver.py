"""Tests for ResourceResolver — unified lookup across WAD and pk3 sources."""

from __future__ import annotations

import os
import struct
import tempfile

import pytest

from wadlib.pk3 import Pk3Archive
from wadlib.resolver import ResourceRef, ResourceResolver
from wadlib.source import LumpSource, MemoryLumpSource
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Helpers — build minimal in-memory WAD and pk3 fixtures
# ---------------------------------------------------------------------------


def _make_wad(lumps: list[tuple[str, bytes]]) -> str:
    """Write a minimal PWAD with the given lumps and return the path."""
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)
    header = struct.pack("<4sII", b"PWAD", len(lumps), dir_offset)
    directory = b""
    offset = data_start
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.encode().ljust(8, b"\x00"))
        offset += len(data)
    raw = header + lump_data + directory
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def _make_pk3(entries: dict[str, bytes]) -> str:
    """Write a temporary pk3 file and return the path."""
    with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
        path = f.name
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
# doom_load_order named constructor
# ---------------------------------------------------------------------------


class TestDoomLoadOrder:
    """doom_load_order: last patch wins (Doom PWAD override semantics)."""

    def test_last_patch_wins(self) -> None:
        path_base = _make_pk3({"lumps/DATA.lmp": b"base"})
        path_p1 = _make_pk3({"lumps/DATA.lmp": b"patch1"})
        path_p2 = _make_pk3({"lumps/DATA.lmp": b"patch2"})
        try:
            with (
                Pk3Archive(path_base) as base,
                Pk3Archive(path_p1) as p1,
                Pk3Archive(path_p2) as p2,
            ):
                r = ResourceResolver.doom_load_order(base, p1, p2)
                assert r.read("DATA") == b"patch2"
        finally:
            for p in (path_base, path_p1, path_p2):
                os.unlink(p)

    def test_base_used_when_patches_dont_have_it(self) -> None:
        path_base = _make_pk3({"lumps/IWAD.lmp": b"iwad_only"})
        path_p1 = _make_pk3({"lumps/MOD.lmp": b"mod_only"})
        try:
            with Pk3Archive(path_base) as base, Pk3Archive(path_p1) as p1:
                r = ResourceResolver.doom_load_order(base, p1)
                assert r.read("IWAD") == b"iwad_only"
                assert r.read("MOD") == b"mod_only"
        finally:
            os.unlink(path_base)
            os.unlink(path_p1)

    def test_no_patches_returns_base_only(self) -> None:
        path_base = _make_pk3({"lumps/ONLY.lmp": b"solo"})
        try:
            with Pk3Archive(path_base) as base:
                r = ResourceResolver.doom_load_order(base)
                assert r.read("ONLY") == b"solo"
                assert len(r) == 1
        finally:
            os.unlink(path_base)

    def test_load_order_vs_priority_order_differ(self) -> None:
        """Confirms doom_load_order and default constructor give opposite results."""
        path_a = _make_pk3({"lumps/X.lmp": b"a"})
        path_b = _make_pk3({"lumps/X.lmp": b"b"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                priority = ResourceResolver(a, b)  # a wins
                doom = ResourceResolver.doom_load_order(a, b)  # b wins (last patch)
                assert priority.read("X") == b"a"
                assert doom.read("X") == b"b"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)


# ---------------------------------------------------------------------------
# find_all — all matches, highest priority first
# ---------------------------------------------------------------------------


class TestFindAll:
    """find_all returns ResourceRef objects for every source that has the name."""

    def test_empty_resolver_returns_empty_list(self) -> None:
        r = ResourceResolver()
        assert r.find_all("PLAYPAL") == []

    def test_single_match_returns_one_ref(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"hello"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = r.find_all("DATA")
            assert len(refs) == 1
            assert isinstance(refs[0], ResourceRef)
            assert refs[0].name == "DATA"
            assert refs[0].read_bytes() == b"hello"
        finally:
            os.unlink(path)

    def test_two_sources_both_returned(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"from_a"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"from_b"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                r = ResourceResolver(a, b)
                refs = r.find_all("DATA")
            assert len(refs) == 2
            # highest priority first
            assert refs[0].read_bytes() == b"from_a"
            assert refs[1].read_bytes() == b"from_b"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_archive_field_identifies_origin(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"a"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"b"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                r = ResourceResolver(a, b)
                refs = r.find_all("DATA")
                assert refs[0].archive is a
                assert refs[1].archive is b
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_no_match_returns_empty_list(self) -> None:
        path = _make_pk3({"lumps/PRESENT.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert r.find_all("ABSENT") == []
        finally:
            os.unlink(path)

    def test_name_is_uppercased(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = r.find_all("data")
                assert refs[0].name == "DATA"
        finally:
            os.unlink(path)

    def test_source_field_is_lump_source(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"abc"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = r.find_all("DATA")
                assert isinstance(refs[0].source, LumpSource)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# ResourceRef dataclass
# ---------------------------------------------------------------------------


class TestResourceRef:
    def test_frozen(self) -> None:
        src = MemoryLumpSource("DATA", b"x")
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = ResourceRef(name="DATA", archive=pk3, source=src)
                with pytest.raises((AttributeError, TypeError)):
                    ref.name = "OTHER"  # type: ignore[misc]
        finally:
            os.unlink(path)

    def test_read_bytes_delegates_to_source(self) -> None:
        src = MemoryLumpSource("DATA", b"payload")
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = ResourceRef(name="DATA", archive=pk3, source=src)
                assert ref.read_bytes() == b"payload"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# find_all — collision-complete: WAD duplicate lumps
# ---------------------------------------------------------------------------


class TestFindAllWadDuplicates:
    """find_all must return every entry when a WAD contains duplicate lump names."""

    def test_wad_duplicate_lumps_both_returned(self) -> None:
        path = _make_wad([("MYDATA", b"first"), ("MYDATA", b"second")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                refs = r.find_all("MYDATA")
                assert len(refs) == 2
                # Last directory entry is highest priority
                assert refs[0].read_bytes() == b"second"
                assert refs[1].read_bytes() == b"first"
        finally:
            os.unlink(path)

    def test_wad_duplicate_first_ref_matches_find_source(self) -> None:
        """find_all(name)[0] must agree with find_source(name) on the winner."""
        path = _make_wad([("MYDATA", b"first"), ("MYDATA", b"second")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                winner = r.find_source("MYDATA")
                refs = r.find_all("MYDATA")
                assert winner is not None
                assert refs[0].read_bytes() == winner.read_bytes()
        finally:
            os.unlink(path)

    def test_wad_three_duplicates_all_returned(self) -> None:
        path = _make_wad([("X", b"a"), ("X", b"b"), ("X", b"c")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                refs = r.find_all("X")
                assert len(refs) == 3
                assert [ref.read_bytes() for ref in refs] == [b"c", b"b", b"a"]
        finally:
            os.unlink(path)

    def test_wad_single_entry_no_duplication(self) -> None:
        path = _make_wad([("MYDATA", b"only")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                refs = r.find_all("MYDATA")
            assert len(refs) == 1
        finally:
            os.unlink(path)

    def test_archive_field_is_same_wad_for_all_dups(self) -> None:
        path = _make_wad([("MYDATA", b"a"), ("MYDATA", b"b")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                refs = r.find_all("MYDATA")
                assert all(ref.archive is wad for ref in refs)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# find_all — collision-complete: PK3 lump-name collisions
# ---------------------------------------------------------------------------


class TestFindAllPk3Collisions:
    """find_all must return every pk3 entry that maps to the same 8-char lump name."""

    def test_pk3_two_files_same_lump_name_both_returned(self) -> None:
        # Two files whose names (after stripping extension, uppercasing, 8-char trim)
        # both produce "LONGNAME".
        path = _make_pk3({"lumps/LONGNAME1.lmp": b"v1", "lumps/LONGNAME2.lmp": b"v2"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = r.find_all("LONGNAME")
            # Both "LONGNAME1" and "LONGNAME2" truncate to "LONGNAME" (8 chars)
            assert len(refs) == 2
        finally:
            os.unlink(path)

    def test_pk3_collision_first_ref_matches_find_source(self) -> None:
        path = _make_pk3({"lumps/LONGNAME1.lmp": b"first", "lumps/LONGNAME2.lmp": b"second"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                winner = r.find_source("LONGNAME")
                refs = r.find_all("LONGNAME")
            assert winner is not None
            assert refs[0].read_bytes() == winner.read_bytes()
        finally:
            os.unlink(path)

    def test_pk3_no_collision_returns_single(self) -> None:
        path = _make_pk3({"lumps/UNIQUE.lmp": b"solo"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = r.find_all("UNIQUE")
            assert len(refs) == 1
        finally:
            os.unlink(path)


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
        assert len(data) == 768 * 14  # 14 palettes x 256 colours x 3 bytes

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
