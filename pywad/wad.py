from functools import cached_property
from io import SEEK_SET
from struct import unpack, calcsize

from .enums import WadType
from .exceptions import BadHeaderWadException


class DirectoryEntry:
    def __init__(self, owner, offset, size, name):
        self.owner = owner
        self.name = name.decode("ascii")
        self.size = size
        self.offset = offset

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}" / {self.size}>'


class WadFile:
    def __init__(self, filename):
        self.fd = open(filename, "rb")

        header_format = "<4sII"
        magic, self.directory_size, self._directory_offset = \
            unpack(header_format, self.fd.read(calcsize(header_format)))
        magic = magic.decode("ascii")
        if magic not in ("IWAD", "PWAD"):
            raise BadHeaderWadException(magic)

        self.wad_type = WadType[magic]

    def close(self):
        if not self.fd.closed:
            self.fd.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @cached_property
    def directory(self):
        lump_format = "<II8s"
        self.fd.seek(self._directory_offset, SEEK_SET)

        entries = []
        for i in range(self.directory_size):
            lump = unpack(lump_format, self.fd.read(calcsize(lump_format)))
            entries.append(DirectoryEntry(self, *lump))
        return entries
