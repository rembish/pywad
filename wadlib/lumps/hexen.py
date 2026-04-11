"""Hexen-format lump parsers.

Hexen (and Heretic with BEHAVIOR) uses extended THINGS (20 bytes) and
LINEDEFS (16 bytes) compared to Doom's 10 and 14-byte versions.

Detection: a BEHAVIOR lump in the same map block signals Hexen format.
"""

from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump
from .things import Flags

HEXEN_THING_FORMAT = "<hhhhHHHBBBBBB"
HEXEN_LINEDEF_FORMAT = "<HHHBBBBBBhh"


@dataclass
class HexenThing:
    tid: int  # thing id (for ACS scripts)
    x: int
    y: int
    z: int  # height offset above floor
    angle: int
    type: int
    flags: Flags
    action: int  # special action number
    arg0: int
    arg1: int
    arg2: int
    arg3: int
    arg4: int

    def __post_init__(self) -> None:
        self.flags = Flags(self.flags)

    def to_bytes(self) -> bytes:
        return pack(
            HEXEN_THING_FORMAT,
            self.tid,
            self.x,
            self.y,
            self.z,
            self.angle,
            self.type,
            int(self.flags),
            self.action,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            self.arg4,
        )


@dataclass
class HexenLineDef:
    start_vertex: int
    finish_vertex: int
    flags: int
    special_type: int
    arg0: int
    arg1: int
    arg2: int
    arg3: int
    arg4: int
    right_sidedef: int
    left_sidedef: int

    def to_bytes(self) -> bytes:
        return pack(
            HEXEN_LINEDEF_FORMAT,
            self.start_vertex,
            self.finish_vertex,
            self.flags,
            self.special_type,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
            self.arg4,
            self.right_sidedef,
            self.left_sidedef,
        )


class HexenThings(BaseLump[HexenThing]):
    _row_format: ClassVar[str] = HEXEN_THING_FORMAT
    _row_item: ClassVar[type[HexenThing]] = HexenThing


class HexenLineDefs(BaseLump[HexenLineDef]):
    _row_format: ClassVar[str] = HEXEN_LINEDEF_FORMAT
    _row_item: ClassVar[type[HexenLineDef]] = HexenLineDef
