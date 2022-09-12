from .base import BaseLump
from ..constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX


class BaseMapEntry(BaseLump):
    _regex = None

    def __init__(self, entry):
        super().__init__(entry)
        self._match = self._regex.match(self.name)
        self._things = None

    @property
    def number(self):
        return self._match.group("number").lstrip("0")

    @property
    def things(self):
        if not self._things:
            raise
        return self._things.data

    def attach(self, lump: BaseLump):
        pass

    def attach_things(self, things):
        self._things = things


class Doom1MapEntry(BaseMapEntry):
    _regex = DOOM1_MAP_NAME_REGEX

    @property
    def episode(self):
        return self._match.group("episode")

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
