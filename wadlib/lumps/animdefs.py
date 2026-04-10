"""ANIMDEFS lump parser (Hexen format) — animated flat/texture definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Literal

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


class AnimDefsLump(BaseLump):
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
