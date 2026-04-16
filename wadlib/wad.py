import re
from functools import cached_property
from io import SEEK_END, SEEK_SET, BytesIO
from struct import calcsize, unpack
from typing import Any, BinaryIO

from .constants import (
    DIRECTORY_ENTRY_FORMAT,
    DOOM1_MAP_NAME_REGEX,
    DOOM2_MAP_NAME_REGEX,
    HEADER_FORMAT,
)
from .directory import DirectoryEntry
from .enums import WadType
from .exceptions import BadHeaderWadException, InvalidDirectoryError, TruncatedWadError
from .lumps.animdefs import AnimDefsLump
from .lumps.base import BaseLump
from .lumps.colormap import ColormapLump
from .lumps.decorate import DecorateLump
from .lumps.dehacked import DehackedFile, DehackedLump
from .lumps.endoom import Endoom
from .lumps.flat import Flat
from .lumps.language import LanguageLump
from .lumps.map import BaseMapEntry
from .lumps.mapinfo import MapInfoLump
from .lumps.mus import _HEADER_SIZE as _MUS_MIN_SIZE
from .lumps.mus import _MUS_MAGIC, Mus
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
from .lumps.sndinfo import SndInfo
from .lumps.sndseq import SndSeqLump
from .lumps.sound import _HEADER_SIZE as _DMX_HEADER_SIZE
from .lumps.sound import DmxSound
from .lumps.textures import PNames, TextureList
from .lumps.zmapinfo import ZMapInfoLump
from .registry import assemble_maps

_STCFN_RE = re.compile(r"^STCFN(\d{3})$")


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

    def __repr__(self) -> str:
        name = getattr(self.fd, "name", "<embedded>")
        return f"WadFile({name!r})"

    @classmethod
    def from_bytes(cls, data: bytes, *, name: str = "<embedded>") -> "WadFile":
        """Parse a WAD from an in-memory *data* buffer.

        This is primarily used for embedded WAD maps inside PK3 archives
        (``maps/MAP01.wad`` entries), where the WAD is stored as raw bytes
        inside a ZIP entry rather than as a standalone file.

        The returned ``WadFile`` has no real file descriptor; its internal
        ``fd`` is a :class:`io.BytesIO` buffer.  Calling :meth:`close` on it
        is safe but is effectively a no-op — the buffer is released when the
        object is garbage-collected.

        Args:
            data: Raw WAD bytes.
            name: Optional label used in error messages (default ``"<embedded>"``).

        Raises:
            :exc:`~wadlib.exceptions.TruncatedWadError`: *data* is too short.
            :exc:`~wadlib.exceptions.BadHeaderWadException`: bad magic bytes.
            :exc:`~wadlib.exceptions.InvalidDirectoryError`: directory out of bounds.
        """
        wad = object.__new__(cls)
        wad.fd = BytesIO(data)
        header_size = calcsize(HEADER_FORMAT)
        raw_header = wad.fd.read(header_size)
        if len(raw_header) < header_size:
            raise TruncatedWadError(
                f"{name!r}: buffer too short for WAD header: "
                f"{len(raw_header)} bytes (expected {header_size})"
            )
        magic_raw, wad.directory_size, wad._directory_offset = unpack(HEADER_FORMAT, raw_header)
        if not magic_raw.isascii():
            raise BadHeaderWadException(repr(magic_raw))
        magic = magic_raw.decode("ascii")
        if magic not in WadType.names():
            raise BadHeaderWadException(magic)
        wad.fd.seek(0, SEEK_END)
        file_size = wad.fd.tell()
        dir_end = wad._directory_offset + wad.directory_size * calcsize(DIRECTORY_ENTRY_FORMAT)
        if wad._directory_offset < 0 or dir_end > file_size:
            raise InvalidDirectoryError(
                f"{name!r}: directory table out of bounds: "
                f"offset={wad._directory_offset}, entries={wad.directory_size}, "
                f"file_size={file_size}"
            )
        wad.wad_type = WadType[magic]
        wad._pwads = []
        return wad

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

    @property
    def all_wads(self) -> "list[WadFile]":
        """All WAD files in this PWAD stack, highest-priority first.

        The base WAD is last; each layered PWAD precedes it.  This is the
        canonical order for resource resolution (first match wins) and is
        the public counterpart of the internal ``_all_wads`` property.
        """
        return self._all_wads

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
        # Directories in base-first order (reversed _all_wads) so PWADs overwrite.
        return assemble_maps([w.directory for w in reversed(self._all_wads)])

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

    def find_lumps(self, name: str) -> "list[DirectoryEntry]":
        """Return all directory entries with the given name, highest priority first.

        Unlike :meth:`find_lump`, which stops at the first match, this returns
        every entry across all loaded WADs (base + PWADs).  Entries are ordered
        highest-priority first: PWADs before the base WAD, and within each WAD
        the last directory entry comes first, matching ``W_CheckNumForName``
        semantics.

        ``find_lumps(name)[0] == find_lump(name)`` holds whenever the result is
        non-empty.

        Unlike :meth:`get_lumps`, which wraps entries in ``BaseLump`` and uses
        base-WAD-first ordering, this method returns raw ``DirectoryEntry``
        objects in priority order.
        """
        upper = name.upper()
        result: list[DirectoryEntry] = []
        for wad in self._all_wads:
            result.extend(entry for entry in reversed(wad.directory) if entry.name == upper)
        return result

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
