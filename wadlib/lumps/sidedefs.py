from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

SIDEDEF_FORMAT = "<hh8s8s8sH"


def _encode_texture(name: str) -> bytes:
    """Encode a texture name to 8-byte null-padded ASCII."""
    return name.encode("latin-1")[:8].ljust(8, b"\x00")


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
            self.upper_texture = self.upper_texture.decode("latin-1").rstrip("\x00")
        if isinstance(self.lower_texture, bytes):
            self.lower_texture = self.lower_texture.decode("latin-1").rstrip("\x00")
        if isinstance(self.middle_texture, bytes):
            self.middle_texture = self.middle_texture.decode("latin-1").rstrip("\x00")

    def to_bytes(self) -> bytes:
        return pack(
            SIDEDEF_FORMAT,
            self.x_offset,
            self.y_offset,
            _encode_texture(self.upper_texture),
            _encode_texture(self.lower_texture),
            _encode_texture(self.middle_texture),
            self.sector,
        )


class SideDefs(BaseLump[SideDef]):
    _row_format: ClassVar[str] = SIDEDEF_FORMAT
    _row_item: ClassVar[type[SideDef]] = SideDef
