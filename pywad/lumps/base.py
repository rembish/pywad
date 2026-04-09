from collections.abc import Iterator
from functools import cached_property
from io import SEEK_CUR, SEEK_END, SEEK_SET
from struct import calcsize, unpack
from typing import Any, ClassVar

from ..directory import DirectoryEntry


class BaseLump:
    _row_format: ClassVar[str | None] = None
    _row_item: ClassVar[type[Any] | None] = None

    def __init__(self, entry: DirectoryEntry) -> None:
        self.owner = entry.owner
        self._size: int | None = entry.size or None
        self._offset: int | None = entry.offset if self._size else None
        self._rposition: int | None = 0 if self._size else None
        self._name = entry.name

    @property
    def name(self) -> str:
        if self.compressed:
            return self._name[1:]
        return self._name

    @property
    def compressed(self) -> bool:
        return self._name[0] == chr(0x80)

    @cached_property
    def _row_size(self) -> int:
        assert self._row_format is not None
        return calcsize(self._row_format)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}[{len(self) or "n/a"}]>'

    def __iter__(self) -> Iterator[Any]:
        self.seek(0)
        return self

    def __next__(self) -> Any:
        if not self.readable():
            raise StopIteration
        assert self._rposition is not None
        assert self._size is not None
        if self._rposition > self._size:
            raise StopIteration
        return self.read_item()

    def __len__(self) -> int:
        if not self.readable():
            return 0
        assert self._size is not None
        return self._size // self._row_size

    def __getitem__(self, index: int) -> Any:
        return self.read_item(index)

    def seek(self, offset: int, whence: int = SEEK_SET) -> int | None:
        if not self.seekable():
            return None

        assert self._rposition is not None
        assert self._size is not None
        assert self._offset is not None

        if whence == SEEK_SET:
            self._rposition = min(offset, self._size)
        elif whence == SEEK_CUR:
            new_pos = self._rposition + offset
            if new_pos > self._size:
                self._rposition = self._size
            elif new_pos < 0:
                self._rposition = 0
            else:
                self._rposition = new_pos
        elif whence == SEEK_END:
            # Offset is negative
            self._rposition = self._size + min(offset, self._size)
        self.owner.fd.seek(self._offset + self._rposition, SEEK_SET)
        return self._rposition

    def tell(self) -> int | None:
        if not self.seekable():
            return None
        return self._rposition

    def read(self, size: int | None = None) -> bytes | None:
        if not self.readable():
            return None

        assert self._rposition is not None
        assert self._size is not None
        assert self._offset is not None

        if self._rposition > self._size:
            raise EOFError()

        self.owner.fd.seek(self._offset + self._rposition, SEEK_SET)
        if size is None or size == -1:  # Standard .read compatibility
            size = self._size - self._rposition
        self._rposition += size
        return self.owner.fd.read(size)

    def read_row(self, index: int | None = None) -> tuple[Any, ...] | None:
        if not self.readable():
            return None

        assert self._row_format is not None

        if index is not None:
            if index < 0 or index >= len(self):
                raise IndexError(index)
            self.seek(index * self._row_size)
        data = self.read(self._row_size)
        assert data is not None
        return unpack(self._row_format, data)

    def read_item(self, index: int | None = None) -> Any:
        if not self.readable():
            return None

        assert self._row_item is not None
        row = self.read_row(index)
        assert row is not None
        return self._row_item(*row)  # pylint: disable=not-callable

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return self._rposition is not None

    def readable(self) -> bool:
        return self._rposition is not None

    def get(self, index: int, default: Any = None) -> Any:
        if 0 <= index < len(self):
            return self[index]
        return default
