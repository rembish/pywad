from dataclasses import dataclass
from struct import pack
from typing import TYPE_CHECKING, ClassVar

from .base import BaseLump

if TYPE_CHECKING:
    from .boom import GeneralizedLinedef

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

    @property
    def generalized(self) -> "GeneralizedLinedef | None":
        """Decode this linedef as a Boom generalized type, or return None.

        Returns a :class:`~wadlib.lumps.boom.GeneralizedLinedef` when
        ``special_type >= 0x2F80`` (Boom generalized range), otherwise ``None``.
        """
        from .boom import decode_generalized  # lazy — avoids circular import

        return decode_generalized(self.special_type)

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
