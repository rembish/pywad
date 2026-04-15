import re
from collections.abc import Callable
from functools import cached_property
from io import SEEK_END, SEEK_SET
from struct import calcsize, unpack
from typing import Any, BinaryIO

from .constants import (
    DIRECTORY_ENTRY_FORMAT,
    DOOM1_MAP_NAME_REGEX,
    DOOM2_MAP_NAME_REGEX,
    HEADER_FORMAT,
)
from .directory import DirectoryEntry
from .enums import MapData, WadType
from .exceptions import BadHeaderWadException, InvalidDirectoryError, TruncatedWadError
from .lumps.animdefs import AnimDefsLump
from .lumps.base import BaseLump
from .lumps.behavior import BehaviorLump
from .lumps.blockmap import BlockMap, Reject
from .lumps.colormap import ColormapLump
from .lumps.decorate import DecorateLump
from .lumps.dehacked import DehackedFile, DehackedLump
from .lumps.endoom import Endoom
from .lumps.flat import Flat
from .lumps.hexen import HexenLineDefs, HexenThings
from .lumps.language import LanguageLump
from .lumps.lines import Lines
from .lumps.map import BaseMapEntry, MapEntry  # MapEntry is a factory function
from .lumps.mapinfo import MapInfoLump
from .lumps.mus import _HEADER_SIZE as _MUS_MIN_SIZE
from .lumps.mus import _MUS_MAGIC, Mus
from .lumps.nodes import Nodes
from .lumps.ogg import (
    MIDI_MAGIC,
    MP3_ID3_MAGIC,
    MP3_SYNC_MAGIC,
    MP3_SYNC_MAGIC2,
    MP3_SYNC_MAGIC3,
    OGG_MAGIC,
    MidiLump,
    Mp3Lump,
    OggLump,
)
from .lumps.picture import Picture
from .lumps.playpal import PlayPal
from .lumps.sectors import Sectors
from .lumps.segs import Segs, SubSectors
from .lumps.sidedefs import SideDefs
from .lumps.sndinfo import SndInfo
from .lumps.sndseq import SndSeqLump
from .lumps.sound import _HEADER_SIZE as _DMX_HEADER_SIZE
from .lumps.sound import DmxSound
from .lumps.textures import PNames, TextureList
from .lumps.things import Things
from .lumps.udmf import UdmfLump
from .lumps.vertices import Vertices
from .lumps.zmapinfo import ZMapInfoLump
from .lumps.znodes import ZNodesLump

_STCFN_RE = re.compile(r"^STCFN(\d{3})$")

# Doom-format lump dispatch: name -> (attach method, constructor)
_DOOM_DISPATCH: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
    "THINGS": ("attach_things", Things),
    "VERTEXES": ("attach_vertices", Vertices),
    "LINEDEFS": ("attach_linedefs", Lines),
    "SIDEDEFS": ("attach_sidedefs", SideDefs),
    "SECTORS": ("attach_sectors", Sectors),
    "SEGS": ("attach_segs", Segs),
    "SSECTORS": ("attach_ssectors", SubSectors),
    "NODES": ("attach_nodes", Nodes),
    "REJECT": ("attach_reject", Reject),
    "BLOCKMAP": ("attach_blockmap", BlockMap),
    "ZNODES": ("attach_znodes", ZNodesLump),
    "BEHAVIOR": ("attach_behavior", BehaviorLump),
    "TEXTMAP": ("attach_textmap", UdmfLump),
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


class WadFile:  # pylint: disable=too-many-public-methods
    fd: BinaryIO

    def __init__(self, filename: str) -> None:
        self.fd = open(filename, "rb")  # noqa: SIM115  # pylint: disable=consider-using-with
        try:
            header_size = calcsize(HEADER_FORMAT)
            raw_header = self.fd.read(header_size)
            if len(raw_header) < header_size:
                raise TruncatedWadError(
                    f"File too short for WAD header: {len(raw_header)} bytes "
                    f"(expected {header_size})"
                )
            magic_raw, self.directory_size, self._directory_offset = unpack(
                HEADER_FORMAT, raw_header
            )
            if not magic_raw.isascii():
                raise BadHeaderWadException(repr(magic_raw))
            magic = magic_raw.decode("ascii")
            if magic not in WadType.names():
                raise BadHeaderWadException(magic)

            # Validate that the directory table lies within the file.
            self.fd.seek(0, SEEK_END)
            file_size = self.fd.tell()
            dir_end = self._directory_offset + self.directory_size * calcsize(
                DIRECTORY_ENTRY_FORMAT
            )
            if self._directory_offset < 0 or dir_end > file_size:
                raise InvalidDirectoryError(
                    f"Directory table out of bounds: offset={self._directory_offset}, "
                    f"entries={self.directory_size}, file_size={file_size}"
                )
        except Exception:
            self.fd.close()
            raise

        self.wad_type = WadType[magic]
        self._pwads: list[WadFile] = []

    @classmethod
    def open(cls, base: str, *pwads: str) -> "WadFile":
        """Open a base WAD with zero or more PWADs layered on top.

        PWAD lumps shadow base-WAD lumps by name, exactly as the Doom engine
        does when loading patches.  The returned object is the base ``WadFile``;
        call ``.close()`` (or use it as a context manager) to release all files.

        Example::

            with WadFile.open("wads/DOOM2.WAD", "wads/scythe2.wad") as wad:
                print(wad.maps)
        """
        wad = cls(base)
        try:
            for path in pwads:
                wad._pwads.append(cls(path))
        except Exception:
            wad.close()
            raise
        return wad

    def close(self) -> None:
        for pwad in self._pwads:
            pwad.close()
        if not self.fd.closed:
            self.fd.close()

    def __enter__(self) -> "WadFile":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    @property
    def _all_wads(self) -> "list[WadFile]":
        """PWAD-first order: later (higher-priority) WADs come first."""
        return [*list(reversed(self._pwads)), self]

    @cached_property
    def directory(self) -> list[DirectoryEntry]:
        self.fd.seek(0, SEEK_END)
        file_size = self.fd.tell()

        self.fd.seek(self._directory_offset, SEEK_SET)
        entry_size = calcsize(DIRECTORY_ENTRY_FORMAT)

        entries = []
        for _ in range(self.directory_size):
            raw = self.fd.read(entry_size)
            if len(raw) < entry_size:
                raise TruncatedWadError("Unexpected end of file while reading WAD directory")
            lump = unpack(DIRECTORY_ENTRY_FORMAT, raw)
            offset, size, name = lump
            if size > 0 and (offset < 0 or offset + size > file_size):
                decoded_name = name.rstrip(b"\x00").decode("ascii", errors="replace")
                raise InvalidDirectoryError(
                    f"Lump {decoded_name!r} data out of bounds: "
                    f"offset={offset}, size={size}, file_size={file_size}"
                )
            entries.append(DirectoryEntry(self, *lump))
        return entries

    @cached_property
    def _maps_raw(self) -> tuple[dict[str, BaseMapEntry], list[str]]:
        """Return (seen, order) where *order* is WAD directory insertion order."""
        seen: dict[str, BaseMapEntry] = {}  # name → map entry, last writer wins
        order: list[str] = []  # insertion order from WAD directory

        for wad in reversed(self._all_wads):  # base first, PWADs overwrite
            groups: list[tuple[DirectoryEntry, list[DirectoryEntry]]] = []
            current_lumps: list[DirectoryEntry] = []
            marker: DirectoryEntry | None = None

            for entry in wad.directory:
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

            for map_marker, lumps in groups:
                map_entry = MapEntry(map_marker)
                hexen = any(e.name == "BEHAVIOR" for e in lumps)
                _attach_lumps(map_entry, lumps, hexen)
                name = str(map_entry)
                if name not in seen:
                    order.append(name)
                seen[name] = map_entry

        return seen, order

    @cached_property
    def maps(self) -> list[BaseMapEntry]:
        """Maps sorted by episode/map number (E1M1, E1M2, … or MAP01, MAP02, …)."""
        seen, order = self._maps_raw

        def _map_sort_key(name: str) -> tuple[int, int, int]:
            m1 = DOOM1_MAP_NAME_REGEX.match(name)
            if m1:
                return (0, int(m1.group("episode")), int(m1.group("number")))
            m2 = DOOM2_MAP_NAME_REGEX.match(name)
            if m2:
                return (1, 0, int(m2.group("number")))
            return (2, 0, 0)

        return [seen[n] for n in sorted(order, key=_map_sort_key)]

    @cached_property
    def maps_in_order(self) -> list[BaseMapEntry]:
        """Maps in the order they appear in the WAD directory (no sorting)."""
        seen, order = self._maps_raw
        return [seen[n] for n in order]

    def find_lump(self, name: str) -> "DirectoryEntry | None":
        """Return the highest-priority directory entry with the given name.

        PWADs are checked newest-first, then the base WAD -- mirroring how
        the Doom engine resolves lump names when multiple WADs are loaded.
        Within each WAD the directory is scanned in reverse so the last entry
        with a given name wins, matching Doom's ``W_CheckNumForName`` semantics.
        """
        for wad in self._all_wads:
            for entry in reversed(wad.directory):
                if entry.name == name:
                    return entry
        return None

    @cached_property
    def playpal(self) -> PlayPal | None:
        """Return the PLAYPAL lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("PLAYPAL")
        return PlayPal(entry) if entry else None

    @cached_property
    def colormap(self) -> ColormapLump | None:
        """Return the COLORMAP lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("COLORMAP")
        return ColormapLump(entry) if entry else None

    @cached_property
    def pnames(self) -> PNames | None:
        """Return the PNAMES lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("PNAMES")
        return PNames(entry) if entry else None

    @cached_property
    def texture1(self) -> TextureList | None:
        """Return the TEXTURE1 lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("TEXTURE1")
        return TextureList(entry) if entry else None

    @cached_property
    def texture2(self) -> TextureList | None:
        """Return the TEXTURE2 lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("TEXTURE2")
        return TextureList(entry) if entry else None

    @cached_property
    def flats(self) -> dict[str, Flat]:
        """Return all flat lumps (PWAD-aware), base WAD first then PWAD overrides."""
        result: dict[str, Flat] = {}
        # Collect base-first so PWAD entries overwrite base entries
        for wad in reversed(self._all_wads):
            inside = False
            for entry in wad.directory:
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
        """Return a named flat (PWAD-aware), or None if not found."""
        return self.flats.get(name.upper())

    def get_picture(self, name: str) -> Picture | None:
        """Return a named lump as a Picture (PWAD-aware), or None."""
        entry = self.find_lump(name.upper())
        return Picture(entry) if entry else None

    def get_lump(self, name: str) -> BaseLump[Any] | None:
        """Return the first directory lump with the given name (PWAD-aware), or None."""
        entry = self.find_lump(name.upper())
        return BaseLump(entry) if entry else None

    def get_lumps(self, name: str) -> list[BaseLump[Any]]:
        """Return all directory lumps with the given name across all loaded WADs."""
        upper = name.upper()
        return [BaseLump(e) for wad in self._all_wads for e in wad.directory if e.name == upper]

    @cached_property
    def music(self) -> dict[str, Mus | MidiLump | OggLump | Mp3Lump]:
        """Return all music lumps by name (PWAD-aware), detected by magic bytes.

        Supports MUS (Doom native), MIDI (Standard MIDI Format), OGG Vorbis, and MP3.
        """
        result: dict[str, Mus | MidiLump | OggLump | Mp3Lump] = {}
        for wad in reversed(self._all_wads):
            for entry in wad.directory:
                if entry.size < 4:
                    continue
                wad.fd.seek(entry.offset)
                magic = wad.fd.read(4)
                if len(magic) < 4:
                    continue
                if magic == _MUS_MAGIC and entry.size >= _MUS_MIN_SIZE:
                    result[entry.name] = Mus(entry)
                elif magic[:4] == MIDI_MAGIC:
                    result[entry.name] = MidiLump(entry)
                elif magic[:4] == OGG_MAGIC:
                    result[entry.name] = OggLump(entry)
                elif magic[:3] == MP3_ID3_MAGIC or magic[:2] in (
                    MP3_SYNC_MAGIC,
                    MP3_SYNC_MAGIC2,
                    MP3_SYNC_MAGIC3,
                ):
                    result[entry.name] = Mp3Lump(entry)
        return result

    def get_music(self, name: str) -> Mus | MidiLump | OggLump | Mp3Lump | None:
        """Return a named music lump (MUS/MIDI/OGG/MP3), or None if not found."""
        return self.music.get(name.upper())

    @cached_property
    def sounds(self) -> dict[str, DmxSound]:
        """Return all DMX digitized sound lumps (PWAD-aware), detected by magic bytes."""
        result: dict[str, DmxSound] = {}
        for wad in reversed(self._all_wads):
            for entry in wad.directory:
                if entry.size < _DMX_HEADER_SIZE:
                    continue
                wad.fd.seek(entry.offset)
                raw_header = wad.fd.read(_DMX_HEADER_SIZE)
                fmt = int.from_bytes(raw_header[0:2], "little")
                rate = int.from_bytes(raw_header[2:4], "little")
                num_samples = int.from_bytes(raw_header[4:8], "little")
                expected_size = _DMX_HEADER_SIZE + num_samples
                if fmt == 3 and 4000 <= rate <= 44100 and expected_size <= entry.size:
                    result[entry.name] = DmxSound(entry)
        return result

    def get_sound(self, name: str) -> DmxSound | None:
        return self.sounds.get(name.upper())

    @cached_property
    def sprites(self) -> dict[str, Picture]:
        """Return all sprite lumps (PWAD-aware), base WAD first then PWAD overrides."""
        result: dict[str, Picture] = {}
        for wad in reversed(self._all_wads):
            inside = False
            for entry in wad.directory:
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
        entry = self.find_lump("ENDOOM")
        return Endoom(entry) if entry else None

    @cached_property
    def sndinfo(self) -> SndInfo | None:
        """Return the SNDINFO lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("SNDINFO")
        return SndInfo(entry) if entry else None

    @cached_property
    def sndseq(self) -> SndSeqLump | None:
        """Return the SNDSEQ lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("SNDSEQ")
        return SndSeqLump(entry) if entry else None

    @cached_property
    def mapinfo(self) -> MapInfoLump | None:
        """Return the MAPINFO lump (Hexen format, PWAD-aware), or None if not present."""
        entry = self.find_lump("MAPINFO")
        return MapInfoLump(entry) if entry else None

    @cached_property
    def zmapinfo(self) -> ZMapInfoLump | None:
        """Return the ZMAPINFO lump (ZDoom format, PWAD-aware), or None if not present."""
        entry = self.find_lump("ZMAPINFO")
        return ZMapInfoLump(entry) if entry else None

    @cached_property
    def language(self) -> LanguageLump | None:
        """Return the LANGUAGE lump (ZDoom localisation, PWAD-aware), or None if not present."""
        entry = self.find_lump("LANGUAGE")
        return LanguageLump(entry) if entry else None

    @cached_property
    def animdefs(self) -> AnimDefsLump | None:
        """Return the ANIMDEFS lump (PWAD-aware), or None if not present."""
        entry = self.find_lump("ANIMDEFS")
        return AnimDefsLump(entry) if entry else None

    @cached_property
    def decorate(self) -> DecorateLump | None:
        """Return the DECORATE lump (ZDoom actor definitions, PWAD-aware), or None."""
        entry = self.find_lump("DECORATE")
        return DecorateLump(entry) if entry else None

    @cached_property
    def stcfn(self) -> dict[int, Picture]:
        """Return Doom's STCFN HUD font glyphs (PWAD-aware), keyed by ASCII ordinal.

        STCFN033 → ord('!') = 33, …, STCFN065 → ord('A') = 65, etc.
        """
        result: dict[int, Picture] = {}
        for wad in reversed(self._all_wads):
            for entry in wad.directory:
                m = _STCFN_RE.match(entry.name)
                if m:
                    result[int(m.group(1))] = Picture(entry)
        return result

    @cached_property
    def fonta(self) -> dict[int, Picture]:
        """Return Heretic FONTA large-font glyphs (PWAD-aware), keyed by ASCII ordinal.

        FONTA01 = '!' (33), FONTA02 = '"' (34), …
        """
        result: dict[int, Picture] = {}
        for wad in reversed(self._all_wads):
            inside = False
            index = 0
            for entry in wad.directory:
                if entry.name == "FONTA_S":
                    inside = True
                    index = 0
                    continue
                if entry.name == "FONTA_E":
                    inside = False
                    continue
                if inside:
                    result[33 + index] = Picture(entry)
                    index += 1
        return result

    @cached_property
    def fontb(self) -> dict[int, Picture]:
        """Return Heretic FONTB small-font glyphs (PWAD-aware), keyed by ASCII ordinal.

        FONTB01 = '!' (33), FONTB02 = '"' (34), …
        """
        result: dict[int, Picture] = {}
        for wad in reversed(self._all_wads):
            inside = False
            index = 0
            for entry in wad.directory:
                if entry.name == "FONTB_S":
                    inside = True
                    index = 0
                    continue
                if entry.name == "FONTB_E":
                    inside = False
                    continue
                if inside:
                    result[33 + index] = Picture(entry)
                    index += 1
        return result

    @cached_property
    def dehacked(self) -> DehackedLump | None:
        """Return the DEHACKED lump (PWAD-aware), or None if not present.

        An external ``.deh`` file takes priority if one was loaded via
        :meth:`load_deh`.
        """
        entry = self.find_lump("DEHACKED")
        return DehackedLump(entry) if entry else None

    def load_deh(self, path: str) -> None:
        """Load a standalone ``.deh`` file and use it as this WAD's DEHACKED data.

        Overrides any embedded DEHACKED lump.  Call before first access to
        ``wad.dehacked``; subsequent calls replace the previously loaded file.
        """
        # cached_property stores its value in __dict__ under the property name;
        # setting it directly bypasses the descriptor and acts as an override.
        self.__dict__["dehacked"] = DehackedFile(path)

    def load_pwad(self, path: str) -> None:
        """Dynamically layer a PWAD on top of the current WAD stack.

        Invalidates all cached properties so they are re-derived from the
        updated stack on next access.  Any external ``.deh`` override loaded
        via :meth:`load_deh` is preserved across the cache eviction.
        """
        pwad = WadFile(path)
        self._pwads.append(pwad)
        # Preserve any externally-loaded DEH override before evicting caches.
        saved_deh = self.__dict__.get("dehacked")
        # Evict every cached_property from the instance dict so they pick up
        # the new PWAD on next access.
        for name in list(self.__dict__):
            if isinstance(getattr(type(self), name, None), cached_property):
                del self.__dict__[name]
        # Restore DEH override if one was present.
        if saved_deh is not None:
            self.__dict__["dehacked"] = saved_deh
