from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from re import Pattern
from typing import TYPE_CHECKING, Any, ClassVar

from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
from .base import BaseLump

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

        self.things: Any = None
        self.vertices: Any = None
        self.lines: Any = None
        self.sidedefs: Any = None
        self.sectors: Any = None
        self.segs: Any = None
        self.ssectors: Any = None

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self.name}>'

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

    def attach(self, lump: Any) -> None:
        pass

    def attach_things(self, things: Any) -> None:
        self.things = things

    def attach_vertexes(self, vertices: Any) -> None:
        self.vertices = vertices

    def attach_linedefs(self, lines: Any) -> None:
        self.lines = lines

    def attach_sidedefs(self, sidedefs: Any) -> None:
        self.sidedefs = sidedefs

    def attach_sectors(self, sectors: Any) -> None:
        self.sectors = sectors

    def attach_segs(self, segs: Any) -> None:
        self.segs = segs

    def attach_ssectors(self, ssectors: Any) -> None:
        self.ssectors = ssectors


class Doom1MapEntry(BaseMapEntry):
    _regex = DOOM1_MAP_NAME_REGEX

    @property
    def episode(self) -> int:
        assert self._match is not None
        return int(self._match.group("episode"))

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} Episode {self.episode} Map {self.number}>'


class Doom2MapEntry(BaseMapEntry):
    _regex = DOOM2_MAP_NAME_REGEX

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} Map {self.number}>'


def MapEntry(entry: DirectoryEntry) -> BaseMapEntry:  # pylint: disable=invalid-name
    if DOOM1_MAP_NAME_REGEX.match(entry.name):
        return Doom1MapEntry(entry)

    if DOOM2_MAP_NAME_REGEX.match(entry.name):
        return Doom2MapEntry(entry)

    raise ValueError(f"Unknown map name format: {entry.name!r}")
