from dataclasses import dataclass
from enum import IntFlag
from functools import cached_property
from struct import calcsize, unpack

from .base import BaseLump

DOOM_FORMAT = "<hhHHH"
HEXEN_FORMAT = "<HhhhHHHbbbbb"  # How to understand that we are reading Hexen Wad?


class DoomFlags(IntFlag):
    SKILL_1_2 = 0x0001
    SKILL_3 = 0x0002
    SKILL_4_5 = 0x0004
    DEAF = 0x0008
    NOT_SINGLEPLAYER = 0x0010
    NOT_DEATHMATCH = 0x0020  # Boom
    NOT_COOP = 0x0040  # Boom
    FRIENDLY = 0x0080  # MBF


@dataclass
class DoomThing:
    x: int
    y: int
    direction: int
    type: int
    flags: DoomFlags


class Things(BaseLump):
    @cached_property
    def data(self):
        chunk_size = calcsize(DOOM_FORMAT)
        for _ in range(self._size // chunk_size):
            data = unpack(DOOM_FORMAT, self.read(chunk_size))
            thing = DoomThing(*data)
            yield thing
