"""DEHACKED lump parser — full DeHackEd patch format.

Parses all standard block types plus BEX extensions.

Usage::

    from wadlib.lumps.dehacked import DehackedLump, DehackedThing, parse_dehacked
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any

from ..base import BaseLump
from .data import STOCK_SPRITE_NAMES as STOCK_SPRITE_NAMES
from .parser import parse_dehacked as parse_dehacked
from .types import (
    DehackedAmmo as DehackedAmmo,
)
from .types import (
    DehackedFrame as DehackedFrame,
)
from .types import (
    DehackedMisc as DehackedMisc,
)
from .types import (
    DehackedPatch as DehackedPatch,
)
from .types import (
    DehackedSound as DehackedSound,
)
from .types import (
    DehackedText as DehackedText,
)
from .types import (
    DehackedThing as DehackedThing,
)
from .types import (
    DehackedWeapon as DehackedWeapon,
)


class DehackedLump(BaseLump[Any]):
    """DEHACKED lump: DeHackEd patch embedded in a WAD."""

    @cached_property
    def _text(self) -> str:
        return self.raw().decode("latin-1")

    @cached_property
    def parsed(self) -> DehackedPatch:
        """Return the fully parsed DEHACKED patch."""
        return parse_dehacked(self._text)

    @cached_property
    def par_times(self) -> dict[str, int]:
        """Return PAR times keyed by map name."""
        return self.parsed.par_times

    @cached_property
    def doom_version(self) -> int | None:
        """Doom engine version targeted by this patch (e.g. ``19`` for v1.9), or ``None``."""
        return self.parsed.doom_version

    @cached_property
    def patch_format(self) -> int | None:
        """DeHackEd patch format version, or ``None`` if not declared in the patch."""
        return self.parsed.patch_format

    @cached_property
    def things(self) -> dict[int, DehackedThing]:
        """Return custom Thing type definitions keyed by DoomEd type ID."""
        return self.parsed.things


class DehackedFile(DehackedLump):
    """A standalone ``.deh`` file loaded from disk, reusing the ``DehackedLump`` API."""

    def __init__(self, path: str | Path) -> None:  # pylint: disable=super-init-not-called
        object.__init__(self)  # pylint: disable=non-parent-init-called
        self._deh_path = Path(path)

    @cached_property
    def _text(self) -> str:
        return self._deh_path.read_bytes().decode("latin-1")

    def raw(self) -> bytes:
        """Return the raw bytes of the ``.deh`` file."""
        return self._deh_path.read_bytes()
