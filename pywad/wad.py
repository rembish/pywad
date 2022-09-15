from functools import cached_property
from io import SEEK_SET
from struct import unpack, calcsize

from .constants import HEADER_FORMAT, DIRECTORY_ENTRY_FORMAT, DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
from .directory import DirectoryEntry
from .enums import WadType, MapData
from .exceptions import BadHeaderWadException
from .lumps.lines import Lines
from .lumps.map import MapEntry
from .lumps.things import Things
from .lumps.vertices import Vertices


class WadFile:
    def __init__(self, filename):
        self.fd = open(filename, "rb")

        magic, self.directory_size, self._directory_offset = \
            unpack(HEADER_FORMAT, self.fd.read(calcsize(HEADER_FORMAT)))
        magic = magic.decode("ascii")
        if magic not in WadType.names():
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
        self.fd.seek(self._directory_offset, SEEK_SET)

        entries = []
        for _ in range(self.directory_size):
            lump = unpack(DIRECTORY_ENTRY_FORMAT, self.fd.read(calcsize(DIRECTORY_ENTRY_FORMAT)))
            entries.append(DirectoryEntry(self, *lump))
        return entries

    @cached_property
    def maps(self):
        mlist = []
        last = None
        for entry in self.directory:
            if DOOM1_MAP_NAME_REGEX.match(entry.name) or DOOM2_MAP_NAME_REGEX.match(entry.name):
                last = MapEntry(entry)
                mlist.append(last)
            elif entry.name in MapData.names():
                if entry.name == "THINGS":
                    last.attach_things(Things(entry))
                elif entry.name == "VERTEXES":
                    last.attach_vertexes(Vertices(entry))
                elif entry.name == "LINEDEFS":
                    last.attach_linedefs(Lines(entry))
                else:
                    last.attach(entry)
        return mlist
