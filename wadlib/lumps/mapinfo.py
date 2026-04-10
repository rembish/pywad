"""MAPINFO lump parser (Hexen format)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from .base import BaseLump

_MAP_RE = re.compile(r'^map\s+(\d+)\s+"([^"]*)"', re.IGNORECASE)


@dataclass
class MapInfoEntry:
    map_num: int
    title: str
    warptrans: int | None = None
    next: int | None = None
    cluster: int | None = None
    sky1: str | None = None
    sky2: str | None = None
    cdtrack: int | None = None
    lightning: bool = False
    doublesky: bool = False
    fadetable: str | None = None


class MapInfoLump(BaseLump[Any]):
    """MAPINFO lump: per-map metadata for Hexen WADs."""

    @cached_property
    def maps(self) -> list[MapInfoEntry]:  # pylint: disable=too-many-branches
        """Return all map entries defined in MAPINFO."""
        entries: list[MapInfoEntry] = []
        current: MapInfoEntry | None = None

        text = self.raw().decode("latin-1")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(";"):
                continue

            m = _MAP_RE.match(stripped)
            if m:
                if current is not None:
                    entries.append(current)
                current = MapInfoEntry(map_num=int(m.group(1)), title=m.group(2))
                continue

            if current is None:
                # global directive — skip
                continue

            parts = stripped.split()
            key = parts[0].lower()

            if key == "warptrans" and len(parts) >= 2:
                current.warptrans = int(parts[1])
            elif key == "next" and len(parts) >= 2:
                current.next = int(parts[1])
            elif key == "cluster" and len(parts) >= 2:
                current.cluster = int(parts[1])
            elif key == "sky1" and len(parts) >= 2:
                current.sky1 = parts[1]
            elif key == "sky2" and len(parts) >= 2:
                current.sky2 = parts[1]
            elif key == "cdtrack" and len(parts) >= 2:
                current.cdtrack = int(parts[1])
            elif key == "lightning":
                current.lightning = True
            elif key == "doublesky":
                current.doublesky = True
            elif key == "fadetable" and len(parts) >= 2:
                current.fadetable = parts[1]

        if current is not None:
            entries.append(current)

        return entries

    def get(self, map_num: int) -> MapInfoEntry | None:  # type: ignore[override]  # pylint: disable=arguments-differ,arguments-renamed
        """Return the MapInfoEntry for the given map number, or None."""
        return next((m for m in self.maps if m.map_num == map_num), None)
