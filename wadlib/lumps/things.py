from dataclasses import dataclass
from enum import IntFlag
from typing import ClassVar

from .base import BaseLump

DOOM_FORMAT = "<hhHHH"
# Hexen detection happens at map-assembly time in wad.py via BEHAVIOR lump presence.


class Flags(IntFlag):
    SKILL_1_2 = 0x0001
    SKILL_3 = 0x0002
    SKILL_4_5 = 0x0004
    DEAF = 0x0008
    NOT_SINGLEPLAYER = 0x0010
    NOT_DEATHMATCH = 0x0020  # Boom
    NOT_COOP = 0x0040  # Boom
    FRIENDLY = 0x0080  # MBF


@dataclass
class Thing:
    x: int
    y: int
    direction: int
    type: int
    flags: Flags

    def __post_init__(self) -> None:
        self.flags = Flags(self.flags)


class Things(BaseLump[Thing]):
    _row_format: ClassVar[str] = DOOM_FORMAT
    _row_item: ClassVar[type[Thing]] = Thing
