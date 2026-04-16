"""ZDoom TEXTURES lump parser — text-based texture definitions.

The TEXTURES lump is ZDoom's replacement for the binary TEXTUREx+PNAMES
system.  It defines composite textures using a readable text format with
features like rotation, scaling, flipping, and blending.

Syntax::

    Texture "MYBRICK", 128, 64
    {
        Patch "WALL00_1", 0, 0
        Patch "WALL00_2", 64, 0 { FlipX }
    }

    Flat "MYFLOOR", 64, 64
    {
        Patch "FLAT01", 0, 0
    }

    Sprite "MYSPRITE", 32, 56
    {
        Offset 16, 55
        Patch "TROOA1", 0, 0
    }

Reference: https://zdoom.org/wiki/TEXTURES
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal

from .base import BaseLump

_TEX_HEADER_RE = re.compile(
    r'^(Texture|Flat|Sprite|WallTexture|Graphic)\s+"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)',
    re.IGNORECASE,
)
_PATCH_RE = re.compile(
    r'^\s*Patch\s+"([^"]+)"\s*,\s*(-?\d+)\s*,\s*(-?\d+)',
    re.IGNORECASE,
)
_OFFSET_RE = re.compile(r"^\s*Offset\s+(-?\d+)\s*,\s*(-?\d+)", re.IGNORECASE)
_XSCALE_RE = re.compile(r"^\s*XScale\s+([\d.]+)", re.IGNORECASE)
_YSCALE_RE = re.compile(r"^\s*YScale\s+([\d.]+)", re.IGNORECASE)
_NAMESPACE_RE = re.compile(r"^\s*Namespace\s+\"?(\w+)\"?", re.IGNORECASE)
_BRACE_OPEN = re.compile(r"^\s*\{")
_BRACE_CLOSE = re.compile(r"^\s*\}")


@dataclass
class TexturesPatch:
    """A single patch reference within a TEXTURES definition."""

    name: str
    x: int = 0
    y: int = 0
    flip_x: bool = False
    flip_y: bool = False
    rotate: int = 0
    alpha: float = 1.0
    style: str = ""
    translation: str = ""
    blend: str = ""
    raw_props: dict[str, str] = field(default_factory=dict)


@dataclass
class TexturesDef:
    """A single texture/flat/sprite definition from a TEXTURES lump."""

    kind: Literal["texture", "flat", "sprite", "walltexture", "graphic"]
    name: str
    width: int
    height: int
    x_offset: int = 0
    y_offset: int = 0
    x_scale: float = 1.0
    y_scale: float = 1.0
    patches: list[TexturesPatch] = field(default_factory=list)
    namespace: str = ""
    optional: bool = False
    world_panning: bool = False
    no_decals: bool = False
    raw_props: dict[str, str] = field(default_factory=dict)


def _apply_patch_prop(patch: TexturesPatch, pline: str) -> None:
    """Apply a single patch property statement to *patch* (multi-line body form)."""
    pl = pline.lower()
    known = False
    if "flipx" in pl:
        patch.flip_x = True
        known = True
    if "flipy" in pl:
        patch.flip_y = True
        known = True
    rm = re.match(r"rotate\s+(-?\d+)", pline, re.IGNORECASE)
    if rm:
        patch.rotate = int(rm.group(1))
        known = True
    am = re.match(r"alpha\s+([\d.]+)", pline, re.IGNORECASE)
    if am:
        patch.alpha = float(am.group(1))
        known = True
    sm = re.match(r"style\s+(\w+)", pline, re.IGNORECASE)
    if sm:
        patch.style = sm.group(1)
        known = True
    tm = re.match(r"translation\s+(.*)", pline, re.IGNORECASE)
    if tm:
        patch.translation = tm.group(1).strip()
        known = True
    bm = re.match(r"blend\s+(.*)", pline, re.IGNORECASE)
    if bm:
        patch.blend = bm.group(1).strip()
        known = True
    if not known:
        km = re.match(r"(\w+)", pline)
        if km:
            patch.raw_props[km.group(1).lower()] = pline


def _apply_patch_props_inline(patch: TexturesPatch, content: str) -> None:
    """Parse space-separated inline patch properties (e.g. ``FlipX Rotate 90``)."""
    tokens = content.split()
    i = 0
    while i < len(tokens):
        tok = tokens[i].lower()
        if tok == "flipx":
            patch.flip_x = True
            i += 1
        elif tok == "flipy":
            patch.flip_y = True
            i += 1
        elif tok == "rotate" and i + 1 < len(tokens):
            with contextlib.suppress(ValueError):
                patch.rotate = int(tokens[i + 1])
            i += 2
        elif tok == "alpha" and i + 1 < len(tokens):
            with contextlib.suppress(ValueError):
                patch.alpha = float(tokens[i + 1])
            i += 2
        elif tok == "style" and i + 1 < len(tokens):
            patch.style = tokens[i + 1]
            i += 2
        elif tok == "translation" and i + 1 < len(tokens):
            patch.translation = tokens[i + 1]
            i += 2
        elif tok == "blend" and i + 1 < len(tokens):
            patch.blend = tokens[i + 1]
            i += 2
        else:
            patch.raw_props[tokens[i].lower()] = tokens[i]
            i += 1


def parse_textures(text: str) -> list[TexturesDef]:
    """Parse a ZDoom TEXTURES lump into a list of TexturesDef."""
    result: list[TexturesDef] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        i += 1

        # Skip comments and empty lines
        if not line or line.startswith("//"):
            continue

        # Texture/Flat/Sprite header
        m = _TEX_HEADER_RE.match(line)
        if not m:
            continue

        kind_raw = m.group(1).lower()
        kind: Literal["texture", "flat", "sprite", "walltexture", "graphic"]
        if kind_raw == "walltexture":
            kind = "walltexture"
        elif kind_raw == "graphic":
            kind = "graphic"
        elif kind_raw == "flat":
            kind = "flat"
        elif kind_raw == "sprite":
            kind = "sprite"
        else:
            kind = "texture"

        tex = TexturesDef(
            kind=kind,
            name=m.group(2),
            width=int(m.group(3)),
            height=int(m.group(4)),
        )

        # Skip to opening brace
        while i < len(lines):
            bline = lines[i].strip()
            i += 1
            if _BRACE_OPEN.match(bline):
                break

        # Parse body until closing brace
        while i < len(lines):
            bline = lines[i].strip()
            i += 1

            if _BRACE_CLOSE.match(bline):
                break

            # Skip comments
            if bline.startswith("//") or not bline:
                continue

            # Offset
            om = _OFFSET_RE.match(bline)
            if om:
                tex.x_offset = int(om.group(1))
                tex.y_offset = int(om.group(2))
                continue

            # Scale
            xm = _XSCALE_RE.match(bline)
            if xm:
                tex.x_scale = float(xm.group(1))
                continue
            ym = _YSCALE_RE.match(bline)
            if ym:
                tex.y_scale = float(ym.group(1))
                continue

            # Flags
            if re.match(r"^\s*Optional", bline, re.IGNORECASE):
                tex.optional = True
                continue
            if re.match(r"^\s*WorldPanning", bline, re.IGNORECASE):
                tex.world_panning = True
                continue
            if re.match(r"^\s*NoDecals", bline, re.IGNORECASE):
                tex.no_decals = True
                continue
            nm = _NAMESPACE_RE.match(bline)
            if nm:
                tex.namespace = nm.group(1)
                continue

            # Patch
            pm = _PATCH_RE.match(bline)
            if pm:
                patch = TexturesPatch(name=pm.group(1), x=int(pm.group(2)), y=int(pm.group(3)))
                rest = bline[pm.end() :].strip()
                if rest.startswith("{"):
                    # Block opens on the same line as the Patch statement.
                    after_brace = rest[1:]
                    close_pos = after_brace.find("}")
                    if close_pos != -1:
                        # Complete inline block: "Patch ..., x, y { FlipX Rotate 90 }"
                        _apply_patch_props_inline(patch, after_brace[:close_pos].strip())
                    else:
                        # Open inline: "Patch ..., x, y { FlipX"  (closes on a later line)
                        if after_brace.strip():
                            _apply_patch_props_inline(patch, after_brace.strip())
                        while i < len(lines):
                            pline = lines[i].strip()
                            i += 1
                            if _BRACE_CLOSE.match(pline):
                                break
                            if pline and not pline.startswith("//"):
                                _apply_patch_prop(patch, pline)
                elif i < len(lines) and _BRACE_OPEN.match(lines[i].strip()):
                    i += 1  # skip the opening brace line
                    while i < len(lines):
                        pline = lines[i].strip()
                        i += 1
                        if _BRACE_CLOSE.match(pline):
                            break
                        if pline and not pline.startswith("//"):
                            _apply_patch_prop(patch, pline)
                tex.patches.append(patch)
            else:
                km = re.match(r"(\w+)", bline)
                if km:
                    tex.raw_props[km.group(1).lower()] = bline

        result.append(tex)

    return result


def serialize_textures(defs: list[TexturesDef]) -> str:
    """Serialize a list of TexturesDef to TEXTURES lump text."""
    parts: list[str] = []

    for tex in defs:
        kind = tex.kind.capitalize()
        if kind == "Walltexture":
            kind = "WallTexture"
        parts.append(f'{kind} "{tex.name}", {tex.width}, {tex.height}')
        parts.append("{")

        if tex.x_offset != 0 or tex.y_offset != 0:
            parts.append(f"    Offset {tex.x_offset}, {tex.y_offset}")
        if tex.x_scale != 1.0:
            parts.append(f"    XScale {tex.x_scale}")
        if tex.y_scale != 1.0:
            parts.append(f"    YScale {tex.y_scale}")
        if tex.optional:
            parts.append("    Optional")
        if tex.world_panning:
            parts.append("    WorldPanning")
        if tex.no_decals:
            parts.append("    NoDecals")
        if tex.namespace:
            parts.append(f'    Namespace "{tex.namespace}"')
        for raw_val in tex.raw_props.values():
            parts.append(f"    {raw_val}")

        for p in tex.patches:
            has_props = (
                p.flip_x
                or p.flip_y
                or p.rotate != 0
                or p.alpha != 1.0
                or p.style
                or p.translation
                or p.blend
                or p.raw_props
            )
            if has_props:
                parts.append(f'    Patch "{p.name}", {p.x}, {p.y}')
                parts.append("    {")
                if p.flip_x:
                    parts.append("        FlipX")
                if p.flip_y:
                    parts.append("        FlipY")
                if p.rotate != 0:
                    parts.append(f"        Rotate {p.rotate}")
                if p.alpha != 1.0:
                    parts.append(f"        Alpha {p.alpha}")
                if p.style:
                    parts.append(f"        Style {p.style}")
                if p.translation:
                    parts.append(f"        Translation {p.translation}")
                if p.blend:
                    parts.append(f"        Blend {p.blend}")
                for raw_val in p.raw_props.values():
                    parts.append(f"        {raw_val}")
                parts.append("    }")
            else:
                parts.append(f'    Patch "{p.name}", {p.x}, {p.y}')

        parts.append("}")
        parts.append("")

    return "\n".join(parts)


class TexturesLump(BaseLump[Any]):
    """A ZDoom TEXTURES lump."""

    @cached_property
    def definitions(self) -> list[TexturesDef]:
        return parse_textures(self.raw().decode("utf-8", errors="replace"))
