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
    sector { heightfloor = 0; heightceiling = 128; texturefloor = "FLAT1"; textureceiling = "CEIL3_5"; }

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
    r'"([^"]*)"'  # quoted string
    r"|"
    r"(true|false)"  # boolean
    r"|"
    r"(-?[\d]+\.[\d]*|-?\.[\d]+)"  # float
    r"|"
    r"(-?[\d]+)"  # integer
    r")\s*;"
)
_BLOCK_START_RE = re.compile(r"(\w+)\s*\{")
_BLOCK_END_RE = re.compile(r"\}")


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


def parse_udmf(text: str) -> UdmfMap:
    """Parse a UDMF TEXTMAP string into a UdmfMap."""
    # Strip comments
    text = _COMMENT_RE.sub("", text)

    result = UdmfMap()

    # Extract namespace
    ns_match = re.search(r'namespace\s*=\s*"([^"]+)"\s*;', text)
    if ns_match:
        result.namespace = ns_match.group(1)

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
                props[key] = m.group(2)  # string
            elif m.group(3) is not None:
                props[key] = m.group(3) == "true"  # boolean
            elif m.group(4) is not None:
                props[key] = float(m.group(4))  # float
            elif m.group(5) is not None:
                props[key] = int(m.group(5))  # integer

        if block_type == "thing":
            result.things.append(UdmfThing(props=props))
        elif block_type == "vertex":
            result.vertices.append(UdmfVertex(props=props))
        elif block_type == "linedef":
            result.linedefs.append(UdmfLinedef(props=props))
        elif block_type == "sidedef":
            result.sidedefs.append(UdmfSidedef(props=props))
        elif block_type == "sector":
            result.sectors.append(UdmfSector(props=props))

    return result


class UdmfLump(BaseLump[Any]):
    """A TEXTMAP lump containing UDMF map data."""

    @cached_property
    def parsed(self) -> UdmfMap:
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
