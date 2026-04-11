"""Compatibility level detection and conversion for WAD files.

Doom source ports implement different feature sets.  This module detects
which compatibility level a WAD targets based on its contents, and can
report what needs to change for up/downgrading.

Compatibility levels (from strictest to most permissive):

- **Vanilla**  — original Doom engine limits.  Max 128 visplanes, 64KB
  BLOCKMAP, 16-bit indices, basic linedef specials (0-141).
- **Limit-removing** — vanilla format, static limits removed.
- **Boom**     — generalized linedef types, ANIMATED/SWITCHES lumps,
  extended DEHACKED, Boom thing flags (NOT_DEATHMATCH, NOT_COOP).
- **MBF**      — MBF codepointers, FRIENDLY flag, helper dog (type 888).
- **MBF21**    — MBF21 thing/linedef flags, new codepointers.
- **ZDoom**    — ZMAPINFO, ZNODES, LANGUAGE, SNDINFO, DECORATE.
- **UDMF**     — text-based map format (TEXTMAP lump, no binary map data).

Usage::

    from wadlib.compat import detect_complevel, CompLevel, check_downgrade

    level = detect_complevel(wad)           # CompLevel.BOOM
    issues = check_downgrade(wad, CompLevel.VANILLA)
    # [DowngradeIssue("ANIMATED lump requires Boom or higher"), ...]
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wad import WadFile


class CompLevel(IntEnum):
    """Compatibility levels, ordered from strictest to most permissive."""

    VANILLA = 0
    LIMIT_REMOVING = 1
    BOOM = 2
    MBF = 3
    MBF21 = 4
    ZDOOM = 5
    UDMF = 6

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS: dict[CompLevel, str] = {
    CompLevel.VANILLA: "Vanilla Doom",
    CompLevel.LIMIT_REMOVING: "Limit-removing",
    CompLevel.BOOM: "Boom",
    CompLevel.MBF: "MBF",
    CompLevel.MBF21: "MBF21",
    CompLevel.ZDOOM: "ZDoom",
    CompLevel.UDMF: "UDMF",
}


@dataclass(frozen=True)
class CompLevelFeature:
    """A feature detected in a WAD that implies a minimum compatibility level."""

    level: CompLevel
    reason: str

    def __repr__(self) -> str:
        return f"<{self.level.label}: {self.reason}>"


@dataclass(frozen=True)
class DowngradeIssue:
    """An obstacle preventing downgrade to a lower compatibility level."""

    feature: str
    current_level: CompLevel
    message: str

    def __repr__(self) -> str:
        return f"<DowngradeIssue: {self.message}>"


# ---------------------------------------------------------------------------
# Vanilla limits (for limit-removing detection)
# ---------------------------------------------------------------------------

_VANILLA_LIMITS = {
    "segs": 32768,
    "subsectors": 32768,
    "nodes": 32768,
    "vertices": 32768,
    "linedefs": 32768,
    "sidedefs": 32768,
    "sectors": 256,  # Doom's soft limit (REJECT table)
}

_BLOCKMAP_VANILLA_MAX = 65536  # 64KB


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def detect_features(wad: WadFile) -> list[CompLevelFeature]:
    """Scan a WAD and return all features that imply specific compatibility levels."""
    features: list[CompLevelFeature] = []

    # --- UDMF ---
    for entry in wad.directory:
        if entry.name == "TEXTMAP":
            features.append(CompLevelFeature(CompLevel.UDMF, "TEXTMAP lump (UDMF map format)"))
            break

    # --- ZDoom features ---
    if wad._find_lump("ZMAPINFO"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "ZMAPINFO lump"))
    if wad._find_lump("LANGUAGE"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "LANGUAGE lump"))
    if wad._find_lump("SNDINFO"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "SNDINFO lump"))
    if wad._find_lump("DECORATE"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "DECORATE lump"))
    if wad._find_lump("ZSCRIPT"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "ZSCRIPT lump"))
    if wad._find_lump("GLDEFS"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "GLDEFS lump"))

    # ZNODES in any map
    for m in wad.maps:
        if hasattr(m, "segs") and m.segs is not None:
            # Check if it's a ZNodList (from ZNODES) vs regular Segs
            from .lumps.znodes import ZNodList

            if isinstance(m.segs, ZNodList):
                features.append(CompLevelFeature(CompLevel.ZDOOM, f"ZNODES in {m.name}"))
                break

    # --- Boom features ---
    if wad._find_lump("ANIMATED"):
        features.append(CompLevelFeature(CompLevel.BOOM, "ANIMATED lump (Boom binary animations)"))
    if wad._find_lump("SWITCHES"):
        features.append(CompLevelFeature(CompLevel.BOOM, "SWITCHES lump (Boom switch textures)"))

    # Check for Boom thing flags or generalized linedef types in maps
    for m in wad.maps:
        if m.things is not None:
            from .lumps.things import Thing

            for t_item in m.things:
                if isinstance(t_item, Thing):
                    flags = int(t_item.flags)
                    if flags & 0x0020:  # NOT_DEATHMATCH
                        features.append(
                            CompLevelFeature(CompLevel.BOOM, f"NOT_DEATHMATCH flag in {m.name}")
                        )
                        break
                    if flags & 0x0040:  # NOT_COOP
                        features.append(
                            CompLevelFeature(CompLevel.BOOM, f"NOT_COOP flag in {m.name}")
                        )
                        break
                    if flags & 0x0080:  # FRIENDLY (MBF)
                        features.append(
                            CompLevelFeature(CompLevel.MBF, f"FRIENDLY flag in {m.name}")
                        )
                        break
            # Check for MBF helper dog
            for t_item in m.things or []:
                if isinstance(t_item, Thing) and t_item.type == 888:
                    features.append(CompLevelFeature(CompLevel.MBF, f"MBF Helper Dog in {m.name}"))
                    break

        # Check for generalized linedefs (Boom)
        if m.lines is not None:
            from .lumps.lines import LineDefinition

            for line in m.lines:
                if isinstance(line, LineDefinition) and line.special_type >= 0x2F80:
                    features.append(
                        CompLevelFeature(
                            CompLevel.BOOM,
                            f"generalized linedef {line.special_type:#06x} in {m.name}",
                        )
                    )
                    break

    # --- Limit-removing ---
    for m in wad.maps:
        for lump_name, lump_attr in [
            ("segs", m.segs),
            ("vertices", m.vertices),
            ("sidedefs", m.sidedefs),
            ("sectors", m.sectors),
        ]:
            if lump_attr is not None and hasattr(lump_attr, "__len__"):
                count = len(lump_attr)
                limit = _VANILLA_LIMITS.get(lump_name, 32768)
                if count > limit:
                    features.append(
                        CompLevelFeature(
                            CompLevel.LIMIT_REMOVING,
                            f"{m.name}: {count} {lump_name} exceeds vanilla limit ({limit})",
                        )
                    )

        # Blockmap size check
        if m.blockmap is not None:
            bm_size = len(m.blockmap.to_bytes())
            if bm_size > _BLOCKMAP_VANILLA_MAX:
                features.append(
                    CompLevelFeature(
                        CompLevel.LIMIT_REMOVING,
                        f"{m.name}: BLOCKMAP {bm_size} bytes exceeds vanilla 64KB limit",
                    )
                )

    return features


def detect_complevel(wad: WadFile) -> CompLevel:
    """Detect the minimum compatibility level required by a WAD.

    Scans the WAD for features that require specific source port support
    and returns the highest (most permissive) level needed.
    """
    features = detect_features(wad)
    if not features:
        return CompLevel.VANILLA
    return max(f.level for f in features)


# ---------------------------------------------------------------------------
# Downgrade checking
# ---------------------------------------------------------------------------


def check_downgrade(wad: WadFile, target: CompLevel) -> list[DowngradeIssue]:
    """Check what prevents a WAD from being downgraded to *target* level.

    Returns a list of issues.  An empty list means the WAD is already
    compatible with *target*.

    Example::

        issues = check_downgrade(wad, CompLevel.VANILLA)
        for issue in issues:
            print(f"[{issue.current_level.label}] {issue.message}")
    """
    features = detect_features(wad)
    issues: list[DowngradeIssue] = []

    for feat in features:
        if feat.level > target:
            issues.append(
                DowngradeIssue(
                    feature=feat.reason,
                    current_level=feat.level,
                    message=f"requires {feat.level.label}: {feat.reason}",
                )
            )

    return issues


def check_upgrade(wad: WadFile, target: CompLevel) -> list[str]:
    """List features available at *target* level that the WAD could use.

    This is informational — shows what becomes possible when upgrading.
    """
    current = detect_complevel(wad)
    suggestions: list[str] = []

    if current < CompLevel.BOOM <= target:
        suggestions.append("Boom: generalized linedef types, ANIMATED/SWITCHES lumps")
    if current < CompLevel.MBF <= target:
        suggestions.append("MBF: FRIENDLY thing flag, helper dog (type 888), MBF codepointers")
    if current < CompLevel.MBF21 <= target:
        suggestions.append("MBF21: extended thing/linedef flags, new codepointers")
    if current < CompLevel.ZDOOM <= target:
        suggestions.append("ZDoom: ZMAPINFO, ZNODES, DECORATE actors, SNDINFO, LANGUAGE")
    if current < CompLevel.UDMF <= target:
        suggestions.append(
            "UDMF: text-based maps, floating-point coordinates, unlimited properties"
        )

    return suggestions
