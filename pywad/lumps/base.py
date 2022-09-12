from io import SEEK_SET, SEEK_CUR, SEEK_END

from ..directory import DirectoryEntry


class BaseLump:
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    def seek(self, offset, whence=SEEK_SET):
        if not self.seekable():
            return None

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

    def read(self, size=-1):
        if not self.readable():
            return None

        self.owner.fd.seek(self._offset + self._rposition, SEEK_SET)
        if size == -1:
            size = self._size - self._rposition
        self._rposition += size
        return self.owner.fd.read(size)

    def writable(self):
        return False

    def seekable(self):
        return self._rposition is not None

    def readable(self):
        return self._rposition is not None
