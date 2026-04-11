from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

VERTEX_FORMAT = "<hh"


@dataclass
class Vertex:
    x: int
    y: int

    def to_bytes(self) -> bytes:
        return pack(VERTEX_FORMAT, self.x, self.y)


class Vertices(BaseLump[Vertex]):
    _row_format: ClassVar[str] = VERTEX_FORMAT
    _row_item: ClassVar[type[Vertex]] = Vertex
