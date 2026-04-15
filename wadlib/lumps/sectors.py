from dataclasses import dataclass
from struct import pack
from typing import ClassVar

from .base import BaseLump

SECTOR_FORMAT = "<hh8s8sHHH"


def _encode_texture(name: str) -> bytes:
    """Encode a texture name to 8-byte null-padded ASCII."""
    return name.encode("ascii")[:8].ljust(8, b"\x00")


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

    @property
    def special_name(self) -> str:
        """Return a human-readable name for this sector's special effect.

        Covers standard Doom sector specials (0-17).  Returns a generic
        ``"Special <n>"`` string for unrecognised values.
        """
        from .boom import DOOM_SECTOR_SPECIALS  # lazy — avoids circular import

        return DOOM_SECTOR_SPECIALS.get(self.special, f"Special {self.special}")

    def to_bytes(self) -> bytes:
        return pack(
            SECTOR_FORMAT,
            self.floor_height,
            self.ceiling_height,
            _encode_texture(self.floor_texture),
            _encode_texture(self.ceiling_texture),
            self.light_level,
            self.special,
            self.tag,
        )


class Sectors(BaseLump[Sector]):
    _row_format: ClassVar[str] = SECTOR_FORMAT
    _row_item: ClassVar[type[Sector]] = Sector
