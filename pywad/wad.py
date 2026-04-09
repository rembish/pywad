from collections.abc import Callable
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
from .lumps.blockmap import BlockMap, Reject
from .lumps.lines import Lines
from .lumps.map import BaseMapEntry, MapEntry  # MapEntry is a factory function
from .lumps.nodes import Nodes
from .lumps.sectors import Sectors
from .lumps.segs import Segs, SubSectors
from .lumps.sidedefs import SideDefs
from .lumps.things import Things
from .lumps.vertices import Vertices

# Dispatch table: lump name -> attach method name + lump constructor
_LUMP_DISPATCH: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
    "THINGS": ("attach_things", Things),
    "VERTEXES": ("attach_vertexes", Vertices),
    "LINEDEFS": ("attach_linedefs", Lines),
    "SIDEDEFS": ("attach_sidedefs", SideDefs),
    "SECTORS": ("attach_sectors", Sectors),
    "SEGS": ("attach_segs", Segs),
    "SSECTORS": ("attach_ssectors", SubSectors),
    "NODES": ("attach_nodes", Nodes),
    "REJECT": ("attach_reject", Reject),
    "BLOCKMAP": ("attach_blockmap", BlockMap),
}


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
                dispatch = _LUMP_DISPATCH.get(entry.name)
                if dispatch:
                    method_name, constructor = dispatch
                    getattr(last, method_name)(constructor(entry))
                else:
                    last.attach(entry)
        return mlist
