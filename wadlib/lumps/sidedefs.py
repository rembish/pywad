from dataclasses import dataclass
from typing import ClassVar

from .base import BaseLump

SIDEDEF_FORMAT = "<hh8s8s8sH"


@dataclass
class SideDef:
    x_offset: int
    y_offset: int
    upper_texture: str
    lower_texture: str
    middle_texture: str
    sector: int

    def __post_init__(self) -> None:
        if isinstance(self.upper_texture, bytes):
            self.upper_texture = self.upper_texture.decode("ascii").rstrip("\x00")
        if isinstance(self.lower_texture, bytes):
            self.lower_texture = self.lower_texture.decode("ascii").rstrip("\x00")
        if isinstance(self.middle_texture, bytes):
            self.middle_texture = self.middle_texture.decode("ascii").rstrip("\x00")


class SideDefs(BaseLump[SideDef]):
    _row_format: ClassVar[str] = SIDEDEF_FORMAT
    _row_item: ClassVar[type[SideDef]] = SideDef
