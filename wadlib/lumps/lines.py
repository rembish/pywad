from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

LINEDEF_FORMAT = "<HHHHHhh"


@dataclass
class LineDefinition:
    start_vertex: int
    finish_vertex: int
    flags: int
    special_type: int
    sector_tag: int
    right_sidedef: int
    left_sidedef: int

    def to_bytes(self) -> bytes:
        return pack(
            LINEDEF_FORMAT,
            self.start_vertex,
            self.finish_vertex,
            self.flags,
            self.special_type,
            self.sector_tag,
            self.right_sidedef,
            self.left_sidedef,
        )


class Lines(BaseLump[LineDefinition]):
    _row_format: ClassVar[str] = LINEDEF_FORMAT
    _row_item: ClassVar[type[LineDefinition]] = LineDefinition
