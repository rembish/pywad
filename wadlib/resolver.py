"""ResourceResolver — unified resource lookup across WAD files and pk3 archives.

A single ``ResourceResolver`` instance can wrap any mix of ``WadFile`` and
``Pk3Archive`` objects.  Sources are searched in priority order (first wins).

Usage::

    from wadlib.resolver import ResourceResolver

    # Priority order: wad wins over pk3 for the same name.
    with WadFile("DOOM2.WAD") as wad, Pk3Archive("mod.pk3") as pk3:
        resolver = ResourceResolver(wad, pk3)
        data = resolver.read("PLAYPAL")       # bytes or None
        src  = resolver.find_source("D_E1M1") # LumpSource or None

    # Doom load order: last argument (PWAD) overrides earlier ones.
    with WadFile("DOOM2.WAD") as base, WadFile("MOD.WAD") as mod:
        resolver = ResourceResolver.doom_load_order(base, mod)
        data = resolver.read("PLAYPAL")       # mod wins if it has PLAYPAL
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .pk3 import Pk3Archive
from .source import LumpSource, MemoryLumpSource
from .wad import WadFile


@dataclass(frozen=True)
class ResourceRef:
    """A resource hit returned by :meth:`ResourceResolver.find_all`.

    Attributes:
        name:    Canonical lump name (uppercase, at most 8 characters).
        archive: The ``WadFile`` or ``Pk3Archive`` that contains this resource.
        source:  A ``LumpSource`` whose :meth:`~LumpSource.read_bytes` returns
                 the raw bytes for the resource.
    """

    name: str
    archive: WadFile | Pk3Archive
    source: LumpSource

    def read_bytes(self) -> bytes | None:
        """Return the raw bytes for this resource."""
        return self.source.read_bytes()


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
    # Named constructors
    # ------------------------------------------------------------------

    @classmethod
    def doom_load_order(
        cls, base: WadFile | Pk3Archive, *patches: WadFile | Pk3Archive
    ) -> ResourceResolver:
        """Create a resolver that follows Doom WAD load order.

        In Doom, the base IWAD has the lowest priority and each successive PWAD
        overrides it.  This constructor translates that into ``ResourceResolver``
        priority order (first source wins) by reversing the caller's argument
        sequence::

            ResourceResolver.doom_load_order(base, patch1, patch2)
            # equivalent to: doom -iwad base -file patch1 patch2
            # patch2 wins over patch1 wins over base

        Args:
            base:    The base archive (lowest priority, e.g. the IWAD).
            patches: Zero or more patch archives in load order; the last
                     patch has the highest priority.
        """
        return cls(*reversed((base, *patches)))

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def _iter_source(self, name_upper: str) -> Iterator[tuple[WadFile | Pk3Archive, LumpSource]]:
        """Yield ``(archive, LumpSource)`` pairs for every hit across all sources.

        For WAD sources every duplicate entry (same lump name appearing more than
        once in the directory) is yielded individually, highest priority first,
        via :meth:`WadFile.find_lumps`.  For pk3 sources every colliding entry
        (multiple files that map to the same 8-char lump name) is yielded via
        :meth:`Pk3Archive.find_resources`.
        """
        for src in self._sources:
            if isinstance(src, WadFile):
                for entry in src.find_lumps(name_upper):
                    yield src, entry
            else:
                for pk3_entry in src.find_resources(name_upper):
                    lump_src: LumpSource = MemoryLumpSource(
                        pk3_entry.lump_name, src.read(pk3_entry.path)
                    )
                    yield src, lump_src

    def find_source(self, name: str) -> LumpSource | None:
        """Return a ``LumpSource`` for the first matching resource, or ``None``."""
        for _archive, lump_src in self._iter_source(name.upper()):
            return lump_src
        return None

    def find_all(self, name: str) -> list[ResourceRef]:
        """Return all matching resources across every source, highest priority first.

        Callers can use this to inspect resources that are shadowed by a
        higher-priority source::

            refs = resolver.find_all("PLAYPAL")
            for ref in refs:
                print(ref.archive, ref.read_bytes()[:4])
        """
        name_upper = name.upper()
        return [
            ResourceRef(name=name_upper, archive=archive, source=lump_src)
            for archive, lump_src in self._iter_source(name_upper)
        ]

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
