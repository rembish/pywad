from dataclasses import dataclass
from typing import ClassVar

from .base import BaseLump

SECTOR_FORMAT = "<hh8s8sHHH"


@dataclass
class Sector:
    floor_height: int
    ceiling_height: int
    floor_texture: str
    ceiling_texture: str
    light_level: int
    special: int
    tag: int

    def __post_init__(self) -> None:
        if isinstance(self.floor_texture, bytes):
            self.floor_texture = self.floor_texture.decode("ascii").rstrip("\x00")
        if isinstance(self.ceiling_texture, bytes):
            self.ceiling_texture = self.ceiling_texture.decode("ascii").rstrip("\x00")


class Sectors(BaseLump):
    _row_format: ClassVar[str] = SECTOR_FORMAT
    _row_item: ClassVar[type[Sector]] = Sector
