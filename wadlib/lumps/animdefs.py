"""ANIMDEFS lump parser (Hexen format) — animated flat/texture definitions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any, Literal

from .base import BaseLump


@dataclass
class AnimFrame:
    pic: int
    min_tics: int
    max_tics: int  # equals min_tics for fixed timing; > min_tics for rand


@dataclass
class AnimDef:
    kind: Literal["flat", "texture"]
    name: str
    frames: list[AnimFrame] = field(default_factory=list)

    @property
    def is_random(self) -> bool:
        return any(f.max_tics != f.min_tics for f in self.frames)

    def resolve_frames(self, ordered_names: Sequence[str]) -> list[str] | None:
        """Resolve animation frame indices to actual lump names.

        In the Hexen-style ANIMDEFS format each ``pic N`` directive refers to
        the *N*-th entry in directory order starting from this animation's base
        name.  ``pic 1`` is the base name itself; ``pic 2`` is the next entry
        after it; and so on.

        *ordered_names* must be the full ordered list for the appropriate
        resource kind — e.g. all flat names between ``F_START``/``F_END`` for
        a flat animation, or all texture names from ``TEXTURE1``/``TEXTURE2``
        for a texture animation.  The comparison is case-insensitive.

        Returns the resolved list of lump/texture names in frame order, or
        ``None`` if the base name is not found in *ordered_names* or any frame
        index falls outside the list bounds.

        Example::

            flat_names = ["NUKAGE1", "NUKAGE2", "NUKAGE3", "BLOOD1"]
            anim = AnimDef("flat", "NUKAGE1", [
                AnimFrame(pic=1, min_tics=8, max_tics=8),
                AnimFrame(pic=2, min_tics=8, max_tics=8),
                AnimFrame(pic=3, min_tics=8, max_tics=8),
            ])
            anim.resolve_frames(flat_names)
            # -> ["NUKAGE1", "NUKAGE2", "NUKAGE3"]
        """
        upper = self.name.upper()
        base_idx: int | None = None
        for i, n in enumerate(ordered_names):
            if n.upper() == upper:
                base_idx = i
                break
        if base_idx is None:
            return None

        result: list[str] = []
        for frame in self.frames:
            idx = base_idx + frame.pic - 1
            if idx < 0 or idx >= len(ordered_names):
                return None
            result.append(ordered_names[idx])
        return result


def serialize_animdefs(animations: list[AnimDef]) -> str:
    """Serialize a list of AnimDef to ANIMDEFS text."""
    parts: list[str] = []
    for a in animations:
        parts.append(f"{a.kind} {a.name}")
        for f in a.frames:
            if f.max_tics != f.min_tics:
                parts.append(f"  pic {f.pic} rand {f.min_tics} {f.max_tics}")
            else:
                parts.append(f"  pic {f.pic} tics {f.min_tics}")
        parts.append("")
    return "\n".join(parts)


class AnimDefsLump(BaseLump[Any]):
    """ANIMDEFS lump: flat and texture animation sequences."""

    @cached_property
    def animations(self) -> list[AnimDef]:
        """Return all animation definitions."""
        result: list[AnimDef] = []
        current: AnimDef | None = None

        text = self.raw().decode("latin-1")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            parts = stripped.split()
            keyword = parts[0].lower()

            if keyword in ("flat", "texture") and len(parts) >= 2:
                kind: Literal["flat", "texture"] = "flat" if keyword == "flat" else "texture"
                current = AnimDef(kind=kind, name=parts[1])
                result.append(current)

            elif keyword == "pic" and current is not None and len(parts) >= 4:
                pic = int(parts[1])
                timing = parts[2].lower()
                if timing == "tics" and len(parts) >= 4:
                    tics = int(parts[3])
                    current.frames.append(AnimFrame(pic=pic, min_tics=tics, max_tics=tics))
                elif timing == "rand" and len(parts) >= 5:
                    min_tics = int(parts[3])
                    max_tics = int(parts[4])
                    current.frames.append(AnimFrame(pic=pic, min_tics=min_tics, max_tics=max_tics))

        return result

    @property
    def flats(self) -> list[AnimDef]:
        return [a for a in self.animations if a.kind == "flat"]

    @property
    def textures(self) -> list[AnimDef]:
        return [a for a in self.animations if a.kind == "texture"]
