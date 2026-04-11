from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

SEG_FORMAT = "<HHHHHh"
SSECTOR_FORMAT = "<HH"


@dataclass
class Seg:
    start_vertex: int
    end_vertex: int
    angle: int  # binary angle (0-65535 maps to 0-360 degrees)
    linedef: int
    direction: int  # 0 = same as linedef, 1 = opposite
    offset: int  # distance along linedef to start of seg

    def to_bytes(self) -> bytes:
        return pack(
            SEG_FORMAT,
            self.start_vertex,
            self.end_vertex,
            self.angle,
            self.linedef,
            self.direction,
            self.offset,
        )


@dataclass
class SubSector:
    seg_count: int
    first_seg: int  # index into SEGS

    def to_bytes(self) -> bytes:
        return pack(SSECTOR_FORMAT, self.seg_count, self.first_seg)


class Segs(BaseLump[Seg]):
    _row_format: ClassVar[str] = SEG_FORMAT
    _row_item: ClassVar[type[Seg]] = Seg


class SubSectors(BaseLump[SubSector]):
    _row_format: ClassVar[str] = SSECTOR_FORMAT
    _row_item: ClassVar[type[SubSector]] = SubSector
