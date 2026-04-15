from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wad import WadFile


class DirectoryEntry:
    def __init__(self, owner: WadFile, offset: int, size: int, name: bytes | str) -> None:
        from .exceptions import InvalidDirectoryError

        self.owner = owner
        if isinstance(name, bytes):
            if not name.rstrip(b"\0").isascii():
                raise InvalidDirectoryError(f"Non-ASCII bytes in lump name: {name!r}")
            self.name = name.decode("ascii").rstrip("\0")
        else:
            self.name = name
        self.size = size
        self.offset = offset

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} "{self.name}" / {self.size}>'
