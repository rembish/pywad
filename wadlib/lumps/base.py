from collections.abc import Iterator
from functools import cached_property
from io import SEEK_CUR, SEEK_END, SEEK_SET, BytesIO
from struct import calcsize, unpack
from typing import Any, ClassVar, cast, overload

from ..source import LumpSource


class BaseLump[T]:
    """Base class for all WAD lump types.

    Each instance buffers its raw bytes from the WAD file descriptor on
    construction, making it completely independent of the shared fd
    afterwards.  This means concurrent iteration over multiple lumps
    from the same WAD is safe.

    The type parameter *T* is the row item type returned by ``read_item``
    and ``get``.  Concrete subclasses fix it via ``_row_item``.
    """

    _row_format: ClassVar[str | None] = None
    _row_item: ClassVar[type[Any] | None] = None

    def __init__(self, entry: LumpSource) -> None:
        self._name = entry.name
        self._size: int | None = entry.size or None
        self._rposition: int | None = 0 if self._size else None

        if self._size:
            self._buf: BytesIO | None = BytesIO(entry.read_bytes())
        else:
            self._buf = None

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
        return f"<{self.__class__.__name__}[{len(self) or 'n/a'}]>"

    def __iter__(self) -> Iterator[T]:
        self.seek(0)
        return self

    def __next__(self) -> T:
        if not self.readable():
            raise StopIteration
        assert self._rposition is not None
        assert self._size is not None
        if self._rposition >= self._size:
            raise StopIteration
        return self.read_item()

    @property
    def byte_size(self) -> int:
        """Raw byte size of the lump data, independent of domain semantics.

        Use this when you need the actual number of bytes on disk.  ``len()``
        returns a domain-specific count (row count for binary lumps, page count
        for ``ConversationLump``, etc.) which is not the same thing.
        """
        return self._size or 0

    def __bool__(self) -> bool:
        """Return ``True`` if this lump contains any data."""
        return self._size is not None and self._size > 0

    def __len__(self) -> int:
        if not self.readable():
            return 0
        if self._row_format is None:
            # Non-row lumps (e.g. UdmfLump, text lumps) have no fixed row size.
            # Return the raw byte count so len() is at least safe to call.
            assert self._size is not None
            return self._size
        assert self._size is not None
        return self._size // self._row_size

    def __getitem__(self, index: int) -> T:
        return self.read_item(index)

    def seek(self, offset: int, whence: int = SEEK_SET) -> int | None:
        if not self.seekable():
            return None

        assert self._rposition is not None
        assert self._size is not None

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
            # Offset is expected to be negative
            self._rposition = self._size + min(offset, self._size)
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
        assert self._buf is not None

        if size == 0:
            return b""

        if self._rposition >= self._size:
            raise EOFError()

        if size is None or size == -1:  # Standard .read compatibility
            size = self._size - self._rposition
        self._buf.seek(self._rposition)
        data = self._buf.read(size)
        self._rposition += len(data)
        return data

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

    def read_item(self, index: int | None = None) -> T:
        if not self.readable():
            return None  # type: ignore[return-value]

        assert self._row_item is not None
        row = self.read_row(index)
        assert row is not None
        return cast(T, self._row_item(*row))  # pylint: disable=not-callable

    def raw(self) -> bytes:
        """Return the entire lump as raw bytes."""
        if self._buf is None:
            return b""
        self._buf.seek(0)
        return self._buf.read()

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return self._rposition is not None

    def readable(self) -> bool:
        return self._rposition is not None

    @overload
    def get(self, index: int) -> T | None: ...
    @overload
    def get(self, index: int, default: T) -> T: ...
    @overload
    def get(self, index: int, default: None) -> T | None: ...

    def get(self, index: int, default: T | None = None) -> T | None:
        if 0 <= index < len(self):
            return self[index]
        return default
