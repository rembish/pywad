"""SNDSEQ lump parser (Hexen) — named sound sequence scripts."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from functools import cached_property

from .base import BaseLump


@dataclass
class SndSeqCommand:
    """A single command line within a sound sequence."""

    command: str  # e.g. "playrepeat", "playuntildone", "stopsound"
    sound: str | None  # logical sound name argument, if any
    tics: int | None  # optional numeric argument (e.g. playtime delay)


@dataclass
class SndSeq:
    """A named sound sequence (one :Label … end block)."""

    name: str
    commands: list[SndSeqCommand] = field(default_factory=list)


class SndSeqLump(BaseLump):
    """SNDSEQ lump: scripted ambient/door/platform sound sequences."""

    @cached_property
    def sequences(self) -> list[SndSeq]:
        """Return all named sequences defined in SNDSEQ."""
        result: list[SndSeq] = []
        current: SndSeq | None = None

        text = self.raw().decode("latin-1")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            if stripped.startswith(":"):
                # New sequence block
                current = SndSeq(name=stripped[1:].strip())
                result.append(current)
                continue

            if current is None:
                continue

            if stripped.lower() == "end":
                current = None
                continue

            parts = stripped.split()
            cmd = parts[0].lower()
            sound = parts[1] if len(parts) >= 2 else None
            tics: int | None = None
            if len(parts) >= 3:
                with contextlib.suppress(ValueError):
                    tics = int(parts[2])
            current.commands.append(SndSeqCommand(command=cmd, sound=sound, tics=tics))

        return result

    def get(self, name: str) -> SndSeq | None:  # type: ignore[override]  # pylint: disable=arguments-differ
        """Return the sequence with the given name, or None."""
        return next((s for s in self.sequences if s.name.lower() == name.lower()), None)
