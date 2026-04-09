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
from .lumps.animdefs import AnimDefsLump
from .lumps.base import BaseLump
from .lumps.blockmap import BlockMap, Reject
from .lumps.colormap import ColormapLump
from .lumps.endoom import Endoom
from .lumps.flat import Flat
from .lumps.hexen import HexenLineDefs, HexenThings
from .lumps.lines import Lines
from .lumps.map import BaseMapEntry, MapEntry  # MapEntry is a factory function
from .lumps.mapinfo import MapInfoLump
from .lumps.mus import _HEADER_SIZE as _MUS_MIN_SIZE
from .lumps.mus import _MUS_MAGIC, Mus
from .lumps.nodes import Nodes
from .lumps.picture import Picture
from .lumps.playpal import PlayPal
from .lumps.sectors import Sectors
from .lumps.segs import Segs, SubSectors
from .lumps.sidedefs import SideDefs
from .lumps.sndinfo import SndInfo
from .lumps.sound import DmxSound
from .lumps.textures import PNames, TextureList
from .lumps.things import Things
from .lumps.vertices import Vertices

# Doom-format lump dispatch: name -> (attach method, constructor)
_DOOM_DISPATCH: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
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

# Hexen overrides only differ for THINGS and LINEDEFS
_HEXEN_OVERRIDES: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
    "THINGS": ("attach_things", HexenThings),
    "LINEDEFS": ("attach_linedefs", HexenLineDefs),
}


def _attach_lumps(map_entry: BaseMapEntry, lumps: list[DirectoryEntry], hexen: bool) -> None:
    dispatch = dict(_DOOM_DISPATCH)
    if hexen:
        dispatch.update(_HEXEN_OVERRIDES)

    for entry in lumps:
        if entry.name not in MapData.names():
            continue
        action = dispatch.get(entry.name)
        if action:
            method_name, constructor = action
            getattr(map_entry, method_name)(constructor(entry))
        else:
            map_entry.attach(entry)


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
        # Group directory entries into per-map buckets so we can detect
        # BEHAVIOR (Hexen format marker) before parsing THINGS/LINEDEFS.
        groups: list[tuple[DirectoryEntry, list[DirectoryEntry]]] = []
        current_lumps: list[DirectoryEntry] = []
        marker: DirectoryEntry | None = None

        for entry in self.directory:
            is_marker = bool(
                DOOM1_MAP_NAME_REGEX.match(entry.name) or DOOM2_MAP_NAME_REGEX.match(entry.name)
            )
            if is_marker:
                if marker is not None:
                    groups.append((marker, current_lumps))
                marker = entry
                current_lumps = []
            elif marker is not None and entry.name in MapData.names():
                current_lumps.append(entry)

        if marker is not None:
            groups.append((marker, current_lumps))

        result: list[BaseMapEntry] = []
        for map_marker, lumps in groups:
            map_entry = MapEntry(map_marker)
            hexen = any(e.name == "BEHAVIOR" for e in lumps)
            _attach_lumps(map_entry, lumps, hexen)
            result.append(map_entry)

        return result

    @cached_property
    def playpal(self) -> PlayPal | None:
        """Return the PLAYPAL lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "PLAYPAL":
                return PlayPal(entry)
        return None

    @cached_property
    def colormap(self) -> ColormapLump | None:
        """Return the COLORMAP lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "COLORMAP":
                return ColormapLump(entry)
        return None

    @cached_property
    def pnames(self) -> PNames | None:
        """Return the PNAMES lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "PNAMES":
                return PNames(entry)
        return None

    @cached_property
    def texture1(self) -> TextureList | None:
        """Return the TEXTURE1 lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "TEXTURE1":
                return TextureList(entry)
        return None

    @cached_property
    def texture2(self) -> TextureList | None:
        """Return the TEXTURE2 lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "TEXTURE2":
                return TextureList(entry)
        return None

    @cached_property
    def flats(self) -> dict[str, Flat]:
        """Return all flat lumps (between F_START/F_END markers) by name."""
        result: dict[str, Flat] = {}
        inside = False
        for entry in self.directory:
            if entry.name in ("F_START", "FF_START"):
                inside = True
                continue
            if entry.name in ("F_END", "FF_END"):
                inside = False
                continue
            if inside and entry.size == 4096:
                result[entry.name] = Flat(entry)
        return result

    def get_flat(self, name: str) -> Flat | None:
        """Return a named flat, or None if not found."""
        return self.flats.get(name.upper())

    def get_picture(self, name: str) -> Picture | None:
        """Return a named lump as a Picture (patch/sprite/graphic), or None."""
        for entry in self.directory:
            if entry.name == name:
                return Picture(entry)
        return None

    def get_lump(self, name: str) -> BaseLump | None:
        """Return the first directory lump with the given name, or None."""
        for entry in self.directory:
            if entry.name == name:
                return BaseLump(entry)
        return None

    def get_lumps(self, name: str) -> list[BaseLump]:
        """Return all directory lumps with the given name."""
        return [BaseLump(e) for e in self.directory if e.name == name]

    @cached_property
    def music(self) -> dict[str, Mus]:
        """Return all MUS music lumps by name, detected by MUS\\x1a magic bytes."""
        result: dict[str, Mus] = {}
        for entry in self.directory:
            if entry.size < _MUS_MIN_SIZE:
                continue
            self.fd.seek(entry.offset)
            if self.fd.read(4) == _MUS_MAGIC:
                result[entry.name] = Mus(entry)
        return result

    def get_music(self, name: str) -> Mus | None:
        """Return a named MUS lump, or None if not found."""
        return self.music.get(name.upper())

    _DMX_HEADER_SIZE: int = 8   # fmt(2) + rate(2) + num_samples(4)

    @cached_property
    def sounds(self) -> dict[str, DmxSound]:
        """Return all DMX digitized sound lumps, detected by format=3 magic bytes.

        num_samples in the DMX header includes the 16-byte padding, so the
        expected total lump size is header(8) + num_samples.
        """
        result: dict[str, DmxSound] = {}
        for entry in self.directory:
            if entry.size < self._DMX_HEADER_SIZE:
                continue
            self.fd.seek(entry.offset)
            raw_header = self.fd.read(self._DMX_HEADER_SIZE)
            fmt = int.from_bytes(raw_header[0:2], "little")
            rate = int.from_bytes(raw_header[2:4], "little")
            num_samples = int.from_bytes(raw_header[4:8], "little")
            expected_size = self._DMX_HEADER_SIZE + num_samples
            if fmt == 3 and 4000 <= rate <= 44100 and expected_size <= entry.size:
                result[entry.name] = DmxSound(entry)
        return result

    def get_sound(self, name: str) -> DmxSound | None:
        return self.sounds.get(name.upper())

    @cached_property
    def sprites(self) -> dict[str, Picture]:
        result: dict[str, Picture] = {}
        inside = False
        for entry in self.directory:
            if entry.name in ("S_START", "SS_START"):
                inside = True
                continue
            if entry.name in ("S_END", "SS_END"):
                inside = False
                continue
            if inside and entry.size > 0:
                result[entry.name] = Picture(entry)
        return result

    def get_sprite(self, name: str) -> Picture | None:
        return self.sprites.get(name.upper())

    @cached_property
    def endoom(self) -> Endoom | None:
        for entry in self.directory:
            if entry.name == "ENDOOM":
                return Endoom(entry)
        return None

    @cached_property
    def sndinfo(self) -> SndInfo | None:
        """Return the SNDINFO lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "SNDINFO":
                return SndInfo(entry)
        return None

    @cached_property
    def mapinfo(self) -> MapInfoLump | None:
        """Return the MAPINFO lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "MAPINFO":
                return MapInfoLump(entry)
        return None

    @cached_property
    def animdefs(self) -> AnimDefsLump | None:
        """Return the ANIMDEFS lump, or None if not present."""
        for entry in self.directory:
            if entry.name == "ANIMDEFS":
                return AnimDefsLump(entry)
        return None
