from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from re import Pattern
from typing import Any, ClassVar

from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
from ..source import LumpSource
from .base import BaseLump
from .blockmap import BlockMap, Reject
from .hexen import HexenLineDefs, HexenThings
from .lines import Lines
from .nodes import Nodes
from .sectors import Sectors
from .segs import Segs, SubSectors
from .sidedefs import SideDefs
from .things import Things
from .udmf import UdmfLump
from .vertices import Vertices
from .znodes import ZNodesLump, ZNodList, ZNodNode, ZNodSeg, ZNodSubSector, ZNodVertex


@dataclass
class Point:
    """A 2-D map coordinate (in Doom map units)."""

    x: int
    y: int


class BaseMapEntry(BaseLump[Any]):
    """Abstract base for a single map assembled from its constituent sub-lumps.

    Concrete subclasses (``Doom1MapEntry``, ``Doom2MapEntry``) fix the name
    regex and provide format-specific properties such as ``episode``.  Sub-lumps
    (THINGS, VERTEXES, LINEDEFS, …) are attached after construction by the
    registry layer via ``attach_*`` methods.
    """

    _regex: ClassVar[Pattern[str]]

    def __init__(self, entry: LumpSource) -> None:
        super().__init__(entry)
        self._match = self._regex.match(self.name)

        self.things: Things | HexenThings | None = None
        self.vertices: Vertices | ZNodList[ZNodVertex] | None = None
        self.lines: Lines | HexenLineDefs | None = None
        self.sidedefs: SideDefs | None = None
        self.sectors: Sectors | None = None
        self.segs: Segs | ZNodList[ZNodSeg] | None = None
        self.ssectors: SubSectors | ZNodList[ZNodSubSector] | None = None
        self.nodes: Nodes | ZNodList[ZNodNode] | None = None
        self.reject: Reject | None = None
        self.blockmap: BlockMap | None = None
        self.behavior: object | None = None  # BehaviorLump if Hexen/ZDoom ACS
        self.udmf: UdmfLump | None = None  # TEXTMAP lump if UDMF format
        self.origin: str = ""  # source file/archive that contributed this map

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    @property
    def number(self) -> int:
        """The map number extracted from the lump name (e.g. ``1`` for ``MAP01`` or ``E1M1``)."""
        assert self._match is not None
        return int(self._match.group("number").lstrip("0"))

    @cached_property
    def boundaries(self) -> tuple[Point, Point]:
        """Bounding box of the map as ``(min_point, max_point)``.

        Computed from the union of thing positions and vertex positions.
        Returns ``((0, 0), (0, 0))`` if no geometry has been attached yet.
        """
        entries: list[Any] = list(chain(self.things or [], self.vertices or []))
        if not entries:
            return (Point(0, 0), Point(0, 0))

        min_x = max_x = entries[0].x
        min_y = max_y = entries[0].y

        for entry in entries[1:]:
            min_x, max_x = min(min_x, entry.x), max(max_x, entry.x)
            min_y, max_y = min(min_y, entry.y), max(max_y, entry.y)

        return (Point(min_x, min_y), Point(max_x, max_y))

    def attach(self, lump: object) -> None:
        """Dispatch a generic lump object to the appropriate ``attach_*`` method."""

    def attach_things(self, things: Things | HexenThings) -> None:
        """Attach the THINGS lump (actor placement data)."""
        self.things = things

    def attach_vertices(self, vertices: Vertices) -> None:
        """Attach the VERTEXES lump (map vertex positions)."""
        self.vertices = vertices

    def attach_linedefs(self, lines: Lines | HexenLineDefs) -> None:
        """Attach the LINEDEFS lump (wall/trigger line definitions)."""
        self.lines = lines

    def attach_sidedefs(self, sidedefs: SideDefs) -> None:
        """Attach the SIDEDEFS lump (texture assignments for each linedef face)."""
        self.sidedefs = sidedefs

    def attach_sectors(self, sectors: Sectors) -> None:
        """Attach the SECTORS lump (room/area definitions)."""
        self.sectors = sectors

    def attach_segs(self, segs: Segs) -> None:
        """Attach the SEGS lump (BSP-split line segments)."""
        self.segs = segs

    def attach_ssectors(self, ssectors: SubSectors) -> None:
        """Attach the SSECTORS lump (BSP leaf convex sub-sectors)."""
        self.ssectors = ssectors

    def attach_nodes(self, nodes: Nodes) -> None:
        """Attach the NODES lump (BSP tree nodes)."""
        self.nodes = nodes

    def attach_reject(self, reject: Reject) -> None:
        """Attach the REJECT lump (sector-to-sector visibility table)."""
        self.reject = reject

    def attach_blockmap(self, blockmap: BlockMap) -> None:
        """Attach the BLOCKMAP lump (spatial hash for collision detection)."""
        self.blockmap = blockmap

    def attach_behavior(self, behavior: object) -> None:
        """Attach the BEHAVIOR lump (compiled ACS bytecode for Hexen/ZDoom maps)."""
        self.behavior = behavior

    def attach_textmap(self, udmf: UdmfLump) -> None:
        """Attach the TEXTMAP lump (UDMF text-format map data)."""
        self.udmf = udmf

    def attach_znodes(self, znodes: ZNodesLump) -> None:
        """Replace vanilla BSP data with ZNOD/XNOD extended nodes.

        Merges any extra vertices produced by the ZDoom node builder onto the
        end of the map's existing vertex list, then replaces segs, ssectors,
        and nodes with the ZNOD equivalents so the renderer's BSP walk works
        unchanged.
        """
        p = znodes.parsed
        orig: list[ZNodVertex] = (
            [ZNodVertex(v.x, v.y) for v in self.vertices] if self.vertices else []
        )
        combined: list[ZNodVertex] = orig + list(p.extra_vertices)
        self.vertices = ZNodList(combined)
        self.segs = p.segs
        self.ssectors = p.subsectors
        self.nodes = p.nodes


class Doom1MapEntry(BaseMapEntry):
    """A Doom 1 / Ultimate Doom map identified by an ``ExMy`` lump name."""

    _regex = DOOM1_MAP_NAME_REGEX

    @property
    def episode(self) -> int:
        """The episode number extracted from the lump name (e.g. ``1`` for ``E1M3``)."""
        assert self._match is not None
        return int(self._match.group("episode"))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} Episode {self.episode} Map {self.number}>"


class Doom2MapEntry(BaseMapEntry):
    """A Doom 2 / Heretic / Hexen map identified by a ``MAPxx`` lump name."""

    _regex = DOOM2_MAP_NAME_REGEX

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} Map {self.number}>"


def MapEntry(entry: LumpSource) -> BaseMapEntry:  # pylint: disable=invalid-name
    """Construct the appropriate ``BaseMapEntry`` subclass for *entry*.

    Returns a ``Doom1MapEntry`` for ``ExMy`` names, a ``Doom2MapEntry`` for
    ``MAPxx`` names, or raises ``ValueError`` for unrecognised formats.
    """
    if DOOM1_MAP_NAME_REGEX.match(entry.name):
        return Doom1MapEntry(entry)

    if DOOM2_MAP_NAME_REGEX.match(entry.name):
        return Doom2MapEntry(entry)

    raise ValueError(f"Unknown map name format: {entry.name!r}")
