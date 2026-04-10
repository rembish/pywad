from dataclasses import dataclass
from typing import ClassVar

from .base import BaseLump


@dataclass
class Vertex:
    x: int
    y: int


class Vertices(BaseLump[Vertex]):
    _row_format: ClassVar[str] = "<hh"
    _row_item: ClassVar[type[Vertex]] = Vertex
