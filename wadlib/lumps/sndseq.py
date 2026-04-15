"""SNDSEQ lump parser (Hexen) — named sound sequence scripts."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

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


def serialize_sndseq(sequences: list[SndSeq]) -> str:
    """Serialize a list of SndSeq to SNDSEQ text."""
    parts: list[str] = []
    for seq in sequences:
        parts.append(f":{seq.name}")
        for cmd in seq.commands:
            line = f"  {cmd.command}"
            if cmd.sound:
                line += f" {cmd.sound}"
            if cmd.tics is not None:
                line += f" {cmd.tics}"
            parts.append(line)
        parts.append("  end")
        parts.append("")
    return "\n".join(parts)


class SndSeqLump(BaseLump[Any]):
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

    def get_sequence(self, name: str) -> SndSeq | None:
        """Return the sequence with the given name (case-insensitive), or None."""
        return next((s for s in self.sequences if s.name.lower() == name.lower()), None)
