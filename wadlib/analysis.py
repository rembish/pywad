"""Read-side diagnostics and structured analysis for WAD files and PK3 archives.

This module provides a library-level validation API that works across both
``WadFile`` and ``Pk3Archive`` sources (via ``ResourceResolver``).  It is
distinct from :mod:`wadlib.validate`, which is a *writer-side* API for
checking lump data before writing.

Usage::

    from wadlib.analysis import analyze
    from wadlib.wad import WadFile

    with WadFile("doom2.wad") as wad:
        report = analyze(wad)
        print(report.complevel)        # CompLevel.VANILLA
        print(len(report.errors))      # 0
        for item in report.warnings:
            print(item)

    # Works on resolvers too:
    from wadlib.resolver import ResourceResolver
    with WadFile("doom2.wad") as base, WadFile("mod.wad") as mod:
        resolver = ResourceResolver.doom_load_order(base, mod)
        report = analyze(resolver)

Public API:

- :func:`analyze` — the single entry point.
- :class:`ValidationReport` — structured report with ``.errors``,
  ``.warnings``, ``.unsupported_features``, ``.complevel``, and
  ``.to_dict()``.
- :class:`DiagnosticItem` — a single finding.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .compat import CompLevel, detect_features
from .pk3 import Pk3Archive
from .resolver import ResourceResolver
from .validate import Severity
from .wad import WadFile

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiagnosticItem:
    """A single diagnostic finding produced by :func:`analyze`.

    Attributes:
        code:     Machine-readable issue code (e.g. ``"MISSING_TEXTURE"``).
        severity: :attr:`~wadlib.validate.Severity.ERROR` or
                  :attr:`~wadlib.validate.Severity.WARNING`.
        context:  Where the issue was found — usually a map name or lump name.
        message:  Human-readable description of the problem.
    """

    code: str
    severity: Severity
    context: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable dict."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "context": self.context,
            "message": self.message,
        }

    def __repr__(self) -> str:
        return f"<{self.severity.value.upper()} [{self.code}] {self.context}: {self.message}>"


@dataclass
class ValidationReport:
    """Structured diagnostics report returned by :func:`analyze`.

    Attributes:
        items:                All diagnostic items (errors and warnings combined),
                              in the order they were discovered.
        unsupported_features: Human-readable strings describing source-port
                              features detected in the content (e.g.
                              ``"ZMAPINFO lump"``).  These are not errors — they
                              describe what the content requires.
        complevel:            The minimum :class:`~wadlib.compat.CompLevel`
                              required by any WAD source in the resolver, or
                              ``None`` if no WAD sources were found (e.g. a
                              PK3-only resolver).
    """

    items: list[DiagnosticItem] = field(default_factory=list)
    unsupported_features: list[str] = field(default_factory=list)
    complevel: CompLevel | None = None

    @property
    def errors(self) -> list[DiagnosticItem]:
        """All items with severity ERROR."""
        return [it for it in self.items if it.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[DiagnosticItem]:
        """All items with severity WARNING."""
        return [it for it in self.items if it.severity is Severity.WARNING]

    @property
    def is_clean(self) -> bool:
        """True if there are no errors (warnings are allowed)."""
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of this report."""
        return {
            "complevel": self.complevel.label if self.complevel is not None else None,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "is_clean": self.is_clean,
            "unsupported_features": list(self.unsupported_features),
            "items": [it.to_dict() for it in self.items],
        }


# ---------------------------------------------------------------------------
# Internal helpers — texture / flat name collection
# ---------------------------------------------------------------------------

# Textures used as sky placeholders — never defined in TEXTUREx, always valid.
_SKY_TEXTURES: frozenset[str] = frozenset(
    {"F_SKY1", "F_SKY2", "F_SKY3", "F_SKY4", "SKY1", "SKY2", "SKY3", "SKY4"}
)
# Sentinel meaning "no texture here".
_NO_TEXTURE = "-"


def _wad_texture_names(wad: WadFile) -> frozenset[str]:
    names: set[str] = set()
    for tl in (wad.texture1, wad.texture2):
        if tl:
            # Suppress parse errors here; _check_pnames emits TEXTURE_PARSE_FAILED
            # for the same failure so callers don't lose diagnostics.
            with contextlib.suppress(Exception):
                names.update(t.name.upper() for t in tl.textures)
    names |= _SKY_TEXTURES
    return frozenset(names)


def _wad_flat_names(wad: WadFile) -> frozenset[str]:
    return frozenset(n.upper() for n in wad.flats) | _SKY_TEXTURES


def _collect_texture_names(resolver: ResourceResolver) -> frozenset[str]:
    """Union all texture names from every source in the resolver.

    Covers TEXTUREx WAD lumps, ZDoom TEXTURES text lumps (best-effort),
    and PK3 ``textures/`` / ``patches/`` directory entries.
    """
    names: set[str] = set(_SKY_TEXTURES)
    for src in resolver._sources:  # pylint: disable=protected-access
        if isinstance(src, WadFile):
            names.update(_wad_texture_names(src))
            # ZDoom TEXTURES lump (text-based): best-effort.  Parse failures
            # cause extra MISSING_TEXTURE warnings rather than false-clean reports.
            entry = src.find_lump("TEXTURES")
            if entry is not None:
                with contextlib.suppress(Exception):
                    from .lumps.texturex import TexturesLump

                    lump = TexturesLump(entry)
                    names.update(d.name.upper() for d in lump.definitions)
        else:
            # PK3: textures live under textures/ and patches/ category directories.
            for ref in src.infolist():
                if ref.category in ("textures", "patches"):
                    names.add(ref.lump_name)
    return frozenset(names)


def _collect_flat_names(resolver: ResourceResolver) -> frozenset[str]:
    """Union all flat names from every WAD source in the resolver."""
    names: set[str] = set(_SKY_TEXTURES)
    for src in resolver._sources:  # pylint: disable=protected-access
        if isinstance(src, WadFile):
            names.update(_wad_flat_names(src))
        else:
            # PK3: flats live under the "flats" category namespace
            for ref in src.infolist():
                if ref.category == "flats":
                    names.add(ref.lump_name)
    return frozenset(names)


# ---------------------------------------------------------------------------
# Internal helpers — per-map checks
# ---------------------------------------------------------------------------


def _check_map_refs(
    map_entry: BaseMapEntry,
) -> list[DiagnosticItem]:
    """Check linedef vertex/sidedef indices and sidedef sector indices."""
    items: list[DiagnosticItem] = []
    name = map_entry.name

    # UDMF maps use text-based geometry; binary attributes may be None.
    if map_entry.udmf is not None:
        return items

    lines = map_entry.lines
    vertices = map_entry.vertices
    sidedefs = map_entry.sidedefs
    sectors = map_entry.sectors

    from .lumps.lines import LineDefinition

    if lines and vertices:
        vertex_count = len(vertices)
        sidedef_count = len(sidedefs) if sidedefs else 0
        for i, line in enumerate(lines):
            if not isinstance(line, LineDefinition):
                continue
            if line.start_vertex >= vertex_count:
                items.append(
                    DiagnosticItem(
                        code="BAD_VERTEX_REF",
                        severity=Severity.ERROR,
                        context=name,
                        message=(
                            f"linedef {i}: start_vertex {line.start_vertex} >= {vertex_count}"
                        ),
                    )
                )
            if line.finish_vertex >= vertex_count:
                items.append(
                    DiagnosticItem(
                        code="BAD_VERTEX_REF",
                        severity=Severity.ERROR,
                        context=name,
                        message=(
                            f"linedef {i}: finish_vertex {line.finish_vertex} >= {vertex_count}"
                        ),
                    )
                )
            if 0 < sidedef_count <= line.right_sidedef:
                items.append(
                    DiagnosticItem(
                        code="BAD_SIDEDEF_REF",
                        severity=Severity.ERROR,
                        context=name,
                        message=(
                            f"linedef {i}: right_sidedef {line.right_sidedef} >= {sidedef_count}"
                        ),
                    )
                )
            if line.left_sidedef != -1 and 0 < sidedef_count <= line.left_sidedef:
                items.append(
                    DiagnosticItem(
                        code="BAD_SIDEDEF_REF",
                        severity=Severity.ERROR,
                        context=name,
                        message=(
                            f"linedef {i}: left_sidedef {line.left_sidedef} >= {sidedef_count}"
                        ),
                    )
                )

    if sidedefs and sectors:
        sector_count = len(sectors)
        for i, sd in enumerate(sidedefs):
            if sd.sector >= sector_count:
                items.append(
                    DiagnosticItem(
                        code="BAD_SECTOR_REF",
                        severity=Severity.ERROR,
                        context=name,
                        message=f"sidedef {i}: sector {sd.sector} >= {sector_count}",
                    )
                )

    return items


def _check_map_textures(
    map_entry: BaseMapEntry,
    textures: frozenset[str],
    flats: frozenset[str],
) -> list[DiagnosticItem]:
    """Check sidedefs for missing textures and sectors for missing flats."""
    items: list[DiagnosticItem] = []
    name = map_entry.name

    # UDMF: skip (texture names are in the TEXTMAP, resolution is port-specific)
    if map_entry.udmf is not None:
        return items
    # No texture data to check against — skip silently
    if not textures - _SKY_TEXTURES and not flats - _SKY_TEXTURES:
        return items

    if map_entry.sidedefs and textures - _SKY_TEXTURES:
        for i, sd in enumerate(map_entry.sidedefs):
            for field_name, val in (
                ("upper_texture", sd.upper_texture.upper()),
                ("lower_texture", sd.lower_texture.upper()),
                ("middle_texture", sd.middle_texture.upper()),
            ):
                if val != _NO_TEXTURE and val not in textures:
                    items.append(
                        DiagnosticItem(
                            code="MISSING_TEXTURE",
                            severity=Severity.WARNING,
                            context=name,
                            message=f"sidedef {i} {field_name}: '{val}'",
                        )
                    )

    if map_entry.sectors and flats - _SKY_TEXTURES:
        for i, sec in enumerate(map_entry.sectors):
            for field_name, val in (
                ("floor_texture", sec.floor_texture.upper()),
                ("ceiling_texture", sec.ceiling_texture.upper()),
            ):
                if val != _NO_TEXTURE and val not in flats:
                    items.append(
                        DiagnosticItem(
                            code="MISSING_FLAT",
                            severity=Severity.WARNING,
                            context=name,
                            message=f"sector {i} {field_name}: '{val}'",
                        )
                    )

    return items


# ---------------------------------------------------------------------------
# Internal helpers — PNAMES integrity
# ---------------------------------------------------------------------------


def _check_pnames(resolver: ResourceResolver) -> list[DiagnosticItem]:
    """Check that every patch_index in TEXTURE1/2 is within PNAMES bounds."""
    items: list[DiagnosticItem] = []
    for src in resolver._sources:  # pylint: disable=protected-access
        if not isinstance(src, WadFile):
            continue
        pnames = src.pnames
        if pnames is None:
            continue
        pnames_count = len(pnames)
        for tl_name, tl in (("TEXTURE1", src.texture1), ("TEXTURE2", src.texture2)):
            if tl is None:
                continue
            try:
                textures = tl.textures
            except Exception as exc:  # pylint: disable=broad-exception-caught
                items.append(
                    DiagnosticItem(
                        code="TEXTURE_PARSE_FAILED",
                        severity=Severity.WARNING,
                        context=tl_name,
                        message=f"Failed to parse {tl_name}: {exc}",
                    )
                )
                continue
            for tex in textures:
                for patch in tex.patches:
                    if patch.patch_index >= pnames_count:
                        items.append(
                            DiagnosticItem(
                                code="BAD_PNAMES_INDEX",
                                severity=Severity.ERROR,
                                context=tl_name,
                                message=(
                                    f"texture '{tex.name}': patch_index"
                                    f" {patch.patch_index} >= PNAMES count"
                                    f" {pnames_count}"
                                ),
                            )
                        )
    return items


# ---------------------------------------------------------------------------
# Internal helpers — resource collisions
# ---------------------------------------------------------------------------


def _check_collisions(resolver: ResourceResolver) -> list[DiagnosticItem]:
    """Warn about resource names that appear more than once across sources."""
    items: list[DiagnosticItem] = []
    try:
        clashes = resolver.collisions()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        items.append(
            DiagnosticItem(
                code="COLLISION_CHECK_FAILED",
                severity=Severity.WARNING,
                context="collisions",
                message=f"Collision check failed: {exc}",
            )
        )
        return items
    for name, refs in clashes.items():
        winner = refs[0]
        losers = refs[1:]
        items.append(
            DiagnosticItem(
                code="RESOURCE_COLLISION",
                severity=Severity.WARNING,
                context=name,
                message=(
                    f"'{name}' found {len(refs)} time(s); "
                    f"winner: {winner.archive!r}, "
                    f"{len(losers)} shadowed"
                ),
            )
        )
    return items


# ---------------------------------------------------------------------------
# Internal helpers — compatibility level
# ---------------------------------------------------------------------------


def _check_complevel(
    resolver: ResourceResolver,
) -> tuple[CompLevel | None, list[str]]:
    """Return (detected complevel, list of feature strings) across WAD sources."""
    all_features = []
    has_wad = False
    for src in resolver._sources:  # pylint: disable=protected-access
        if isinstance(src, WadFile):
            has_wad = True
            with contextlib.suppress(Exception):
                all_features.extend(detect_features(src))

    has_pk3 = any(isinstance(s, Pk3Archive) for s in resolver._sources)  # pylint: disable=protected-access

    if not all_features:
        if has_wad:
            # WAD present but no special features → Vanilla
            complevel: CompLevel | None = CompLevel.VANILLA
        elif has_pk3:
            complevel = CompLevel.ZDOOM
        else:
            complevel = None
        return complevel, []

    detected = max(f.level for f in all_features)
    feature_strs = [f.reason for f in all_features]
    return detected, feature_strs


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze(source: WadFile | Pk3Archive | ResourceResolver) -> ValidationReport:
    """Analyze a WAD file, PK3 archive, or resolver and return a structured report.

    Checks performed:

    - **Map reference integrity**: linedef vertex indices, sidedef indices, and
      sidedef-to-sector references are validated against their respective lump
      sizes.  UDMF maps are skipped (their geometry is text-based).
    - **Missing textures / flats**: sidedef texture names and sector flat names
      are checked against the texture and flat names known to each WAD source.
      Only runs when texture/flat data is present.
    - **PNAMES integrity**: every ``patch_index`` in TEXTURE1/TEXTURE2 is
      validated to lie within the bounds of the PNAMES patch list.
    - **Resource collisions**: resource names that appear more than once across
      sources are reported as warnings.
    - **Compatibility level**: the minimum
      :class:`~wadlib.compat.CompLevel` required by WAD sources is detected and
      stored in :attr:`~ValidationReport.complevel`.  Features that imply a
      specific compat level are listed in
      :attr:`~ValidationReport.unsupported_features`.

    Args:
        source: A :class:`~wadlib.wad.WadFile`, :class:`~wadlib.pk3.Pk3Archive`,
                or :class:`~wadlib.resolver.ResourceResolver`.  Non-resolver
                inputs are wrapped in a single-source resolver internally so all
                checks use the same code path.

    Returns:
        A :class:`ValidationReport` instance.
    """
    resolver = ResourceResolver(source) if isinstance(source, (WadFile, Pk3Archive)) else source

    report = ValidationReport()

    # Compat level and unsupported features
    complevel, features = _check_complevel(resolver)
    report.complevel = complevel
    report.unsupported_features = features

    # Gather texture / flat name sets once (across all WAD sources)
    textures = _collect_texture_names(resolver)
    flats = _collect_flat_names(resolver)

    # Assembled maps across all sources
    try:
        maps = resolver.maps()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        report.items.append(
            DiagnosticItem(
                code="MAP_ASSEMBLY_FAILED",
                severity=Severity.WARNING,
                context="maps",
                message=f"Map assembly failed: {exc}",
            )
        )
        maps = {}

    # Emit a single note for UDMF maps whose texture/flat validation is skipped.
    udmf_map_names = [n for n, m in maps.items() if m.udmf is not None]
    if udmf_map_names:
        ctx = ", ".join(udmf_map_names[:5])
        if len(udmf_map_names) > 5:
            ctx += f" \u2026 ({len(udmf_map_names)} total)"
        report.items.append(
            DiagnosticItem(
                code="UDMF_TEXTURE_CHECK_SKIPPED",
                severity=Severity.WARNING,
                context=ctx,
                message="UDMF maps: texture and flat validation skipped (port-specific resolution)",
            )
        )

    # Per-map checks
    for map_entry in maps.values():
        report.items.extend(_check_map_refs(map_entry))
        report.items.extend(_check_map_textures(map_entry, textures, flats))

    # PNAMES integrity
    report.items.extend(_check_pnames(resolver))

    # Resource collisions
    report.items.extend(_check_collisions(resolver))

    return report
