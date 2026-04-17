"""Phase 3 — validation and diagnostics layer.

Tests cover:
- DiagnosticItem dataclass and to_dict()
- ValidationReport properties: errors, warnings, is_clean, to_dict()
- analyze() on WadFile, Pk3Archive, and ResourceResolver inputs
- Map reference checks: bad vertex refs, bad sidedef refs, bad sector refs
- Missing texture / flat warnings
- PNAMES integrity checks
- Resource collision warnings
- Compatibility level detection
"""

from __future__ import annotations

import os
import struct
import tempfile
import zipfile
from unittest.mock import patch

from wadlib.analysis import DiagnosticItem, ValidationReport, _collect_texture_names, analyze
from wadlib.compat import CompLevel
from wadlib.pk3 import Pk3Archive
from wadlib.resolver import ResourceResolver
from wadlib.validate import Severity
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# WAD / PK3 construction helpers (shared with test_phase2_maps.py style)
# ---------------------------------------------------------------------------


def _pack_name(name: str) -> bytes:
    return name.encode("ascii")[:8].ljust(8, b"\x00")


def _wad_bytes(lumps: list[tuple[str, bytes]]) -> bytes:
    """Build a minimal PWAD in memory."""
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)
    header = struct.pack("<4sII", b"PWAD", len(lumps), dir_offset)
    directory = b""
    offset = data_start
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), _pack_name(name))
        offset += len(data)
    return header + lump_data + directory


def _wad_file(lumps: list[tuple[str, bytes]]) -> str:
    raw = _wad_bytes(lumps)
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def _pk3_file(entries: dict[str, bytes]) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return path


# ---------------------------------------------------------------------------
# Helper to build binary map lumps
# ---------------------------------------------------------------------------

# Doom vertex: x(int16) y(int16) — 4 bytes
_VERTEX = struct.pack("<hh", 0, 0)


# Doom sidedef: x_off(int16) y_off(int16) upper(8s) lower(8s) middle(8s)
# sector(uint16) — 30 bytes
def _sidedef(upper: str = "-", lower: str = "-", mid: str = "-", sector: int = 0) -> bytes:
    return struct.pack(
        "<hh8s8s8sH",
        0,
        0,
        _pack_name(upper),
        _pack_name(lower),
        _pack_name(mid),
        sector,
    )


# Doom linedef: v1(uint16) v2(uint16) flags(uint16) special(uint16) tag(uint16)
# right(int16) left(int16) — 14 bytes
def _linedef(
    v1: int = 0,
    v2: int = 1,
    right: int = 0,
    left: int = -1,
    special: int = 0,
) -> bytes:
    return struct.pack("<HHHHHhh", v1, v2, 0, special, 0, right, left)


# Doom sector: floor_h(int16) ceil_h(int16) floor_tex(8s) ceil_tex(8s)
# light(uint16) type(uint16) tag(uint16) — 26 bytes
def _sector(floor: str = "FLOOR4_8", ceiling: str = "CEIL3_5") -> bytes:
    return struct.pack(
        "<hh8s8sHHH",
        0,
        128,
        _pack_name(floor),
        _pack_name(ceiling),
        160,
        0,
        0,
    )


# Doom THINGS: x(int16) y(int16) angle(uint16) type(uint16) flags(uint16) — 10 bytes
_THING = struct.pack("<hhHHH", 0, 0, 0, 1, 7)


# ---------------------------------------------------------------------------
# PNAMES + TEXTUREx builder
# ---------------------------------------------------------------------------


def _pnames_lump(names: list[str]) -> bytes:
    """Build a minimal PNAMES lump."""
    count_bytes = struct.pack("<I", len(names))
    entries = b"".join(_pack_name(n) for n in names)
    return count_bytes + entries


def _texture1_lump(textures: list[tuple[str, list[int]]]) -> bytes:
    """Build a minimal TEXTURE1 lump.

    ``textures`` is a list of ``(name, patch_indices)`` pairs.
    """
    # Header: count(uint32) + offsets(uint32 each)
    count = len(textures)
    # Compute per-texture sizes: header 22 bytes + 10 bytes per patch
    tex_hdr_size = 22
    patch_size = 10
    # offsets table starts after count(4) + offsets(count*4)
    offsets_table_size = 4 + count * 4
    offsets: list[int] = []
    pos = offsets_table_size
    for _, patches in textures:
        offsets.append(pos)
        pos += tex_hdr_size + patch_size * len(patches)

    buf = struct.pack("<I", count)
    for off in offsets:
        buf += struct.pack("<I", off)
    for name, patch_indices in textures:
        # name(8s) masked(4) width(2) height(2) columndirectory(4) patchcount(2)
        buf += struct.pack(
            "<8sIHHIH",
            _pack_name(name),
            0,
            64,
            128,
            0,
            len(patch_indices),
        )
        for pidx in patch_indices:
            # originx(2) originy(2) patch_index(2) stepdir(2) colormap(2)
            buf += struct.pack("<hhHhh", 0, 0, pidx, 0, 0)
    return buf


# ---------------------------------------------------------------------------
# DiagnosticItem
# ---------------------------------------------------------------------------


class TestDiagnosticItem:
    def test_fields(self) -> None:
        item = DiagnosticItem(
            code="MISSING_TEXTURE",
            severity=Severity.WARNING,
            context="MAP01",
            message="sidedef 0 upper_texture: 'NOTHERE'",
        )
        assert item.code == "MISSING_TEXTURE"
        assert item.severity is Severity.WARNING
        assert item.context == "MAP01"

    def test_to_dict(self) -> None:
        item = DiagnosticItem(
            code="BAD_VERTEX_REF",
            severity=Severity.ERROR,
            context="E1M1",
            message="linedef 0: start_vertex 99 >= 2",
        )
        d = item.to_dict()
        assert d["code"] == "BAD_VERTEX_REF"
        assert d["severity"] == "error"
        assert d["context"] == "E1M1"
        assert "99" in d["message"]

    def test_repr(self) -> None:
        item = DiagnosticItem("X", Severity.ERROR, "CTX", "msg")
        assert "ERROR" in repr(item)
        assert "CTX" in repr(item)


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------


class TestValidationReport:
    def _make_report(self) -> ValidationReport:
        report = ValidationReport()
        report.items.append(DiagnosticItem("ERR1", Severity.ERROR, "MAP01", "some error"))
        report.items.append(DiagnosticItem("WARN1", Severity.WARNING, "MAP01", "some warning"))
        return report

    def test_errors_property(self) -> None:
        report = self._make_report()
        assert len(report.errors) == 1
        assert report.errors[0].severity is Severity.ERROR

    def test_warnings_property(self) -> None:
        report = self._make_report()
        assert len(report.warnings) == 1
        assert report.warnings[0].severity is Severity.WARNING

    def test_is_clean_false_when_errors(self) -> None:
        report = self._make_report()
        assert not report.is_clean

    def test_is_clean_true_when_no_errors(self) -> None:
        report = ValidationReport()
        report.items.append(DiagnosticItem("W", Severity.WARNING, "CTX", "warn"))
        assert report.is_clean

    def test_empty_is_clean(self) -> None:
        assert ValidationReport().is_clean

    def test_to_dict_structure(self) -> None:
        report = self._make_report()
        report.complevel = CompLevel.BOOM
        report.unsupported_features = ["ANIMATED lump"]
        d = report.to_dict()
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert d["is_clean"] is False
        assert "Boom" in str(d["complevel"])
        assert d["unsupported_features"] == ["ANIMATED lump"]
        assert len(d["items"]) == 2

    def test_to_dict_no_complevel(self) -> None:
        d = ValidationReport().to_dict()
        assert d["complevel"] is None


# ---------------------------------------------------------------------------
# analyze() — basic smoke tests
# ---------------------------------------------------------------------------


class TestAnalyzeSmoke:
    def test_empty_wad_returns_report(self) -> None:
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            assert isinstance(report, ValidationReport)
        finally:
            os.unlink(path)

    def test_accepts_resolver(self) -> None:
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(ResourceResolver(wad))
            assert isinstance(report, ValidationReport)
        finally:
            os.unlink(path)

    def test_accepts_pk3(self) -> None:
        path = _pk3_file({})
        try:
            with Pk3Archive(path) as pk3:
                report = analyze(pk3)
            assert isinstance(report, ValidationReport)
        finally:
            os.unlink(path)

    def test_empty_resolver(self) -> None:
        report = analyze(ResourceResolver())
        assert report.is_clean
        assert report.complevel is None

    def test_pk3_only_resolver_complevel(self) -> None:
        path = _pk3_file({})
        try:
            with Pk3Archive(path) as pk3:
                report = analyze(ResourceResolver(pk3))
            # PK3-only → treated as ZDoom
            assert report.complevel is CompLevel.ZDOOM
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Map reference checks
# ---------------------------------------------------------------------------


class TestMapRefChecks:
    def test_clean_map_no_errors(self) -> None:
        """A minimal map with valid references produces no errors."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0, left=-1)),
            ("SIDEDEFS", _sidedef()),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            ref_errors = [i for i in report.items if "REF" in i.code]
            assert ref_errors == []
        finally:
            os.unlink(path)

    def test_bad_vertex_ref_detected(self) -> None:
        """A linedef referencing a non-existent vertex is an error."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            # v2=99 but only 2 vertices
            ("LINEDEFS", _linedef(v1=0, v2=99, right=0)),
            ("SIDEDEFS", _sidedef()),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.errors]
            assert "BAD_VERTEX_REF" in codes
        finally:
            os.unlink(path)

    def test_bad_sidedef_ref_detected(self) -> None:
        """A linedef referencing a non-existent sidedef is an error."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            # right sidedef 5 but only 1 sidedef
            ("LINEDEFS", _linedef(v1=0, v2=1, right=5)),
            ("SIDEDEFS", _sidedef()),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.errors]
            assert "BAD_SIDEDEF_REF" in codes
        finally:
            os.unlink(path)

    def test_bad_sector_ref_detected(self) -> None:
        """A sidedef referencing a non-existent sector is an error."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0)),
            # sector=5 but only 1 sector
            ("SIDEDEFS", _sidedef(sector=5)),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.errors]
            assert "BAD_SECTOR_REF" in codes
        finally:
            os.unlink(path)

    def test_two_sided_linedef_valid_left(self) -> None:
        """Two-sided linedef with valid left sidedef produces no error."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0, left=1)),
            ("SIDEDEFS", _sidedef() + _sidedef()),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            ref_errors = [i for i in report.errors if "REF" in i.code]
            assert ref_errors == []
        finally:
            os.unlink(path)

    def test_two_sided_linedef_bad_left(self) -> None:
        """Two-sided linedef with out-of-range left sidedef is an error."""
        lumps = [
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0, left=99)),
            ("SIDEDEFS", _sidedef()),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.errors]
            assert "BAD_SIDEDEF_REF" in codes
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Missing texture / flat checks
# ---------------------------------------------------------------------------


class TestMissingTextureChecks:
    def _make_texture1(self, tex_names: list[str]) -> bytes:
        return _texture1_lump([(n, [0]) for n in tex_names])

    def _make_pnames(self) -> bytes:
        return _pnames_lump(["WALL00_1"])

    def test_valid_texture_no_warning(self) -> None:
        """A sidedef using a defined texture produces no MISSING_TEXTURE warning."""
        lumps = [
            ("PNAMES", self._make_pnames()),
            ("TEXTURE1", self._make_texture1(["MYWALL"])),
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0)),
            ("SIDEDEFS", _sidedef(mid="MYWALL")),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            tex_warnings = [i for i in report.warnings if i.code == "MISSING_TEXTURE"]
            assert tex_warnings == []
        finally:
            os.unlink(path)

    def test_missing_texture_warning(self) -> None:
        """A sidedef using an undefined texture produces a MISSING_TEXTURE warning."""
        lumps = [
            ("PNAMES", self._make_pnames()),
            ("TEXTURE1", self._make_texture1(["WALL_A"])),
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0)),
            ("SIDEDEFS", _sidedef(mid="NOTHERE")),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.warnings]
            assert "MISSING_TEXTURE" in codes
        finally:
            os.unlink(path)

    def test_no_texture_sentinel_not_flagged(self) -> None:
        """The '-' sentinel texture is never flagged as missing."""
        lumps = [
            ("PNAMES", self._make_pnames()),
            ("TEXTURE1", self._make_texture1(["WALL_A"])),
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0)),
            ("SIDEDEFS", _sidedef(upper="-", lower="-", mid="-")),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            tex_warnings = [i for i in report.warnings if i.code == "MISSING_TEXTURE"]
            assert tex_warnings == []
        finally:
            os.unlink(path)

    def test_sky_texture_not_flagged(self) -> None:
        """Sky texture names (F_SKY1, SKY1, etc.) are never flagged."""
        lumps = [
            ("PNAMES", self._make_pnames()),
            ("TEXTURE1", self._make_texture1(["WALL_A"])),
            ("MAP01", b""),
            ("THINGS", _THING),
            ("LINEDEFS", _linedef(v1=0, v2=1, right=0)),
            ("SIDEDEFS", _sidedef(upper="F_SKY1", lower="SKY1", mid="-")),
            ("VERTEXES", _VERTEX * 2),
            ("SECTORS", _sector()),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            tex_warnings = [i for i in report.warnings if i.code == "MISSING_TEXTURE"]
            assert tex_warnings == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# PNAMES integrity
# ---------------------------------------------------------------------------


class TestPnamesCheck:
    def test_valid_pnames_no_error(self) -> None:
        """All patch indices within PNAMES bounds produce no error."""
        pnames = _pnames_lump(["WALL00_1", "WALL00_2"])
        texture1 = _texture1_lump([("MYWALL", [0, 1])])
        path = _wad_file([("PNAMES", pnames), ("TEXTURE1", texture1)])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            pnames_errors = [i for i in report.errors if i.code == "BAD_PNAMES_INDEX"]
            assert pnames_errors == []
        finally:
            os.unlink(path)

    def test_out_of_range_pnames_index(self) -> None:
        """A patch_index >= PNAMES count is flagged as an error."""
        pnames = _pnames_lump(["WALL00_1"])  # only 1 entry → index 0 valid
        texture1 = _texture1_lump([("MYWALL", [5])])  # patch_index=5 is invalid
        path = _wad_file([("PNAMES", pnames), ("TEXTURE1", texture1)])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [i.code for i in report.errors]
            assert "BAD_PNAMES_INDEX" in codes
        finally:
            os.unlink(path)

    def test_no_pnames_no_crash(self) -> None:
        """WAD without PNAMES does not raise; just returns no PNAMES errors."""
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            pnames_errors = [i for i in report.errors if i.code == "BAD_PNAMES_INDEX"]
            assert pnames_errors == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Resource collision warnings
# ---------------------------------------------------------------------------


class TestCollisionWarnings:
    def test_no_collision_no_warning(self) -> None:
        path1 = _wad_file([("UNIQUE1", b"a")])
        path2 = _wad_file([("UNIQUE2", b"b")])
        try:
            with WadFile(path1) as w1, WadFile(path2) as w2:
                report = analyze(ResourceResolver(w1, w2))
            collision_warns = [i for i in report.warnings if i.code == "RESOURCE_COLLISION"]
            assert collision_warns == []
        finally:
            os.unlink(path1)
            os.unlink(path2)

    def test_collision_across_sources_warns(self) -> None:
        """Same name in two sources produces a RESOURCE_COLLISION warning."""
        path1 = _wad_file([("SHARED", b"version_a")])
        path2 = _wad_file([("SHARED", b"version_b")])
        try:
            with WadFile(path1) as w1, WadFile(path2) as w2:
                report = analyze(ResourceResolver(w1, w2))
            collision_warns = [i for i in report.warnings if i.code == "RESOURCE_COLLISION"]
            assert len(collision_warns) == 1
            assert collision_warns[0].context == "SHARED"
        finally:
            os.unlink(path1)
            os.unlink(path2)


# ---------------------------------------------------------------------------
# Compatibility level detection
# ---------------------------------------------------------------------------


class TestComplevel:
    def test_vanilla_wad_complevel(self) -> None:
        """An empty WAD with no special features is VANILLA."""
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            assert report.complevel is CompLevel.VANILLA
        finally:
            os.unlink(path)

    def test_zdoom_lump_raises_complevel(self) -> None:
        """A WAD with ZMAPINFO requires ZDoom or higher."""
        path = _wad_file([("ZMAPINFO", b"// empty")])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            assert report.complevel is not None
            assert report.complevel >= CompLevel.ZDOOM
        finally:
            os.unlink(path)

    def test_boom_lump_detected(self) -> None:
        """A WAD with ANIMATED lump is flagged as Boom+."""
        path = _wad_file([("ANIMATED", b"\xff")])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            assert report.complevel is not None
            assert report.complevel >= CompLevel.BOOM
            assert any("ANIMATED" in f for f in report.unsupported_features)
        finally:
            os.unlink(path)

    def test_unsupported_features_populated(self) -> None:
        """Detected features are recorded in unsupported_features."""
        path = _wad_file([("ZMAPINFO", b"// empty"), ("LANGUAGE", b"")])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            assert len(report.unsupported_features) >= 2
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# to_dict() round-trip
# ---------------------------------------------------------------------------


class TestToDictRoundTrip:
    def test_to_dict_is_json_serializable(self) -> None:
        import json

        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            d = report.to_dict()
            # Must not raise
            json.dumps(d)
        finally:
            os.unlink(path)

    def test_to_dict_item_count_consistent(self) -> None:
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
        finally:
            os.unlink(path)
        d = report.to_dict()
        assert d["error_count"] == len(report.errors)
        assert d["warning_count"] == len(report.warnings)
        assert len(d["items"]) == len(report.items)


# ---------------------------------------------------------------------------
# Finding #6 — analyze() gap diagnostics
# ---------------------------------------------------------------------------


class TestAnalyzeGapDiagnostics:
    """Tests for new explicit diagnostics when analysis stages fail or are skipped."""

    def test_map_assembly_failed_diagnostic(self) -> None:
        """analyze() must emit MAP_ASSEMBLY_FAILED if resolver.maps() raises."""
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                resolver = ResourceResolver(wad)
                with patch.object(resolver, "maps", side_effect=RuntimeError("boom")):
                    report = analyze(resolver)
            codes = {it.code for it in report.items}
            assert "MAP_ASSEMBLY_FAILED" in codes
        finally:
            os.unlink(path)

    def test_map_assembly_failed_does_not_crash(self) -> None:
        """analyze() must return a report (not raise) when map assembly fails."""
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                resolver = ResourceResolver(wad)
                with patch.object(resolver, "maps", side_effect=RuntimeError("oops")):
                    report = analyze(resolver)
            assert isinstance(report, ValidationReport)
        finally:
            os.unlink(path)

    def test_udmf_crossref_warning_surfaced(self) -> None:
        """UDMF maps with cross-reference problems produce UDMF_WARNING items."""
        # linedef references v1=99 but only 1 vertex exists
        textmap = (
            b'namespace = "doom";\n'
            b"vertex { x = 0.0; y = 0.0; }\n"
            b"linedef { v1 = 99; v2 = 0; sidefront = 0; }\n"
        )
        lumps = [("MAP01", b""), ("TEXTMAP", textmap), ("ENDMAP", b"")]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            udmf_warns = [it for it in report.items if it.code == "UDMF_WARNING"]
            assert any("v1=99" in it.message for it in udmf_warns)
        finally:
            os.unlink(path)

    def test_udmf_missing_texture_warns(self) -> None:
        """UDMF sidedef referencing an undefined texture produces MISSING_TEXTURE."""
        textmap = (
            b'namespace = "zdoom";\n'
            b'sector { texturefloor = "FLAT"; textureceiling = "FLAT"; }\n'
            b'sidedef { sector = 0; texturemiddle = "NOTHERE"; }\n'
        )
        pnames = _pnames_lump(["WALL00_1"])
        texture1 = _texture1_lump([("MYWALL", [0])])
        lumps = [
            ("PNAMES", pnames),
            ("TEXTURE1", texture1),
            ("MAP01", b""),
            ("TEXTMAP", textmap),
            ("ENDMAP", b""),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = [it.code for it in report.items]
            assert "MISSING_TEXTURE" in codes
        finally:
            os.unlink(path)

    def test_udmf_valid_texture_no_missing_warning(self) -> None:
        """UDMF sidedef using a defined texture produces no MISSING_TEXTURE warning."""
        textmap = (
            b'namespace = "zdoom";\n'
            b'sector { texturefloor = "FLAT"; textureceiling = "FLAT"; }\n'
            b'sidedef { sector = 0; texturemiddle = "MYWALL"; }\n'
        )
        pnames = _pnames_lump(["WALL00_1"])
        texture1 = _texture1_lump([("MYWALL", [0])])
        lumps = [
            ("PNAMES", pnames),
            ("TEXTURE1", texture1),
            ("MAP01", b""),
            ("TEXTMAP", textmap),
            ("ENDMAP", b""),
        ]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            tex_warns = [it for it in report.items if it.code == "MISSING_TEXTURE"]
            assert tex_warns == []
        finally:
            os.unlink(path)

    def test_udmf_no_texture_data_no_false_positives(self) -> None:
        """UDMF map with no TEXTURE1 in the WAD skips texture checks (no false alarms)."""
        textmap = b'namespace = "zdoom";\nsidedef { sector = 0; texturemiddle = "ANYTHING"; }\n'
        lumps = [("MAP01", b""), ("TEXTMAP", textmap), ("ENDMAP", b"")]
        path = _wad_file(lumps)
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            tex_warns = [it for it in report.items if it.code == "MISSING_TEXTURE"]
            assert tex_warns == []
        finally:
            os.unlink(path)

    def test_no_udmf_warnings_for_classic_map(self) -> None:
        """A classic binary map must not produce UDMF_WARNING items."""
        path = _wad_file([("MAP01", b""), ("THINGS", b""), ("LINEDEFS", b"")])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = {it.code for it in report.items}
            assert "UDMF_WARNING" not in codes
        finally:
            os.unlink(path)

    def test_pk3_textures_category_included_in_collection(self) -> None:
        """PK3 entries under textures/ must appear in the texture name set."""
        path = _pk3_file({"textures/MYTEX.png": b"\x89PNG"})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                names = _collect_texture_names(r)
            assert "MYTEX" in names
        finally:
            os.unlink(path)

    def test_pk3_patches_category_included_in_collection(self) -> None:
        """PK3 entries under patches/ must appear in the texture name set."""
        path = _pk3_file({"patches/PATCH1.lmp": b"\x00" * 4})
        try:
            with Pk3Archive(path) as pk3:
                r = ResourceResolver(pk3)
                names = _collect_texture_names(r)
            assert "PATCH1" in names
        finally:
            os.unlink(path)

    def test_texture_parse_failed_diagnostic(self) -> None:
        """A corrupt TEXTURE1 must produce TEXTURE_PARSE_FAILED, not a crash."""
        # Valid PNAMES (1 patch), corrupt TEXTURE1 (count=1 but no offsets).
        pnames_data = struct.pack("<I", 1) + b"PATCH0\x00\x00"
        texture1_data = struct.pack("<I", 1)  # count=1 but offset table is missing
        path = _wad_file([("PNAMES", pnames_data), ("TEXTURE1", texture1_data)])
        try:
            with WadFile(path) as wad:
                report = analyze(wad)
            codes = {it.code for it in report.items}
            assert "TEXTURE_PARSE_FAILED" in codes
        finally:
            os.unlink(path)

    def test_collision_check_failed_diagnostic(self) -> None:
        """analyze() must emit COLLISION_CHECK_FAILED if resolver.collisions() raises."""
        path = _wad_file([])
        try:
            with WadFile(path) as wad:
                resolver = ResourceResolver(wad)
                with patch.object(resolver, "collisions", side_effect=RuntimeError("bad")):
                    report = analyze(resolver)
            codes = {it.code for it in report.items}
            assert "COLLISION_CHECK_FAILED" in codes
        finally:
            os.unlink(path)
