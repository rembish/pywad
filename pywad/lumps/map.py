from .base import BaseLump
from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX


class BaseMapEntry(BaseLump):
    _regex = None

    def __init__(self, entry):
        super().__init__(entry)
        self._match = self._regex.match(self.name)

        self.things = None
        self.vertices = None

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}>'

    @property
    def number(self):
        return int(self._match.group("number").lstrip("0"))

    def attach(self, lump: BaseLump):
        pass

    def attach_things(self, things):
        self.things = things

    def attach_vertexes(self, vertices):
        self.vertices = vertices


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
