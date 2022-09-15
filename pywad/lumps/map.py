from dataclasses import dataclass
from functools import cached_property
from itertools import chain

from .base import BaseLump
from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX


@dataclass
class Point:
    x: int
    y: int


class BaseMapEntry(BaseLump):
    _regex = None

    def __init__(self, entry):
        super().__init__(entry)
        self._match = self._regex.match(self.name)

        self.things = None
        self.vertices = None
        self.lines = None

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    @property
    def number(self):
        return int(self._match.group("number").lstrip("0"))

    @cached_property
    def boundaries(self):
        min_x = max_x = self.things[0].x
        min_y = max_y = self.things[0].y

        for entry in chain(self.things, self.vertices):
            min_x, max_x = min(min_x, entry.x), max(max_x, entry.x)
            min_y, max_y = min(min_y, entry.y), max(max_y, entry.y)

        return tuple([Point(min_x, min_y), Point(max_x, max_y)])

    def attach(self, lump: BaseLump):
        pass

    def attach_things(self, things):
        self.things = things

    def attach_vertexes(self, vertices):
        self.vertices = vertices

    def attach_linedefs(self, lines):
        self.lines = lines


class Doom1MapEntry(BaseMapEntry):
    _regex = DOOM1_MAP_NAME_REGEX

    @property
    def episode(self):
        return int(self._match.group("episode"))

    def __repr__(self):
        return f'<{self.__class__.__name__} Episode {self.episode} Map {self.number}>'


class Doom2MapEntry(BaseMapEntry):
    _regex = DOOM2_MAP_NAME_REGEX

    def __repr__(self):
        return f'<{self.__class__.__name__} Map {self.number}>'


class MapEntry(BaseLump):
    def __new__(cls, entry):
        if DOOM1_MAP_NAME_REGEX.match(entry.name):
            return Doom1MapEntry(entry)

        if DOOM2_MAP_NAME_REGEX.match(entry.name):
            return Doom2MapEntry(entry)
