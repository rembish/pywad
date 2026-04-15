"""ResourceResolver — unified resource lookup across WAD files and pk3 archives.

A single ``ResourceResolver`` instance can wrap any mix of ``WadFile`` and
``Pk3Archive`` objects.  Sources are searched in priority order (first wins).

Usage::

    from wadlib.resolver import ResourceResolver

    with WadFile("DOOM2.WAD") as wad, Pk3Archive("mod.pk3") as pk3:
        resolver = ResourceResolver(wad, pk3)
        data = resolver.read("PLAYPAL")       # bytes or None
        src  = resolver.find_source("D_E1M1") # LumpSource or None
"""

from __future__ import annotations

from .pk3 import Pk3Archive
from .source import LumpSource, MemoryLumpSource
from .wad import WadFile


class ResourceResolver:
    """Search one or more WAD / pk3 sources for a named resource.

    Sources are tried in the order they were passed to the constructor;
    the first hit wins.  ``WadFile`` entries are returned as
    ``DirectoryEntry`` objects (which implement ``LumpSource``), while
    ``Pk3Archive`` hits are wrapped in ``MemoryLumpSource`` so callers get
    the same ``LumpSource`` interface regardless of origin.
    """

    def __init__(self, *sources: WadFile | Pk3Archive) -> None:
        self._sources: list[WadFile | Pk3Archive] = list(sources)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def find_source(self, name: str) -> LumpSource | None:
        """Return a ``LumpSource`` for the first matching resource, or ``None``."""
        name_upper = name.upper()
        for src in self._sources:
            if isinstance(src, WadFile):
                entry = src.find_lump(name_upper)
                if entry is not None:
                    return entry
            else:
                pk3_entry = src.find_resource(name_upper)
                if pk3_entry is not None:
                    return MemoryLumpSource(pk3_entry.lump_name, src.read(pk3_entry.path))
        return None

    def read(self, name: str) -> bytes | None:
        """Return raw bytes for the first matching resource, or ``None``."""
        source = self.find_source(name)
        return source.read_bytes() if source is not None else None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        """Return ``True`` if any source contains a resource with this name."""
        return self.find_source(name) is not None

    def __len__(self) -> int:
        return len(self._sources)

    def __repr__(self) -> str:
        return f"<ResourceResolver sources={len(self._sources)}>"
