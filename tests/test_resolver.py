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


def _make_ref(archive: Pk3Archive, data: bytes = b"x", name: str = "DATA") -> ResourceRef:
    """Build a ResourceRef with all required fields for unit testing."""
    src = MemoryLumpSource(name, data)
    return ResourceRef(
        name=name,
        archive=archive,
        source=src,
        size=len(data),
        kind="pk3-lump-name",
        namespace="lumps",
        load_order_index=0,
    )


class TestResourceRef:
    def test_frozen(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3)
                with pytest.raises((AttributeError, TypeError)):
                    ref.name = "OTHER"  # type: ignore[misc]
        finally:
            os.unlink(path)

    def test_read_bytes_delegates_to_source(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3, data=b"payload")
                assert ref.read_bytes() == b"payload"
        finally:
            os.unlink(path)

    def test_size_field(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3, data=b"hello")
                assert ref.size == 5
        finally:
            os.unlink(path)

    def test_kind_field(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3)
                assert ref.kind == "pk3-lump-name"
        finally:
            os.unlink(path)

    def test_namespace_field(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3)
                assert ref.namespace == "lumps"
        finally:
            os.unlink(path)

    def test_load_order_index_field(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                ref = _make_ref(pk3)
                assert ref.load_order_index == 0
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


# ---------------------------------------------------------------------------
# ResourceRef metadata fields on real find_all results
# ---------------------------------------------------------------------------


class TestResourceRefMetadata:
    """Verify size, kind, namespace, load_order_index on resolver-produced refs."""

    def test_wad_ref_kind_is_wad_name(self) -> None:
        path = _make_wad([("DATA", b"x")])
        try:
            with WadFile(path) as wad:
                refs = ResourceResolver(wad).find_all("DATA")
                assert refs[0].kind == "wad-name"
        finally:
            os.unlink(path)

    def test_wad_ref_namespace_is_empty(self) -> None:
        path = _make_wad([("DATA", b"x")])
        try:
            with WadFile(path) as wad:
                refs = ResourceResolver(wad).find_all("DATA")
                assert refs[0].namespace == ""
        finally:
            os.unlink(path)

    def test_wad_ref_size_matches_data(self) -> None:
        path = _make_wad([("DATA", b"hello")])
        try:
            with WadFile(path) as wad:
                refs = ResourceResolver(wad).find_all("DATA")
                assert refs[0].size == 5
        finally:
            os.unlink(path)

    def test_wad_ref_load_order_index(self) -> None:
        path_a = _make_wad([("A", b"x")])
        path_b = _make_wad([("B", b"y")])
        try:
            with WadFile(path_a) as wa, WadFile(path_b) as wb:
                r = ResourceResolver(wa, wb)
                assert r.find_all("A")[0].load_order_index == 0
                assert r.find_all("B")[0].load_order_index == 1
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_pk3_ref_kind_is_pk3_lump_name(self) -> None:
        path = _make_pk3({"lumps/DATA.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                refs = ResourceResolver(pk3).find_all("DATA")
                assert refs[0].kind == "pk3-lump-name"
        finally:
            os.unlink(path)

    def test_pk3_ref_namespace_is_category(self) -> None:
        path = _make_pk3({"flats/FLOOR0.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                refs = ResourceResolver(pk3).find_all("FLOOR0")
                assert refs[0].namespace == "flats"
        finally:
            os.unlink(path)

    def test_pk3_ref_size_matches_data(self) -> None:
        path = _make_pk3({"lumps/CHUNK.lmp": b"\xff" * 12})
        try:
            with Pk3Archive(path) as pk3:
                refs = ResourceResolver(pk3).find_all("CHUNK")
                assert refs[0].size == 12
        finally:
            os.unlink(path)

    def test_pk3_ref_load_order_index_second_source(self) -> None:
        path_a = _make_pk3({"lumps/A.lmp": b"x"})
        path_b = _make_pk3({"lumps/B.lmp": b"y"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                r = ResourceResolver(a, b)
                assert r.find_all("A")[0].load_order_index == 0
                assert r.find_all("B")[0].load_order_index == 1
        finally:
            os.unlink(path_a)
            os.unlink(path_b)


# ---------------------------------------------------------------------------
# shadowed()
# ---------------------------------------------------------------------------


class TestShadowed:
    """shadowed(name) returns refs hidden behind the highest-priority match."""

    def test_no_collision_returns_empty_list(self) -> None:
        path = _make_pk3({"lumps/ONLY.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                assert r.shadowed("ONLY") == []
        finally:
            os.unlink(path)

    def test_missing_returns_empty_list(self) -> None:
        r = ResourceResolver()
        assert r.shadowed("NOPE") == []

    def test_cross_source_shadowed(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"winner"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"loser"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                r = ResourceResolver(a, b)
                hidden = r.shadowed("DATA")
                assert len(hidden) == 1
                assert hidden[0].read_bytes() == b"loser"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_wad_intra_duplicate_shadowed(self) -> None:
        path = _make_wad([("X", b"first"), ("X", b"second")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                hidden = r.shadowed("X")
                assert len(hidden) == 1
                assert hidden[0].read_bytes() == b"first"
        finally:
            os.unlink(path)

    def test_shadowed_is_find_all_minus_first(self) -> None:
        path_a = _make_pk3({"lumps/D.lmp": b"a"})
        path_b = _make_pk3({"lumps/D.lmp": b"b"})
        path_c = _make_pk3({"lumps/D.lmp": b"c"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b, Pk3Archive(path_c) as c:
                r = ResourceResolver(a, b, c)
                all_refs = r.find_all("D")
                hidden = r.shadowed("D")
                # shadowed must agree with find_all[1:] in length and content
                assert len(hidden) == len(all_refs) - 1
                for shadow, expected in zip(hidden, all_refs[1:], strict=True):
                    assert shadow.read_bytes() == expected.read_bytes()
                    assert shadow.load_order_index == expected.load_order_index
        finally:
            for p in (path_a, path_b, path_c):
                os.unlink(p)


# ---------------------------------------------------------------------------
# iter_resources()
# ---------------------------------------------------------------------------


class TestIterResources:
    """iter_resources yields one ResourceRef per unique name, highest-priority wins."""

    def test_empty_resolver_yields_nothing(self) -> None:
        assert list(ResourceResolver().iter_resources()) == []

    def test_single_pk3_resource_yielded(self) -> None:
        path = _make_pk3({"lumps/SOLO.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                refs = list(ResourceResolver(pk3).iter_resources())
            assert any(r.name == "SOLO" for r in refs)
        finally:
            os.unlink(path)

    def test_cross_source_dedup_yields_winner_only(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"winner"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"loser"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                r = ResourceResolver(a, b)
                data_refs = [ref for ref in r.iter_resources() if ref.name == "DATA"]
                assert len(data_refs) == 1
                assert data_refs[0].read_bytes() == b"winner"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_wad_intra_duplicate_yields_winner_only(self) -> None:
        path = _make_wad([("X", b"first"), ("X", b"second")])
        try:
            with WadFile(path) as wad:
                r = ResourceResolver(wad)
                x_refs = [ref for ref in r.iter_resources() if ref.name == "X"]
                assert len(x_refs) == 1
                assert x_refs[0].read_bytes() == b"second"
        finally:
            os.unlink(path)

    def test_category_filter_includes_matching_namespace(self) -> None:
        path = _make_pk3({"flats/FLOOR0.lmp": b"f", "lumps/OTHER.lmp": b"o"})
        try:
            with Pk3Archive(path) as pk3:
                refs = list(ResourceResolver(pk3).iter_resources(category="flats"))
                names = {r.name for r in refs}
                assert "FLOOR0" in names
                assert "OTHER" not in names
        finally:
            os.unlink(path)

    def test_category_filter_excludes_wad_entries(self) -> None:
        """WAD entries have namespace="" so non-empty category filter skips them."""
        path = _make_wad([("DATA", b"x")])
        try:
            with WadFile(path) as wad:
                refs = list(ResourceResolver(wad).iter_resources(category="flats"))
                assert refs == []
        finally:
            os.unlink(path)

    def test_none_category_includes_all(self) -> None:
        path_wad = _make_wad([("WDATA", b"w")])
        path_pk3 = _make_pk3({"lumps/PDATA.lmp": b"p"})
        try:
            with WadFile(path_wad) as wad, Pk3Archive(path_pk3) as pk3:
                refs = list(ResourceResolver(wad, pk3).iter_resources(category=None))
                names = {r.name for r in refs}
                assert "WDATA" in names
                assert "PDATA" in names
        finally:
            os.unlink(path_wad)
            os.unlink(path_pk3)

    def test_each_name_appears_exactly_once(self) -> None:
        path_a = _make_pk3({"lumps/A.lmp": b"x", "lumps/B.lmp": b"y"})
        path_b = _make_pk3({"lumps/A.lmp": b"z", "lumps/C.lmp": b"w"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                refs = list(ResourceResolver(a, b).iter_resources())
                names = [r.name for r in refs]
                assert len(names) == len(set(names))  # no duplicates
                assert set(names) >= {"A", "B", "C"}
        finally:
            os.unlink(path_a)
            os.unlink(path_b)


# ---------------------------------------------------------------------------
# collisions()
# ---------------------------------------------------------------------------


class TestCollisions:
    """collisions() returns all names with more than one match."""

    def test_no_collision_returns_empty_dict(self) -> None:
        path = _make_pk3({"lumps/UNIQUE.lmp": b"x"})
        try:
            with Pk3Archive(path) as pk3:
                assert ResourceResolver(pk3).collisions() == {}
        finally:
            os.unlink(path)

    def test_empty_resolver_returns_empty_dict(self) -> None:
        assert ResourceResolver().collisions() == {}

    def test_cross_source_collision_detected(self) -> None:
        path_a = _make_pk3({"lumps/DATA.lmp": b"a"})
        path_b = _make_pk3({"lumps/DATA.lmp": b"b"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                clashes = ResourceResolver(a, b).collisions()
                assert "DATA" in clashes
                assert len(clashes["DATA"]) == 2
                assert clashes["DATA"][0].read_bytes() == b"a"
                assert clashes["DATA"][1].read_bytes() == b"b"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_wad_intra_duplicate_detected(self) -> None:
        path = _make_wad([("DUP", b"first"), ("DUP", b"second")])
        try:
            with WadFile(path) as wad:
                clashes = ResourceResolver(wad).collisions()
                assert "DUP" in clashes
                assert len(clashes["DUP"]) == 2
        finally:
            os.unlink(path)

    def test_pk3_lump_name_collision_detected(self) -> None:
        # LONGNAME1 and LONGNAME2 both truncate to LONGNAME (8 chars)
        path = _make_pk3({"lumps/LONGNAME1.lmp": b"v1", "lumps/LONGNAME2.lmp": b"v2"})
        try:
            with Pk3Archive(path) as pk3:
                clashes = ResourceResolver(pk3).collisions()
                assert "LONGNAME" in clashes
                assert len(clashes["LONGNAME"]) == 2
        finally:
            os.unlink(path)

    def test_non_colliding_names_not_in_result(self) -> None:
        path_a = _make_pk3({"lumps/SHARED.lmp": b"a", "lumps/ONLYA.lmp": b"x"})
        path_b = _make_pk3({"lumps/SHARED.lmp": b"b", "lumps/ONLYB.lmp": b"y"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                clashes = ResourceResolver(a, b).collisions()
                assert "SHARED" in clashes
                assert "ONLYA" not in clashes
                assert "ONLYB" not in clashes
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_collisions_refs_are_highest_priority_first(self) -> None:
        path_a = _make_pk3({"lumps/X.lmp": b"winner"})
        path_b = _make_pk3({"lumps/X.lmp": b"loser"})
        try:
            with Pk3Archive(path_a) as a, Pk3Archive(path_b) as b:
                clashes = ResourceResolver(a, b).collisions()
                refs = clashes["X"]
                assert refs[0].read_bytes() == b"winner"
                assert refs[1].read_bytes() == b"loser"
        finally:
            os.unlink(path_a)
            os.unlink(path_b)

    def test_map_sub_lumps_not_reported_as_collisions(self) -> None:
        """A two-map WAD repeats THINGS/LINEDEFS/etc. — these must NOT appear
        as collisions because they are scoped under map markers, not global."""
        # Build a minimal two-map WAD: MAP01 marker + THINGS, MAP02 marker + THINGS.
        lumps = [
            ("MAP01", b""),
            ("THINGS", b"\x00" * 10),
            ("LINEDEFS", b"\x00" * 14),
            ("MAP02", b""),
            ("THINGS", b"\x00" * 10),
            ("LINEDEFS", b"\x00" * 14),
        ]
        path = _make_wad(lumps)
        try:
            with WadFile(path) as wad:
                clashes = ResourceResolver(wad).collisions()
                assert "THINGS" not in clashes
                assert "LINEDEFS" not in clashes
        finally:
            os.unlink(path)

    def test_global_duplicates_still_reported(self) -> None:
        """True global duplicates (e.g. duplicate PLAYPAL) must still be caught."""
        path = _make_wad([("PLAYPAL", b"a" * 10), ("PLAYPAL", b"b" * 10)])
        try:
            with WadFile(path) as wad:
                clashes = ResourceResolver(wad).collisions()
                assert "PLAYPAL" in clashes
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# PK3 category alias normalization
# ---------------------------------------------------------------------------


class TestPk3CategoryAliases:
    """Pk3Entry.category must return canonical names via _CATEGORY_ALIASES."""

    def test_sfx_normalises_to_sounds(self) -> None:
        path = _make_pk3({"sfx/DSPISTOL.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                entries = [e for e in pk3.infolist() if e.name == "DSPISTOL.lmp"]
                assert entries[0].category == "sounds"
        finally:
            os.unlink(path)

    def test_sound_normalises_to_sounds(self) -> None:
        path = _make_pk3({"sound/DSPISTOL.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                entries = [e for e in pk3.infolist() if e.name == "DSPISTOL.lmp"]
                assert entries[0].category == "sounds"
        finally:
            os.unlink(path)

    def test_flat_normalises_to_flats(self) -> None:
        path = _make_pk3({"flat/FLOOR0.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                entries = [e for e in pk3.infolist() if e.name == "FLOOR0.lmp"]
                assert entries[0].category == "flats"
        finally:
            os.unlink(path)

    def test_sounds_canonical_unchanged(self) -> None:
        path = _make_pk3({"sounds/DSPISTOL.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                entries = [e for e in pk3.infolist() if e.name == "DSPISTOL.lmp"]
                assert entries[0].category == "sounds"
        finally:
            os.unlink(path)

    def test_iter_resources_sfx_matches_sounds_filter(self) -> None:
        """iter_resources(category='sounds') must find sfx/ entries."""
        path = _make_pk3({"sfx/DSPISTOL.lmp": b"\x00"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                refs = list(r.iter_resources(category="sounds"))
                names = {ref.name for ref in refs}
                assert "DSPISTOL" in names
        finally:
            os.unlink(path)
