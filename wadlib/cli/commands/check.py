"""wadcli check -- sanity-check a WAD for common authoring errors."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

from ...lumps.lines import LineDefinition
from ...lumps.map import BaseMapEntry
from ...wad import WadFile
from .._wad_args import open_wad

# Textures used as sky (never stored in TEXTURE1/2) -- treat as valid.
_SKY_TEXTURES = frozenset({"F_SKY1", "F_SKY2", "F_SKY3", "F_SKY4", "SKY1", "SKY2", "SKY3", "SKY4"})
# Sentinel value meaning "no texture here" -- always valid.
_NO_TEXTURE = "-"


@dataclass
class Issue:
    map: str
    kind: str
    message: str


def configure(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="output issues as JSON")
    p.set_defaults(func=run)


def _texture_names(wad: WadFile) -> frozenset[str]:
    names: set[str] = set()
    for tl in (wad.texture1, wad.texture2):
        if tl:
            names.update(t.name.upper() for t in tl.textures)
    names |= _SKY_TEXTURES
    return frozenset(names)


def _flat_names(wad: WadFile) -> frozenset[str]:
    return frozenset(n.upper() for n in wad.flats) | _SKY_TEXTURES


def _check_linedefs(m: BaseMapEntry, issues: list[Issue]) -> None:
    if not m.lines or not m.vertices:
        return
    name = m.name
    vertex_count = len(m.vertices)
    sidedef_count = len(m.sidedefs) if m.sidedefs else 0
    for i, line in enumerate(m.lines):
        if not isinstance(line, LineDefinition):
            continue
        if line.start_vertex >= vertex_count:
            issues.append(
                Issue(
                    name,
                    "bad_vertex",
                    f"linedef {i}: start_vertex {line.start_vertex} >= {vertex_count}",
                )
            )
        if line.finish_vertex >= vertex_count:
            issues.append(
                Issue(
                    name,
                    "bad_vertex",
                    f"linedef {i}: finish_vertex {line.finish_vertex} >= {vertex_count}",
                )
            )
        if line.right_sidedef >= sidedef_count:
            issues.append(
                Issue(
                    name,
                    "bad_sidedef",
                    f"linedef {i}: right_sidedef {line.right_sidedef} >= {sidedef_count}",
                )
            )
        if line.left_sidedef != -1 and line.left_sidedef >= sidedef_count:
            issues.append(
                Issue(
                    name,
                    "bad_sidedef",
                    f"linedef {i}: left_sidedef {line.left_sidedef} >= {sidedef_count}",
                )
            )


def _check_sidedefs(m: BaseMapEntry, textures: frozenset[str], issues: list[Issue]) -> None:
    if not m.sidedefs:
        return
    name = m.name
    sector_count = len(m.sectors) if m.sectors else 0
    for i, sd in enumerate(m.sidedefs):
        if sd.sector >= sector_count:
            issues.append(
                Issue(name, "bad_sector_ref", f"sidedef {i}: sector {sd.sector} >= {sector_count}")
            )
        for field, val in (
            ("upper_texture", sd.upper_texture.upper()),
            ("lower_texture", sd.lower_texture.upper()),
            ("middle_texture", sd.middle_texture.upper()),
        ):
            if val != _NO_TEXTURE and val not in textures:
                issues.append(Issue(name, "missing_texture", f"sidedef {i} {field}: '{val}'"))


def _check_sectors(m: BaseMapEntry, flats: frozenset[str], issues: list[Issue]) -> None:
    if not m.sectors:
        return
    name = m.name
    for i, sec in enumerate(m.sectors):
        for field, val in (
            ("floor_texture", sec.floor_texture.upper()),
            ("ceiling_texture", sec.ceiling_texture.upper()),
        ):
            if val != _NO_TEXTURE and val not in flats:
                issues.append(Issue(name, "missing_flat", f"sector {i} {field}: '{val}'"))


def _check_map(
    m: BaseMapEntry,
    textures: frozenset[str],
    flats: frozenset[str],
    issues: list[Issue],
) -> None:
    _check_linedefs(m, issues)
    _check_sidedefs(m, textures, issues)
    _check_sectors(m, flats, issues)


def run(args: argparse.Namespace) -> None:
    if not getattr(args, "wad", None):
        print("error: --wad is required for wadcli check", file=sys.stderr)
        sys.exit(1)

    with open_wad(args) as wad:
        textures = _texture_names(wad)
        flats = _flat_names(wad)
        issues: list[Issue] = []

        # Duplicate map names across the PWAD stack
        seen_maps: dict[str, int] = {}
        for m in wad.maps:
            seen_maps[m.name] = seen_maps.get(m.name, 0) + 1
        for map_name, count in seen_maps.items():
            if count > 1:
                issues.append(
                    Issue(map_name, "duplicate_map", f"map '{map_name}' appears {count} times")
                )

        for m in wad.maps:
            _check_map(m, textures, flats, issues)

    if args.json:
        print(
            json.dumps(
                [{"map": i.map, "kind": i.kind, "message": i.message} for i in issues], indent=2
            )
        )
    elif not issues:
        print("No issues found.")
    else:
        by_map: dict[str, list[Issue]] = {}
        for issue in issues:
            by_map.setdefault(issue.map, []).append(issue)
        for map_name, map_issues in sorted(by_map.items()):
            print(f"{map_name}: {len(map_issues)} issue(s)")
            for issue in map_issues:
                print(f"  [{issue.kind}] {issue.message}")
        print(f"\n{len(issues)} issue(s) in {len(by_map)} map(s).")

    sys.exit(1 if issues else 0)
