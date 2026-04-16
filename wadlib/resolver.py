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

    # Iterate all unique resources (highest-priority wins per name):
    for ref in resolver.iter_resources():
        print(ref.name, ref.kind, ref.namespace, ref.size)

    # Inspect shadowed / colliding resources:
    hidden = resolver.shadowed("PLAYPAL")    # refs behind the winner
    clashes = resolver.collisions()          # dict[name, list[ResourceRef]]
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from .pk3 import Pk3Archive
from .source import LumpSource, MemoryLumpSource
from .wad import WadFile

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry

# Lump names that are map-local sub-lumps, scoped under a map marker (e.g.
# MAP01, E1M1).  These names appear once per map in multi-map WADs and must
# NOT be treated as global resource collisions by collisions().
_MAP_SUB_LUMPS: frozenset[str] = frozenset(
    {
        "THINGS",
        "VERTEXES",
        "LINEDEFS",
        "SIDEDEFS",
        "SECTORS",
        "SEGS",
        "SSECTORS",
        "NODES",
        "REJECT",
        "BLOCKMAP",
        "ZNODES",
        "BEHAVIOR",
        "TEXTMAP",
        "SCRIPTS",
        "ENDMAP",
    }
)


@dataclass(frozen=True)
class ResourceRef:
    """A resource hit returned by :meth:`ResourceResolver.find_all` and friends.

    Attributes:
        name:             Canonical lump name (uppercase, at most 8 characters).
        archive:          The ``WadFile`` or ``Pk3Archive`` that contains this
                          resource.
        source:           A ``LumpSource`` whose :meth:`~LumpSource.read_bytes`
                          returns the raw bytes for the resource.
        size:             Byte size of this resource (same as ``source.size``).
        kind:             How the resource was located:

                          ``"wad-name"``
                              Found by matching an 8-character WAD directory
                              entry name.

                          ``"pk3-lump-name"``
                              Found by matching a PK3 filename (without
                              extension, uppercased, truncated to 8 chars)
                              against the requested name.  This lookup is
                              *lossy* when multiple files in the archive map
                              to the same truncated name.

        namespace:        For PK3 resources this is the top-level directory
                          category (``"flats"``, ``"sprites"``, ``"sounds"``,
                          etc.).  For WAD resources this is always ``""``
                          (WAD directory entries carry no namespace metadata).
        load_order_index: Zero-based position of :attr:`archive` in the
                          resolver's source list.  Lower index = higher
                          priority.
    """

    name: str
    archive: WadFile | Pk3Archive
    source: LumpSource
    size: int
    kind: Literal["wad-name", "pk3-lump-name"]
    namespace: str
    load_order_index: int
    origin_path: str | None = field(default=None)
    """Full path inside the PK3 archive, or ``None`` for WAD entries."""
    directory_index: int | None = field(default=None)
    """Zero-based index of this entry in its WAD's directory, or ``None`` for PK3 entries."""

    def read_bytes(self) -> bytes:
        """Return the raw bytes for this resource."""
        return self.source.read_bytes()

    @property
    def origin(self) -> str:
        """Human-readable origin identifier suitable for diagnostics.

        For PK3 resources this is the full path inside the archive
        (e.g. ``"sprites/POSSA1.png"``).  For WAD resources this is
        the directory index formatted as ``"directory[N]"``.  Returns
        ``""`` when neither field is populated.
        """
        if self.origin_path is not None:
            return self.origin_path
        if self.directory_index is not None:
            return f"directory[{self.directory_index}]"
        return ""


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
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_source(self, name_upper: str) -> Iterator[ResourceRef]:
        """Yield a :class:`ResourceRef` for every hit across all sources.

        For WAD sources every duplicate entry (same lump name appearing more
        than once in the directory) is yielded individually, highest priority
        first, via :meth:`WadFile.find_lumps`.  For pk3 sources every
        colliding entry (multiple files that map to the same 8-char lump name)
        is yielded via :meth:`Pk3Archive.find_resources`.
        """
        for load_order_index, src in enumerate(self._sources):
            if isinstance(src, WadFile):
                for entry in src.find_lumps(name_upper):
                    # Locate the directory index by identity comparison (DirectoryEntry
                    # has no __eq__, so == would fall back to identity anyway, but being
                    # explicit avoids subtle bugs if that ever changes).
                    dir_index: int | None = None
                    for wad in src.all_wads:
                        for idx, d in enumerate(wad.directory):
                            if d is entry:
                                dir_index = idx
                                break
                        if dir_index is not None:
                            break
                    yield ResourceRef(
                        name=name_upper,
                        archive=src,
                        source=entry,
                        size=entry.size,
                        kind="wad-name",
                        namespace="",
                        load_order_index=load_order_index,
                        origin_path=None,
                        directory_index=dir_index,
                    )
            else:
                for pk3_entry in src.find_resources(name_upper):
                    lump_src: LumpSource = MemoryLumpSource(
                        pk3_entry.lump_name, src.read(pk3_entry.path)
                    )
                    yield ResourceRef(
                        name=name_upper,
                        archive=src,
                        source=lump_src,
                        size=pk3_entry.size,
                        kind="pk3-lump-name",
                        namespace=pk3_entry.category,
                        load_order_index=load_order_index,
                        origin_path=pk3_entry.path,
                        directory_index=None,
                    )

    # ------------------------------------------------------------------
    # Core lookup API
    # ------------------------------------------------------------------

    def find_source(self, name: str) -> LumpSource | None:
        """Return a ``LumpSource`` for the first matching resource, or ``None``."""
        for ref in self._iter_source(name.upper()):
            return ref.source
        return None

    def find_all(self, name: str) -> list[ResourceRef]:
        """Return all matching resources across every source, highest priority first.

        Callers can use this to inspect resources that are shadowed by a
        higher-priority source::

            refs = resolver.find_all("PLAYPAL")
            for ref in refs:
                print(ref.archive, ref.kind, ref.read_bytes()[:4])
        """
        return list(self._iter_source(name.upper()))

    def read(self, name: str) -> bytes | None:
        """Return raw bytes for the first matching resource, or ``None``."""
        source = self.find_source(name)
        return source.read_bytes() if source is not None else None

    def shadowed(self, name: str) -> list[ResourceRef]:
        """Return resources with this name that are hidden by a higher-priority hit.

        The first element of :meth:`find_all` wins; everything after it is
        *shadowed*.  An empty list means no shadowing (zero or one match)::

            hidden = resolver.shadowed("PLAYPAL")
            if hidden:
                print(f"PLAYPAL is overridden in {hidden[0].archive}")
        """
        return self.find_all(name)[1:]

    # ------------------------------------------------------------------
    # Iteration and collision inspection
    # ------------------------------------------------------------------

    def iter_resources(self, category: str | None = None) -> Iterator[ResourceRef]:
        """Iterate all unique resources across every source, highest priority first.

        For each resource name, only the highest-priority match is yielded;
        shadowed duplicates are skipped.  Sources are visited in priority order,
        so the first occurrence of a name wins.

        Args:
            category: Optional PK3 category filter (e.g. ``"flats"``,
                      ``"sprites"``, ``"sounds"``).  When given, only resources
                      whose :attr:`~ResourceRef.namespace` equals *category* are
                      yielded.  Pass ``None`` (default) to iterate everything.

                      .. note::

                          WAD directory entries carry no namespace metadata —
                          their :attr:`~ResourceRef.namespace` is always ``""``.
                          Filtering by a non-empty *category* therefore returns
                          only PK3 resources.

        Yields:
            :class:`ResourceRef` — one per unique resource name.
        """
        seen: set[str] = set()
        for load_order_index, src in enumerate(self._sources):
            if isinstance(src, WadFile):
                for wad in src.all_wads:  # PWADs first (higher priority)
                    for dir_index, entry in reversed(list(enumerate(wad.directory))):
                        upper = entry.name.upper()
                        if upper in seen:
                            continue
                        if category is not None and category != "":
                            continue  # WAD entries have no category
                        seen.add(upper)
                        yield ResourceRef(
                            name=upper,
                            archive=src,
                            source=entry,
                            size=entry.size,
                            kind="wad-name",
                            namespace="",
                            load_order_index=load_order_index,
                            directory_index=dir_index,
                        )
            else:
                for pk3_entry in src.infolist():
                    upper = pk3_entry.lump_name
                    if upper in seen:
                        continue
                    if category is not None and category != pk3_entry.category:
                        continue
                    seen.add(upper)
                    lump_src: LumpSource = MemoryLumpSource(upper, src.read(pk3_entry.path))
                    yield ResourceRef(
                        name=upper,
                        archive=src,
                        source=lump_src,
                        size=pk3_entry.size,
                        kind="pk3-lump-name",
                        namespace=pk3_entry.category,
                        load_order_index=load_order_index,
                        origin_path=pk3_entry.path,
                    )

    def collisions(self) -> dict[str, list[ResourceRef]]:
        """Return all resource names that have more than one match.

        A *collision* occurs when:

        - The same lump name appears more than once across different sources
          (cross-source shadowing), or
        - The same lump name appears more than once within a single WAD's
          directory (intra-WAD duplicates), or
        - Multiple PK3 files map to the same 8-char lump name after truncation.

        Returns:
            A ``dict`` mapping each colliding name to the full
            :meth:`find_all` result for that name (highest-priority first).
            Names with exactly one match are not included.

        Example::

            clashes = resolver.collisions()
            for name, refs in clashes.items():
                winner, *losers = refs
                print(f"{name}: {winner.archive} wins; {len(losers)} shadowed")
        """
        # Count name occurrences cheaply (no byte reads).
        name_counts: dict[str, int] = defaultdict(int)
        for src in self._sources:
            if isinstance(src, WadFile):
                for wad in src.all_wads:
                    for entry in wad.directory:
                        name_counts[entry.name.upper()] += 1
            else:
                for pk3_entry in src.infolist():
                    name_counts[pk3_entry.lump_name] += 1

        # Only fetch refs (which reads bytes) for actually-colliding names.
        # Map-local lump names (THINGS, LINEDEFS, etc.) appear once per map in
        # multi-map WADs but are scoped under map markers — they are NOT global
        # resource collisions and must be excluded from this report.
        return {
            name: self.find_all(name)
            for name, count in name_counts.items()
            if count > 1 and name not in _MAP_SUB_LUMPS
        }

    # ------------------------------------------------------------------
    # Map assembly
    # ------------------------------------------------------------------

    def maps(self) -> dict[str, BaseMapEntry]:
        """Return all assembled maps across every source, highest priority wins.

        Maps are collected from all sources (WAD files and PK3 archives) and
        merged so the highest-priority source's version of each map name wins,
        matching Doom load-order semantics.

        The :attr:`~wadlib.lumps.map.BaseMapEntry.origin` attribute of each
        returned map records the file that contributed it.  For WAD sources
        this is the WAD's filename; for PK3 sources it is the path within the
        archive (e.g. ``"mod.pk3/maps/MAP01.wad"`` or
        ``"mod.pk3/maps/MAP01/"``).

        Returns:
            A ``dict`` mapping each map name (``"E1M1"``, ``"MAP01"``, etc.)
            to its assembled :class:`~wadlib.lumps.map.BaseMapEntry`.
        """
        from .lumps.map import BaseMapEntry as _BaseMapEntry
        from .registry import assemble_maps

        result: dict[str, _BaseMapEntry] = {}

        # Process sources lowest-priority first so higher-priority sources
        # overwrite.  In ResourceResolver, sources[0] is highest priority, so
        # we iterate in reverse.
        for src in reversed(self._sources):
            if isinstance(src, WadFile):
                seen, _ = assemble_maps([w.directory for w in reversed(src.all_wads)])
                wad_name: str = getattr(src.fd, "name", repr(src))
                for name, map_entry in seen.items():
                    map_entry.origin = wad_name
                    result[name] = map_entry
            else:
                for name, map_entry in src.maps.items():
                    result[name] = map_entry

        return result

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
