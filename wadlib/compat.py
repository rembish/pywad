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
    from .writer import WadWriter


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
    if wad.find_lump("ZMAPINFO"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "ZMAPINFO lump"))
    if wad.find_lump("LANGUAGE"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "LANGUAGE lump"))
    if wad.find_lump("SNDINFO"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "SNDINFO lump"))
    if wad.find_lump("DECORATE"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "DECORATE lump"))
    if wad.find_lump("ZSCRIPT"):
        features.append(CompLevelFeature(CompLevel.ZDOOM, "ZSCRIPT lump"))
    if wad.find_lump("GLDEFS"):
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
    if wad.find_lump("ANIMATED"):
        features.append(CompLevelFeature(CompLevel.BOOM, "ANIMATED lump (Boom binary animations)"))
    if wad.find_lump("SWITCHES"):
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


# ---------------------------------------------------------------------------
# Conversion actions
# ---------------------------------------------------------------------------


@dataclass
class ConvertAction:
    """A single conversion step when changing compatibility level."""

    description: str
    auto: bool  # True = can be applied automatically; False = needs manual work
    lossy: bool  # True = information is lost


@dataclass
class ConvertResult:
    """Result of a compatibility level conversion attempt."""

    source_level: CompLevel
    target_level: CompLevel
    applied: list[str]
    skipped: list[ConvertAction]


def plan_downgrade(wad: WadFile, target: CompLevel) -> list[ConvertAction]:
    """Plan the steps needed to downgrade a WAD to *target* comp level.

    Returns a list of actions.  Actions with ``auto=True`` can be applied
    by :func:`convert_complevel`.  Actions with ``auto=False`` need manual
    intervention or external tools.
    """
    features = detect_features(wad)
    actions: list[ConvertAction] = []

    for feat in features:
        if feat.level <= target:
            continue

        reason = feat.reason

        # --- Strippable lumps (auto, lossy metadata) ---
        if "ANIMATED lump" in reason:
            actions.append(ConvertAction("Remove ANIMATED lump", auto=True, lossy=True))
        elif "SWITCHES lump" in reason:
            actions.append(ConvertAction("Remove SWITCHES lump", auto=True, lossy=True))
        elif "ZMAPINFO lump" in reason:
            actions.append(ConvertAction("Remove ZMAPINFO lump", auto=True, lossy=True))
        elif "LANGUAGE lump" in reason:
            actions.append(ConvertAction("Remove LANGUAGE lump", auto=True, lossy=True))
        elif "SNDINFO lump" in reason:
            actions.append(ConvertAction("Remove SNDINFO lump", auto=True, lossy=True))
        elif "GLDEFS lump" in reason:
            actions.append(ConvertAction("Remove GLDEFS lump", auto=True, lossy=True))

        # --- Thing flag stripping (auto, lossy) ---
        elif "NOT_DEATHMATCH flag" in reason:
            actions.append(
                ConvertAction(
                    f"Clear NOT_DEATHMATCH flags in {reason.split(' in ')[-1]}",
                    auto=True,
                    lossy=True,
                )
            )
        elif "NOT_COOP flag" in reason:
            actions.append(
                ConvertAction(
                    f"Clear NOT_COOP flags in {reason.split(' in ')[-1]}",
                    auto=True,
                    lossy=True,
                )
            )
        elif "FRIENDLY flag" in reason:
            actions.append(
                ConvertAction(
                    f"Clear FRIENDLY flags in {reason.split(' in ')[-1]}",
                    auto=True,
                    lossy=True,
                )
            )
        elif "MBF Helper Dog" in reason:
            actions.append(
                ConvertAction(
                    f"Remove MBF Helper Dog things in {reason.split(' in ')[-1]}",
                    auto=True,
                    lossy=True,
                )
            )

        # --- UDMF → binary (auto, lossy) ---
        elif "TEXTMAP lump" in reason:
            actions.append(
                ConvertAction(
                    "Convert UDMF TEXTMAP to binary Doom map format "
                    "(loses floating-point precision and extended properties)",
                    auto=True,
                    lossy=True,
                )
            )

        # --- Cannot auto-convert ---
        elif "generalized linedef" in reason:
            actions.append(
                ConvertAction(
                    f"Generalized linedef specials have no vanilla equivalent: {reason}",
                    auto=False,
                    lossy=True,
                )
            )
        elif "ZNODES" in reason:
            actions.append(
                ConvertAction(
                    f"ZNODES need external node builder to rebuild as vanilla BSP: {reason}",
                    auto=False,
                    lossy=False,
                )
            )
        elif "DECORATE" in reason or "ZSCRIPT" in reason:
            actions.append(
                ConvertAction(
                    f"Cannot downgrade scripted actors: {reason}",
                    auto=False,
                    lossy=True,
                )
            )
        elif "exceeds vanilla limit" in reason:
            actions.append(
                ConvertAction(
                    f"Map geometry exceeds vanilla limits: {reason}",
                    auto=False,
                    lossy=False,
                )
            )
        else:
            actions.append(
                ConvertAction(
                    f"Unknown feature needs manual review: {reason}",
                    auto=False,
                    lossy=False,
                )
            )

    return actions


def convert_complevel(
    wad: WadFile,
    target: CompLevel,
    output_path: str,
) -> ConvertResult:
    """Attempt to convert a WAD to a lower compatibility level.

    Applies all auto-convertible actions and saves the result to
    *output_path*.  Returns a ``ConvertResult`` with details of what
    was applied and what was skipped.

    Example::

        from wadlib.compat import convert_complevel, CompLevel
        from wadlib.wad import WadFile

        with WadFile("mod.wad") as wad:
            result = convert_complevel(wad, CompLevel.VANILLA, "mod_vanilla.wad")
            for action in result.applied:
                print(f"  Applied: {action}")
            for action in result.skipped:
                print(f"  SKIPPED: {action.description}")
    """
    from .writer import WadWriter

    source_level = detect_complevel(wad)
    actions = plan_downgrade(wad, target)
    writer = WadWriter.from_wad(wad)

    applied: list[str] = []
    skipped: list[ConvertAction] = []

    for action in actions:
        if not action.auto:
            skipped.append(action)
            continue

        desc = action.description

        # Strip lumps
        for lump_name in ("ANIMATED", "SWITCHES", "ZMAPINFO", "LANGUAGE", "SNDINFO", "GLDEFS"):
            if f"Remove {lump_name} lump" == desc:
                if writer.remove_lump(lump_name):
                    applied.append(desc)
                break
        else:
            # Thing flag operations
            if "Clear NOT_DEATHMATCH flags" in desc:
                _clear_thing_flags(writer, 0x0020)
                applied.append(desc)
            elif "Clear NOT_COOP flags" in desc:
                _clear_thing_flags(writer, 0x0040)
                applied.append(desc)
            elif "Clear FRIENDLY flags" in desc:
                _clear_thing_flags(writer, 0x0080)
                applied.append(desc)
            elif "Remove MBF Helper Dog" in desc:
                _remove_thing_type(writer, 888)
                applied.append(desc)
            elif "Convert UDMF TEXTMAP" in desc:
                if _convert_udmf_to_binary(writer):
                    applied.append(desc)
                else:
                    skipped.append(action)
            else:
                skipped.append(action)

    writer.save(output_path)
    return ConvertResult(
        source_level=source_level,
        target_level=target,
        applied=applied,
        skipped=skipped,
    )


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _clear_thing_flags(writer: WadWriter, flag_mask: int) -> None:
    """Clear a flag bit from all THINGS lumps in the writer."""
    import struct

    keep_mask = 0xFFFF & ~flag_mask
    for i, entry in enumerate(writer.lumps):
        if entry.name != "THINGS" or not entry.data:
            continue
        data = bytearray(entry.data)
        # Each thing is 10 bytes; flags at offset 8 (uint16)
        for pos in range(0, len(data) - 9, 10):
            flags = struct.unpack_from("<H", data, pos + 8)[0]
            flags &= keep_mask
            struct.pack_into("<H", data, pos + 8, flags)
        writer.lumps[i].data = bytes(data)


def _remove_thing_type(writer: WadWriter, type_id: int) -> None:
    """Remove all things of a given type from THINGS lumps."""
    import struct

    for i, entry in enumerate(writer.lumps):
        if entry.name != "THINGS" or not entry.data:
            continue
        data = entry.data
        new_data = bytearray()
        for pos in range(0, len(data) - 9, 10):
            thing_type = struct.unpack_from("<H", data, pos + 6)[0]
            if thing_type != type_id:
                new_data.extend(data[pos : pos + 10])
        writer.lumps[i].data = bytes(new_data)


def _convert_udmf_to_binary(writer: WadWriter) -> bool:
    """Convert UDMF TEXTMAP lumps to binary Doom format in the writer."""
    import struct

    from .lumps.udmf import parse_udmf

    # Find TEXTMAP lumps and their map markers
    idx = 0
    converted_any = False
    while idx < len(writer.lumps):
        entry = writer.lumps[idx]
        if entry.name != "TEXTMAP":
            idx += 1
            continue

        # Parse UDMF
        try:
            udmf = parse_udmf(entry.data.decode("utf-8", errors="replace"))
        except (ValueError, KeyError, IndexError):
            idx += 1
            continue

        # Remove TEXTMAP and ENDMAP
        writer.lumps.pop(idx)  # remove TEXTMAP
        # Check if next is ENDMAP
        if idx < len(writer.lumps) and writer.lumps[idx].name == "ENDMAP":
            writer.lumps.pop(idx)

        # Build binary lumps at the same position
        # THINGS
        things_data = bytearray()
        for t in udmf.things:
            things_data += struct.pack("<hhHHH", int(t.x), int(t.y), t.angle, t.type, 0x0007)
        writer.lumps.insert(idx, type(entry)("THINGS", bytes(things_data)))
        idx += 1

        # LINEDEFS
        lines_data = bytearray()
        for ld in udmf.linedefs:
            lines_data += struct.pack(
                "<HHHHHhh",
                ld.v1,
                ld.v2,
                int(ld.props.get("blocking", False)),
                ld.special,
                0,
                ld.sidefront,
                ld.sideback,
            )
        writer.lumps.insert(idx, type(entry)("LINEDEFS", bytes(lines_data)))
        idx += 1

        # SIDEDEFS
        sides_data = bytearray()
        for sd in udmf.sidedefs:
            sides_data += struct.pack(
                "<hh8s8s8sH",
                sd.offsetx,
                sd.offsety,
                sd.texturetop.encode("ascii")[:8].ljust(8, b"\x00"),
                sd.texturebottom.encode("ascii")[:8].ljust(8, b"\x00"),
                sd.texturemiddle.encode("ascii")[:8].ljust(8, b"\x00"),
                sd.sector,
            )
        writer.lumps.insert(idx, type(entry)("SIDEDEFS", bytes(sides_data)))
        idx += 1

        # VERTEXES
        verts_data = bytearray()
        for v in udmf.vertices:
            verts_data += struct.pack("<hh", int(v.x), int(v.y))
        writer.lumps.insert(idx, type(entry)("VERTEXES", bytes(verts_data)))
        idx += 1

        # SECTORS
        sectors_data = bytearray()
        for sec in udmf.sectors:
            sectors_data += struct.pack(
                "<hh8s8sHHH",
                sec.heightfloor,
                sec.heightceiling,
                sec.texturefloor.encode("ascii")[:8].ljust(8, b"\x00"),
                sec.textureceiling.encode("ascii")[:8].ljust(8, b"\x00"),
                sec.lightlevel,
                sec.special,
                sec.id,
            )
        writer.lumps.insert(idx, type(entry)("SECTORS", bytes(sectors_data)))
        idx += 1

        # BSP lumps are omitted — they need an external node builder
        # (e.g. zdbsp, glbsp) to be regenerated from the geometry.
        # The WAD reader handles missing BSP lumps gracefully (set to None).

        converted_any = True

    return converted_any
