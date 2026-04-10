from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from re import Pattern
from typing import TYPE_CHECKING, ClassVar

from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
from .base import BaseLump
from .blockmap import BlockMap, Reject
from .hexen import HexenLineDefs, HexenThings
from .lines import Lines
from .nodes import Nodes
from .sectors import Sectors
from .segs import Segs, SubSectors
from .sidedefs import SideDefs
from .things import Things
from .vertices import Vertices
from .znodes import ZNodesLump, ZNodList, ZNodVertex

if TYPE_CHECKING:
    from ..directory import DirectoryEntry


@dataclass
class Point:
    x: int
    y: int


class BaseMapEntry(BaseLump):
    _regex: ClassVar[Pattern[str]]

    def __init__(self, entry: DirectoryEntry) -> None:
        super().__init__(entry)
        self._match = self._regex.match(self.name)

        self.things: Things | HexenThings | None = None
        self.vertices: Vertices | None = None
        self.lines: Lines | HexenLineDefs | None = None
        self.sidedefs: SideDefs | None = None
        self.sectors: Sectors | None = None
        self.segs: Segs | None = None
        self.ssectors: SubSectors | None = None
        self.nodes: Nodes | None = None
        self.reject: Reject | None = None
        self.blockmap: BlockMap | None = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    @property
    def number(self) -> int:
        assert self._match is not None
        return int(self._match.group("number").lstrip("0"))

    @cached_property
    def boundaries(self) -> tuple[Point, Point]:
        entries = list(chain(self.things or [], self.vertices or []))
        if not entries:
            return (Point(0, 0), Point(0, 0))

        min_x = max_x = entries[0].x
        min_y = max_y = entries[0].y

        for entry in entries[1:]:
            min_x, max_x = min(min_x, entry.x), max(max_x, entry.x)
            min_y, max_y = min(min_y, entry.y), max(max_y, entry.y)

        return (Point(min_x, min_y), Point(max_x, max_y))

    def attach(self, lump: object) -> None:
        pass

    def attach_things(self, things: Things | HexenThings) -> None:
        self.things = things

    def attach_vertexes(self, vertices: Vertices) -> None:
        self.vertices = vertices

    def attach_linedefs(self, lines: Lines | HexenLineDefs) -> None:
        self.lines = lines

    def attach_sidedefs(self, sidedefs: SideDefs) -> None:
        self.sidedefs = sidedefs

    def attach_sectors(self, sectors: Sectors) -> None:
        self.sectors = sectors

    def attach_segs(self, segs: Segs) -> None:
        self.segs = segs

    def attach_ssectors(self, ssectors: SubSectors) -> None:
        self.ssectors = ssectors

    def attach_nodes(self, nodes: Nodes) -> None:
        self.nodes = nodes

    def attach_reject(self, reject: Reject) -> None:
        self.reject = reject

    def attach_blockmap(self, blockmap: BlockMap) -> None:
        self.blockmap = blockmap

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
        self.vertices = ZNodList(combined)  # type: ignore[assignment]
        self.segs = p.segs  # type: ignore[assignment]
        self.ssectors = p.subsectors  # type: ignore[assignment]
        self.nodes = p.nodes  # type: ignore[assignment]


class Doom1MapEntry(BaseMapEntry):
    _regex = DOOM1_MAP_NAME_REGEX

    @property
    def episode(self) -> int:
        assert self._match is not None
        return int(self._match.group("episode"))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} Episode {self.episode} Map {self.number}>"


class Doom2MapEntry(BaseMapEntry):
    _regex = DOOM2_MAP_NAME_REGEX

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} Map {self.number}>"


def MapEntry(entry: DirectoryEntry) -> BaseMapEntry:  # pylint: disable=invalid-name
    if DOOM1_MAP_NAME_REGEX.match(entry.name):
        return Doom1MapEntry(entry)

    if DOOM2_MAP_NAME_REGEX.match(entry.name):
        return Doom2MapEntry(entry)

    raise ValueError(f"Unknown map name format: {entry.name!r}")
