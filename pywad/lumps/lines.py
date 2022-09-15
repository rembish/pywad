from dataclasses import dataclass

from .base import BaseLump


@dataclass
class LineDefinition:
    start_vertex: int
    finish_vertex: int
    flags: int
    special_type: int
    sector_tag: int
    right_sidedef: int
    left_sidedef: int


class Lines(BaseLump):
    _row_format = "<HHHHHhh"
    _row_item = LineDefinition
