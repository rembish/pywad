from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wad import WadFile


class DirectoryEntry:
    def __init__(self, owner: WadFile, offset: int, size: int, name: bytes | str) -> None:
        self.owner = owner
        self.name = name.decode("ascii").rstrip("\0") if isinstance(name, bytes) else name
        self.size = size
        self.offset = offset

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} "{self.name}" / {self.size}>'
