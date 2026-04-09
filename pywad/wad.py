from functools import cached_property
from io import SEEK_SET
from struct import calcsize, unpack
from typing import BinaryIO

from .constants import (
    DIRECTORY_ENTRY_FORMAT,
    DOOM1_MAP_NAME_REGEX,
    DOOM2_MAP_NAME_REGEX,
    HEADER_FORMAT,
)
from .directory import DirectoryEntry
from .enums import MapData, WadType
from .exceptions import BadHeaderWadException
from .lumps.lines import Lines
from .lumps.map import BaseMapEntry, MapEntry  # MapEntry is a factory function
from .lumps.sectors import Sectors
from .lumps.segs import Segs, SubSectors
from .lumps.sidedefs import SideDefs
from .lumps.things import Things
from .lumps.vertices import Vertices


class WadFile:
    fd: BinaryIO

    def __init__(self, filename: str) -> None:
        self.fd = open(filename, "rb")  # noqa: SIM115  # pylint: disable=consider-using-with

        magic_raw, self.directory_size, self._directory_offset = unpack(
            HEADER_FORMAT, self.fd.read(calcsize(HEADER_FORMAT))
        )
        magic = magic_raw.decode("ascii")
        if magic not in WadType.names():
            raise BadHeaderWadException(magic)

        self.wad_type = WadType[magic]

    def close(self) -> None:
        if not self.fd.closed:
            self.fd.close()

    def __enter__(self) -> "WadFile":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    @cached_property
    def directory(self) -> list[DirectoryEntry]:
        self.fd.seek(self._directory_offset, SEEK_SET)

        entries = []
        for _ in range(self.directory_size):
            lump = unpack(DIRECTORY_ENTRY_FORMAT, self.fd.read(calcsize(DIRECTORY_ENTRY_FORMAT)))
            entries.append(DirectoryEntry(self, *lump))
        return entries

    @cached_property
    def maps(self) -> list[BaseMapEntry]:
        mlist: list[BaseMapEntry] = []
        last: BaseMapEntry | None = None
        for entry in self.directory:
            if DOOM1_MAP_NAME_REGEX.match(entry.name) or DOOM2_MAP_NAME_REGEX.match(entry.name):
                last = MapEntry(entry)
                mlist.append(last)
            elif entry.name in MapData.names() and last is not None:
                if entry.name == "THINGS":
                    last.attach_things(Things(entry))
                elif entry.name == "VERTEXES":
                    last.attach_vertexes(Vertices(entry))
                elif entry.name == "LINEDEFS":
                    last.attach_linedefs(Lines(entry))
                elif entry.name == "SIDEDEFS":
                    last.attach_sidedefs(SideDefs(entry))
                elif entry.name == "SECTORS":
                    last.attach_sectors(Sectors(entry))
                elif entry.name == "SEGS":
                    last.attach_segs(Segs(entry))
                elif entry.name == "SSECTORS":
                    last.attach_ssectors(SubSectors(entry))
                else:
                    last.attach(entry)
        return mlist
