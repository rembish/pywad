"""SNDINFO lump parser — maps logical sound names to WAD lump names."""

from __future__ import annotations

from typing import Any

from .base import BaseLump


def serialize_sndinfo(sounds: dict[str, str]) -> str:
    """Serialize a sound mapping to SNDINFO text.

    Example::

        text = serialize_sndinfo({"weapons/pistol": "DSPISTOL", "doors/open": "DSDOROPN"})
    """
    return "\n".join(f"{name} {lump}" for name, lump in sounds.items()) + "\n"


class SndInfo(BaseLump[Any]):
    """SNDINFO lump: logical-name -> lump-name sound mapping."""

    @property
    def sounds(self) -> dict[str, str]:
        """Return mapping of logical sound name -> WAD lump name (uppercase)."""
        result: dict[str, str] = {}
        text = self.raw().decode("latin-1")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(";") or stripped.startswith("$"):
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                result[parts[0]] = parts[1].upper()
        return result
