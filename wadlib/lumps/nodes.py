from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

NODE_FORMAT = "<hhhhhhhhhhhhHH"

# High bit set on a child index means the child is a subsector, not another node.
SSECTOR_FLAG = 0x8000


@dataclass
class BBox:
    top: int
    bottom: int
    left: int
    right: int


@dataclass
class Node:
    # Partition line
    x: int
    y: int
    dx: int
    dy: int
    # Right child bounding box
    right_top: int
    right_bottom: int
    right_left: int
    right_right: int
    # Left child bounding box
    left_top: int
    left_bottom: int
    left_left: int
    left_right: int
    # Child indices (SSECTOR_FLAG set => subsector index, else node index)
    right_child: int
    left_child: int

    @property
    def right_bbox(self) -> BBox:
        return BBox(self.right_top, self.right_bottom, self.right_left, self.right_right)

    @property
    def left_bbox(self) -> BBox:
        return BBox(self.left_top, self.left_bottom, self.left_left, self.left_right)

    @property
    def right_is_subsector(self) -> bool:
        return bool(self.right_child & SSECTOR_FLAG)

    @property
    def left_is_subsector(self) -> bool:
        return bool(self.left_child & SSECTOR_FLAG)

    def to_bytes(self) -> bytes:
        return pack(
            NODE_FORMAT,
            self.x,
            self.y,
            self.dx,
            self.dy,
            self.right_top,
            self.right_bottom,
            self.right_left,
            self.right_right,
            self.left_top,
            self.left_bottom,
            self.left_left,
            self.left_right,
            self.right_child,
            self.left_child,
        )


class Nodes(BaseLump[Node]):
    _row_format: ClassVar[str] = NODE_FORMAT
    _row_item: ClassVar[type[Node]] = Node
