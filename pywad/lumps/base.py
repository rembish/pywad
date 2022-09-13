from functools import cached_property
from io import SEEK_SET, SEEK_CUR, SEEK_END
from struct import unpack, calcsize

from ..directory import DirectoryEntry


class BaseLump:
    _row_format = None
    _row_item = None

    def __init__(self, entry: DirectoryEntry):
        self.owner = entry.owner
        self._size = entry.size or None
        self._offset = entry.offset if self._size else None
        self._rposition = 0 if self._size else None

        self._name = entry.name

    @property
    def name(self):
        if self.compressed:
            return self._name[1:]
        return self._name

    @property
    def compressed(self):
        return self._name[0] == chr(0x80)

    @cached_property
    def _row_size(self):
        return calcsize(self._row_format)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__}[{len(self) or "n/a"}]>'

    def __iter__(self):
        self.seek(0)
        return self

    def __next__(self):
        if not self.readable():
            raise StopIteration
        if self._rposition > self._size:
            raise StopIteration
        return self.read_item()

    def __len__(self):
        if not self.readable():
            return 0
        return self._size // self._row_size

    def __getitem__(self, index):
        return self.read_item(index)

    def seek(self, offset, whence=SEEK_SET):
        if not self.seekable():
            return None

        # TODO Check .seek behaviors
        if whence == SEEK_SET:
            if offset > self._size:
                offset = self._size
            self._rposition = offset
        elif whence == SEEK_CUR:
            if self._rposition + offset > offset:
                self._rposition = self._size
            elif self._rposition + offset < 0:
                self._rposition = 0
        elif whence == SEEK_END:
            # Offset is negative
            if offset > self._size:
                offset = self._size
            self._rposition = self._size + offset
        self.owner.fd.seek(self._offset + self._rposition, SEEK_SET)
        return self._rposition

    def tell(self):
        if not self.seekable():
            return None
        return self._rposition

    def read(self, size=None):
        if not self.readable():
            return None

        if self._rposition > self._size:
            raise EOFError()

        self.owner.fd.seek(self._offset + self._rposition, SEEK_SET)
        if size is None or size == -1:  # Standard .read compatibility
            size = self._size - self._rposition
        self._rposition += size
        return self.owner.fd.read(size)

    def read_row(self, index=None):
        if not self.readable():
            return None

        if index is not None:
            if index < 0 or index >= len(self):
                raise IndexError(index)
            self.seek(index * self._row_size)
        return unpack(self._row_format, self.read(self._row_size))

    def read_item(self, index=None):
        if not self.readable():
            return None

        return self._row_item(*self.read_row(index))

    def writable(self):
        return False

    def seekable(self):
        return self._rposition is not None

    def readable(self):
        return self._rposition is not None

    def get(self, index, default=None):
        if 0 <= index < len(self):
            return self[index]
        return default
