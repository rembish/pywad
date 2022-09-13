from dataclasses import dataclass

from .base import BaseLump


@dataclass
class Vertex:
    x: int
    y: int


class Vertices(BaseLump):
    _row_format = "<hh"
    _row_item = Vertex
