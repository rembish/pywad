"""UDMF (Universal Doom Map Format) parser and serializer.

UDMF is a text-based map format used by ZDoom, GZDoom, and other modern
source ports.  A UDMF map is stored as a single TEXTMAP lump between
the map marker and ENDMAP.

The format is a series of blocks::

    namespace = "zdoom";

    thing { x = 64.0; y = -128.0; type = 1; }
    vertex { x = 0.0; y = 0.0; }
    linedef { v1 = 0; v2 = 1; sidefront = 0; }
    sidedef { sector = 0; texturemiddle = "BRICK1"; }
    sector { heightfloor = 0; heightceiling = 128;
             texturefloor = "FLAT1"; textureceiling = "CEIL3_5"; }

All values are either integers, floats, strings (quoted), or booleans (true/false).

Reference: https://doomwiki.org/wiki/UDMF
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from .base import BaseLump

# Regex patterns for UDMF tokenizing
_COMMENT_RE = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/")
_ASSIGNMENT_RE = re.compile(
    r"(\w+)\s*=\s*"
    r"(?:"
    r'"((?:[^"\\]|\\.)*)"'  # quoted string (handles \" and \\ escapes)
    r"|"
    r"(true|false)"  # boolean
    r"|"
    r"(-?[\d]+\.[\d]*|-?\.[\d]+)"  # float
    r"|"
    r"(-?0[xX][0-9a-fA-F]+|-?[\d]+)"  # integer: hex (0x…) or decimal
    r")\s*;"
)
_BLOCK_START_RE = re.compile(r"(\w+)\s*\{")
_BLOCK_END_RE = re.compile(r"\}")

_KNOWN_NAMESPACES: frozenset[str] = frozenset(
    {"doom", "heretic", "hexen", "strife", "zdoom", "gzdoom", "eternity", "vavoom"}
)

# ---------------------------------------------------------------------------
# Per-namespace field allowlists for the props catch-all dict.
# Fields already promoted to struct attributes (x, y, angle, type, id, etc.)
# are never in props, so they are not listed here.
# ---------------------------------------------------------------------------

_BASE_THING_PROPS: frozenset[str] = frozenset(
    {
        "skill1",
        "skill2",
        "skill3",
        "skill4",
        "skill5",
        "ambush",
        "single",
        "dm",
        "coop",
        "comment",
    }
)
_BASE_VERTEX_PROPS: frozenset[str] = frozenset({"comment"})
_BASE_LINEDEF_PROPS: frozenset[str] = frozenset(
    {
        "blocking",
        "blockmonsters",
        "twosided",
        "dontpegtop",
        "dontpegbottom",
        "secret",
        "blocksound",
        "dontdraw",
        "mapped",
        "arg0",
        "arg1",
        "arg2",
        "arg3",
        "arg4",
        "comment",
    }
)
_BASE_SIDEDEF_PROPS: frozenset[str] = frozenset({"comment"})
_BASE_SECTOR_PROPS: frozenset[str] = frozenset({"comment"})

# Hexen adds action specials on things and higher difficulty tiers.
_HEXEN_THING_PROPS: frozenset[str] = _BASE_THING_PROPS | frozenset(
    {
        "special",
        "arg0",
        "arg1",
        "arg2",
        "arg3",
        "arg4",
        "skill6",
        "skill7",
        "skill8",
        "dormant",
        "class1",
        "class2",
        "class3",
        "standing",
    }
)

# Strife adds conversation references and allied-NPC flags.
_STRIFE_THING_PROPS: frozenset[str] = _BASE_THING_PROPS | frozenset(
    {
        "conversation",
        "strifeally",
        "standing",
        "translucent",
        "invisible",
    }
)

# ZDoom / GZDoom — broad extension set covering the published ZDoom UDMF spec.
# Not exhaustive (the port is still evolving), but covers all documented fields.
_ZDOOM_THING_PROPS: frozenset[str] = (
    _HEXEN_THING_PROPS
    | _STRIFE_THING_PROPS
    | frozenset({"friendlyname", "gravity", "countsecret", "renderstyle", "alpha", "fillcolor"})
)
_ZDOOM_VERTEX_PROPS: frozenset[str] = _BASE_VERTEX_PROPS | frozenset({"zfloor", "zceiling"})
_ZDOOM_LINEDEF_PROPS: frozenset[str] = _BASE_LINEDEF_PROPS | frozenset(
    {
        "alpha",
        "renderstyle",
        "anycross",
        "monsteractivate",
        "blockplayers",
        "blockeverything",
        "firstsideonly",
        "zoneboundary",
        "clipmidtex",
        "wrapmidtex",
        "midtex3d",
        "checkswitchrange",
        "blockprojectiles",
        "blockuse",
        "blocksight",
        "blockhitscan",
        "impact",
        "playeruse",
        "missilecross",
        "playercross",
        "monstercross",
        "repeatspecial",
        "passuse",
    }
)
_ZDOOM_SIDEDEF_PROPS: frozenset[str] = _BASE_SIDEDEF_PROPS | frozenset(
    {
        "scalex_top",
        "scaley_top",
        "scalex_mid",
        "scaley_mid",
        "scalex_bot",
        "scaley_bot",
        "offsetx_top",
        "offsety_top",
        "offsetx_mid",
        "offsety_mid",
        "offsetx_bot",
        "offsety_bot",
        "light",
        "lightabsolute",
        "lightfog",
        "nofakecontrast",
        "smooth_lighting",
        "clipmidtex",
        "wrapmidtex",
        "nodecals",
    }
)
_ZDOOM_SECTOR_PROPS: frozenset[str] = _BASE_SECTOR_PROPS | frozenset(
    {
        "xpanningfloor",
        "ypanningfloor",
        "xpanningceiling",
        "ypanningceiling",
        "xscalefloor",
        "yscalefloor",
        "xscaleceiling",
        "yscaleceiling",
        "rotationfloor",
        "rotationceiling",
        "lightfloor",
        "lightceiling",
        "lightfloorabsolute",
        "lightceilingabsolute",
        "alphafloor",
        "alphaceiling",
        "renderstylefloor",
        "renderstyleceiling",
        "desaturation",
        "silent",
        "nofallingdamage",
        "dropactors",
        "norespawn",
        "leakiness",
        "damageamount",
        "damagehazard",
        "damagetype",
        "damageterraineffect",
        "damageinterval",
        "floorterrain",
        "ceilingterrain",
        "lightcolor",
        "fadecolor",
        "fogdensity",
        "floorlightlevel",
        "ceilinglightlevel",
        "floorlightabsolute",
        "ceilinglightabsolute",
        "gravity",
        "floor_reflect",
        "ceiling_reflect",
        "hidden",
        "waterzone",
        "moreids",
        "colormap",
    }
)

# (thing, vertex, linedef, sidedef, sector) allowlists per namespace.
_NS_ALLOWLISTS: dict[
    str,
    tuple[frozenset[str], frozenset[str], frozenset[str], frozenset[str], frozenset[str]],
] = {
    "doom": (
        _BASE_THING_PROPS,
        _BASE_VERTEX_PROPS,
        _BASE_LINEDEF_PROPS,
        _BASE_SIDEDEF_PROPS,
        _BASE_SECTOR_PROPS,
    ),
    "heretic": (
        _BASE_THING_PROPS,
        _BASE_VERTEX_PROPS,
        _BASE_LINEDEF_PROPS,
        _BASE_SIDEDEF_PROPS,
        _BASE_SECTOR_PROPS,
    ),
    "hexen": (
        _HEXEN_THING_PROPS,
        _BASE_VERTEX_PROPS,
        _BASE_LINEDEF_PROPS,
        _BASE_SIDEDEF_PROPS,
        _BASE_SECTOR_PROPS,
    ),
    "strife": (
        _STRIFE_THING_PROPS,
        _BASE_VERTEX_PROPS,
        _BASE_LINEDEF_PROPS,
        _BASE_SIDEDEF_PROPS,
        _BASE_SECTOR_PROPS,
    ),
    "zdoom": (
        _ZDOOM_THING_PROPS,
        _ZDOOM_VERTEX_PROPS,
        _ZDOOM_LINEDEF_PROPS,
        _ZDOOM_SIDEDEF_PROPS,
        _ZDOOM_SECTOR_PROPS,
    ),
    "gzdoom": (
        _ZDOOM_THING_PROPS,
        _ZDOOM_VERTEX_PROPS,
        _ZDOOM_LINEDEF_PROPS,
        _ZDOOM_SIDEDEF_PROPS,
        _ZDOOM_SECTOR_PROPS,
    ),
    "eternity": (
        _ZDOOM_THING_PROPS,
        _ZDOOM_VERTEX_PROPS,
        _ZDOOM_LINEDEF_PROPS,
        _ZDOOM_SIDEDEF_PROPS,
        _ZDOOM_SECTOR_PROPS,
    ),
    "vavoom": (
        _ZDOOM_THING_PROPS,
        _ZDOOM_VERTEX_PROPS,
        _ZDOOM_LINEDEF_PROPS,
        _ZDOOM_SIDEDEF_PROPS,
        _ZDOOM_SECTOR_PROPS,
    ),
}


@dataclass
class UdmfThing:
    """A UDMF thing definition."""

    x: float = 0.0
    y: float = 0.0
    height: float = 0.0
    angle: int = 0
    type: int = 0
    id: int = 0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Pull known fields from props if present
        for attr in ("x", "y", "height", "angle", "type", "id"):
            if attr in self.props:
                setattr(self, attr, self.props.pop(attr))


@dataclass
class UdmfVertex:
    """A UDMF vertex definition."""

    x: float = 0.0
    y: float = 0.0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in ("x", "y"):
            if attr in self.props:
                setattr(self, attr, self.props.pop(attr))


@dataclass
class UdmfLinedef:
    """A UDMF linedef definition."""

    v1: int = 0
    v2: int = 0
    sidefront: int = -1
    sideback: int = -1
    special: int = 0
    id: int = 0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in ("v1", "v2", "sidefront", "sideback", "special", "id"):
            if attr in self.props:
                setattr(self, attr, self.props.pop(attr))


@dataclass
class UdmfSidedef:
    """A UDMF sidedef definition."""

    sector: int = 0
    texturetop: str = "-"
    texturebottom: str = "-"
    texturemiddle: str = "-"
    offsetx: int = 0
    offsety: int = 0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in (
            "sector",
            "texturetop",
            "texturebottom",
            "texturemiddle",
            "offsetx",
            "offsety",
        ):
            if attr in self.props:
                setattr(self, attr, self.props.pop(attr))


@dataclass
class UdmfSector:
    """A UDMF sector definition."""

    heightfloor: int = 0
    heightceiling: int = 128
    texturefloor: str = "-"
    textureceiling: str = "-"
    lightlevel: int = 160
    special: int = 0
    id: int = 0
    props: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for attr in (
            "heightfloor",
            "heightceiling",
            "texturefloor",
            "textureceiling",
            "lightlevel",
            "special",
            "id",
        ):
            if attr in self.props:
                setattr(self, attr, self.props.pop(attr))


@dataclass
class UdmfMap:
    """A fully parsed UDMF map."""

    namespace: str = "doom"
    things: list[UdmfThing] = field(default_factory=list)
    vertices: list[UdmfVertex] = field(default_factory=list)
    linedefs: list[UdmfLinedef] = field(default_factory=list)
    sidedefs: list[UdmfSidedef] = field(default_factory=list)
    sectors: list[UdmfSector] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _validate_by_namespace(result: UdmfMap) -> list[str]:
    """Return structural and namespace-specific warnings for a parsed UdmfMap.

    Checks performed:

    * **Cross-reference integrity** — linedef vertex/sidedef indices must be in
      range; sidedef sector indices must be in range.
    * **Per-namespace field allowlists** — any field in the ``props`` catch-all
      dict that is not defined in the UDMF spec for the map's namespace produces
      an ``"unknown field(s)"`` warning.  Allowlists are defined for
      ``doom``, ``heretic``, ``hexen``, ``strife``, and the ZDoom family
      (``zdoom``, ``gzdoom``, ``eternity``, ``vavoom``).  Unknown namespaces
      skip this check.
    """
    warnings: list[str] = []
    ns = result.namespace.lower()
    n_verts = len(result.vertices)
    n_sides = len(result.sidedefs)
    n_sectors = len(result.sectors)

    # --- Cross-reference integrity ---
    for i, ld in enumerate(result.linedefs):
        if not 0 <= ld.v1 < n_verts:
            warnings.append(f"linedef {i}: v1={ld.v1} out of range (map has {n_verts} vertices)")
        if not 0 <= ld.v2 < n_verts:
            warnings.append(f"linedef {i}: v2={ld.v2} out of range (map has {n_verts} vertices)")
        if ld.sidefront >= 0 and not ld.sidefront < n_sides:
            warnings.append(
                f"linedef {i}: sidefront={ld.sidefront} out of range (map has {n_sides} sidedefs)"
            )
        if ld.sideback >= 0 and not ld.sideback < n_sides:
            warnings.append(
                f"linedef {i}: sideback={ld.sideback} out of range (map has {n_sides} sidedefs)"
            )

    for i, sd in enumerate(result.sidedefs):
        if not 0 <= sd.sector < n_sectors:
            warnings.append(
                f"sidedef {i}: sector={sd.sector} out of range (map has {n_sectors} sectors)"
            )

    # --- Per-namespace field allowlists ---
    ns_entry = _NS_ALLOWLISTS.get(ns)
    if ns_entry is not None:
        thing_allow, vertex_allow, linedef_allow, sidedef_allow, sector_allow = ns_entry
        for i, t in enumerate(result.things):
            unknown = sorted(set(t.props) - thing_allow)
            if unknown:
                warnings.append(
                    f"thing {i}: unknown field(s) for '{ns}' namespace: {', '.join(unknown)}"
                )
        for i, v in enumerate(result.vertices):
            unknown = sorted(set(v.props) - vertex_allow)
            if unknown:
                warnings.append(
                    f"vertex {i}: unknown field(s) for '{ns}' namespace: {', '.join(unknown)}"
                )
        for i, ld in enumerate(result.linedefs):
            unknown = sorted(set(ld.props) - linedef_allow)
            if unknown:
                warnings.append(
                    f"linedef {i}: unknown field(s) for '{ns}' namespace: {', '.join(unknown)}"
                )
        for i, sd in enumerate(result.sidedefs):
            unknown = sorted(set(sd.props) - sidedef_allow)
            if unknown:
                warnings.append(
                    f"sidedef {i}: unknown field(s) for '{ns}' namespace: {', '.join(unknown)}"
                )
        for i, sec in enumerate(result.sectors):
            unknown = sorted(set(sec.props) - sector_allow)
            if unknown:
                warnings.append(
                    f"sector {i}: unknown field(s) for '{ns}' namespace: {', '.join(unknown)}"
                )

    return warnings


class UdmfParseError(ValueError):
    """Raised by :func:`parse_udmf` when ``strict=True`` and the text is malformed."""


def parse_udmf(text: str, *, strict: bool = False) -> UdmfMap:
    """Parse a UDMF TEXTMAP string into a UdmfMap.

    Parameters
    ----------
    text:
        Raw TEXTMAP lump content.
    strict:
        When *True*, raise :class:`UdmfParseError` if no ``namespace``
        declaration is found in non-empty input.
    """
    # Strip comments
    text = _COMMENT_RE.sub("", text)

    result = UdmfMap()

    # Extract namespace
    ns_match = re.search(r'namespace\s*=\s*"([^"]+)"\s*;', text)
    if ns_match:
        result.namespace = ns_match.group(1)
        if result.namespace.lower() not in _KNOWN_NAMESPACES:
            result.warnings.append(
                f"unknown namespace '{result.namespace}'; "
                f"known: {', '.join(sorted(_KNOWN_NAMESPACES))}"
            )
    elif strict and text.strip():
        raise UdmfParseError("no namespace declaration found in TEXTMAP")

    # Parse blocks
    pos = 0
    while pos < len(text):
        block_match = _BLOCK_START_RE.search(text, pos)
        if not block_match:
            break

        block_type = block_match.group(1).lower()
        block_start = block_match.end()

        # Find matching closing brace
        end_match = _BLOCK_END_RE.search(text, block_start)
        if not end_match:
            break

        block_body = text[block_start : end_match.start()]
        pos = end_match.end()

        # Parse key=value pairs inside the block
        props: dict[str, Any] = {}
        for m in _ASSIGNMENT_RE.finditer(block_body):
            key = m.group(1)
            if m.group(2) is not None:
                # Unescape \" and \\ sequences inside quoted strings
                props[key] = m.group(2).replace('\\"', '"').replace("\\\\", "\\")
            elif m.group(3) is not None:
                props[key] = m.group(3) == "true"  # boolean
            elif m.group(4) is not None:
                props[key] = float(m.group(4))  # float
            elif m.group(5) is not None:
                props[key] = int(m.group(5), 0)  # decimal or hex (0x…)

        if block_type == "thing":
            idx = len(result.things)
            if "type" not in props:
                result.warnings.append(f"thing {idx}: missing required field 'type'")
            result.things.append(UdmfThing(props=props))
        elif block_type == "vertex":
            if "x" not in props:
                result.warnings.append(f"vertex {len(result.vertices)} missing x coordinate")
            if "y" not in props:
                result.warnings.append(f"vertex {len(result.vertices)} missing y coordinate")
            result.vertices.append(UdmfVertex(props=props))
        elif block_type == "linedef":
            idx = len(result.linedefs)
            if "v1" not in props:
                result.warnings.append(f"linedef {idx} missing v1")
            if "v2" not in props:
                result.warnings.append(f"linedef {idx} missing v2")
            if "sidefront" not in props:
                result.warnings.append(f"linedef {idx} missing sidefront")
            result.linedefs.append(UdmfLinedef(props=props))
        elif block_type == "sidedef":
            idx = len(result.sidedefs)
            if "sector" not in props:
                result.warnings.append(f"sidedef {idx}: missing required field 'sector'")
            result.sidedefs.append(UdmfSidedef(props=props))
        elif block_type == "sector":
            idx = len(result.sectors)
            if "texturefloor" not in props:
                result.warnings.append(f"sector {idx}: missing required field 'texturefloor'")
            if "textureceiling" not in props:
                result.warnings.append(f"sector {idx}: missing required field 'textureceiling'")
            result.sectors.append(UdmfSector(props=props))

    result.warnings.extend(_validate_by_namespace(result))
    return result


class UdmfLump(BaseLump[Any]):
    """A TEXTMAP lump containing UDMF map data."""

    @cached_property
    def parsed(self) -> UdmfMap:
        """The TEXTMAP lump decoded as a :class:`UdmfMap` (lazy, cached on first access)."""
        return parse_udmf(self.raw().decode("utf-8", errors="replace"))


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def _format_value(v: Any) -> str:
    """Format a value for UDMF output."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        # Use enough precision, strip trailing zeros
        s = f"{v:.6f}".rstrip("0").rstrip(".")
        if "." not in s:
            s += ".0"
        return s
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def _write_block(name: str, known: dict[str, Any], extra: dict[str, Any]) -> str:
    """Serialize a single UDMF block."""
    lines = [f"{name}\n{{"]
    all_props = {**known, **extra}
    for key, val in all_props.items():
        lines.append(f"  {key} = {_format_value(val)};")
    lines.append("}")
    return "\n".join(lines)


def serialize_udmf(udmf_map: UdmfMap) -> str:
    """Serialize a UdmfMap to a UDMF TEXTMAP string."""
    parts: list[str] = []
    parts.append(f'namespace = "{udmf_map.namespace}";')
    parts.append("")

    for t in udmf_map.things:
        t_known: dict[str, Any] = {}
        if t.id != 0:
            t_known["id"] = t.id
        t_known["x"] = t.x
        t_known["y"] = t.y
        if t.height != 0.0:
            t_known["height"] = t.height
        t_known["angle"] = t.angle
        t_known["type"] = t.type
        parts.append(_write_block("thing", t_known, t.props))
        parts.append("")

    for v in udmf_map.vertices:
        v_known: dict[str, Any] = {"x": v.x, "y": v.y}
        parts.append(_write_block("vertex", v_known, v.props))
        parts.append("")

    for ld in udmf_map.linedefs:
        ld_known: dict[str, Any] = {"v1": ld.v1, "v2": ld.v2}
        if ld.sidefront >= 0:
            ld_known["sidefront"] = ld.sidefront
        if ld.sideback >= 0:
            ld_known["sideback"] = ld.sideback
        if ld.special != 0:
            ld_known["special"] = ld.special
        if ld.id != 0:
            ld_known["id"] = ld.id
        parts.append(_write_block("linedef", ld_known, ld.props))
        parts.append("")

    for sd in udmf_map.sidedefs:
        sd_known: dict[str, Any] = {"sector": sd.sector}
        if sd.texturetop != "-":
            sd_known["texturetop"] = sd.texturetop
        if sd.texturebottom != "-":
            sd_known["texturebottom"] = sd.texturebottom
        if sd.texturemiddle != "-":
            sd_known["texturemiddle"] = sd.texturemiddle
        if sd.offsetx != 0:
            sd_known["offsetx"] = sd.offsetx
        if sd.offsety != 0:
            sd_known["offsety"] = sd.offsety
        parts.append(_write_block("sidedef", sd_known, sd.props))
        parts.append("")

    for sec in udmf_map.sectors:
        sec_known: dict[str, Any] = {
            "heightfloor": sec.heightfloor,
            "heightceiling": sec.heightceiling,
            "texturefloor": sec.texturefloor,
            "textureceiling": sec.textureceiling,
            "lightlevel": sec.lightlevel,
        }
        if sec.special != 0:
            sec_known["special"] = sec.special
        if sec.id != 0:
            sec_known["id"] = sec.id
        parts.append(_write_block("sector", sec_known, sec.props))
        parts.append("")

    return "\n".join(parts)
