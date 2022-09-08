from functools import cached_property

from .constants import DOOM1_MAP_NAME_REGEX
from .directory import DirectoryEntry


class MapEntry(DirectoryEntry):
    def __init__(self, owner, offset, size, name):
        super().__init__(owner, offset, size, name)

        self.things = None
        self.lines = None
        self.sides = None
        self.segments = None
        self.subsectors = None
        self.nodes = None
        self.sectors = None
        self.reject = None
        self.blockmap = None
        self.behavior = None

    @cached_property
    def map(self):
        if match := DOOM1_MAP_NAME_REGEX.match(self.name):
            return match.group("map")
        if match := DOOM1_MAP_NAME_REGEX.match(self.name):
            return match.group("map")
        return None

    @cached_property
    def episode(self):
        if match := DOOM1_MAP_NAME_REGEX.match(self.name):
            return match.group("episode")
        return None

    @classmethod
    def from_directory(cls, entry):
        return cls(entry.owner, entry.offset, entry.size, entry.name)

    def attach(self, lump):
        pass
