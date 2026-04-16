"""pk3 archive support — read and write ZIP-based WAD archives.

pk3 files are standard ZIP archives used by GZDoom and other modern source
ports.  Files inside the ZIP are organised by directory::

    flats/FLOOR0_1.png
    sprites/TROOA1.png
    sounds/DSPISTOL.wav
    music/D_RUNNIN.mid
    maps/MAP01.wad          (embedded WAD with map data)
    patches/WALL00_1.png
    textures/BRICK7.png
    ...

This module provides ``Pk3Archive`` with the same interface as ``WadArchive``
for reading and writing pk3 files, plus conversion between WAD and pk3.

Usage::

    from wadlib.pk3 import Pk3Archive

    # Read a pk3
    with Pk3Archive("mod.pk3") as pk3:
        print(pk3.namelist())
        data = pk3.read("sounds/DSPISTOL.wav")

    # Convert WAD to pk3
    from wadlib.pk3 import wad_to_pk3
    wad_to_pk3("DOOM2.WAD", "doom2.pk3")

    # Convert pk3 to WAD
    from wadlib.pk3 import pk3_to_wad
    pk3_to_wad("mod.pk3", "mod.wad")
"""

from __future__ import annotations

import os
import zipfile
from dataclasses import dataclass
from functools import cached_property
from io import BytesIO
from typing import TYPE_CHECKING, Literal

from PIL import Image as _PIL

from .constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
from .directory import DirectoryEntry
from .enums import MapData, WadType
from .exceptions import BadHeaderWadException, InvalidDirectoryError, TruncatedWadError
from .wad import WadFile
from .writer import WadWriter

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry

# Canonical category names used by all resource properties.
# Keys are the normalized lowercase directory names found in real pk3 files;
# values are the canonical name this library exposes.
_CATEGORY_ALIASES: dict[str, str] = {
    "sound": "sounds",
    "sounds": "sounds",
    "sfx": "sounds",
    "mus": "music",
    "music": "music",
    "musics": "music",
    "sprite": "sprites",
    "sprites": "sprites",
    "flat": "flats",
    "flats": "flats",
    "patch": "patches",
    "patches": "patches",
    "graphic": "graphics",
    "graphics": "graphics",
    "hires": "hires",
    "texture": "textures",
    "textures": "textures",
    "voxel": "voxels",
    "voxels": "voxels",
    "lump": "lumps",
    "lumps": "lumps",
    "maps": "maps",
    "map": "maps",
    "acs": "acs",
    "filter": "filter",
    "skins": "skins",
    "skin": "skins",
    "voices": "voices",
    "voice": "voices",
}


@dataclass(frozen=True)
class Pk3Entry:
    """Metadata for a file inside a pk3 archive."""

    path: str
    size: int
    compressed_size: int

    @property
    def name(self) -> str:
        """The bare filename without directory."""
        return os.path.basename(self.path)

    @property
    def lump_name(self) -> str:
        """The lump name (filename without extension, uppercased, max 8 chars)."""
        base = os.path.splitext(self.name)[0]
        return base.upper()[:8]

    @property
    def category(self) -> str:
        """The canonical category (flats, sprites, sounds, etc.) or empty string.

        Raw directory names are normalized through ``_CATEGORY_ALIASES`` so
        that ``sfx/`` → ``sounds``, ``flat/`` → ``flats``, etc.
        """
        parts = self.path.replace("\\", "/").split("/")
        if len(parts) <= 1:
            return ""
        raw = parts[0].lower()
        return _CATEGORY_ALIASES.get(raw, raw)

    def __repr__(self) -> str:
        return f"<Pk3Entry {self.path!r} {self.size} bytes>"


class Pk3Archive:
    """Read and write pk3 (ZIP) archives.

    Modes:

    ``"r"``  Read an existing pk3.
    ``"w"``  Create a new pk3 from scratch.
    ``"a"``  Open an existing pk3 for modification.
    """

    def __init__(self, file: str, mode: Literal["r", "w", "a"] = "r") -> None:
        if mode not in ("r", "w", "a"):
            raise ValueError(f"Invalid mode: {mode!r}")
        self._filename = file
        self._mode = mode
        self._zf = zipfile.ZipFile(file, mode, compression=zipfile.ZIP_DEFLATED)  # pylint: disable=consider-using-with

    def __enter__(self) -> Pk3Archive:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def close(self) -> None:
        self._zf.close()

    # -- Read interface -------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def filename(self) -> str:
        return self._filename

    def namelist(self) -> list[str]:
        """Return all file paths in the archive (excluding directories)."""
        return [n for n in self._zf.namelist() if not n.endswith("/")]

    def infolist(self) -> list[Pk3Entry]:
        """Return metadata for every file in the archive."""
        result: list[Pk3Entry] = []
        for info in self._zf.infolist():
            if info.filename.endswith("/"):
                continue
            result.append(
                Pk3Entry(
                    path=info.filename,
                    size=info.file_size,
                    compressed_size=info.compress_size,
                )
            )
        return result

    def read(self, path: str) -> bytes:
        """Read a file from the archive by its full path."""
        return self._zf.read(path)

    def __contains__(self, path: str) -> bool:
        try:
            self._zf.getinfo(path)
            return True
        except KeyError:
            return False

    def __len__(self) -> int:
        return len(self.namelist())

    # -- Write interface ------------------------------------------------------

    def writestr(self, path: str, data: bytes) -> None:
        """Write data to a path inside the archive."""
        self._zf.writestr(path, data)

    def write(self, filename: str, arcname: str | None = None) -> None:
        """Add a file from disk to the archive."""
        self._zf.write(filename, arcname or filename)

    def mkdir(self, path: str) -> None:
        """Create a directory entry in the archive."""
        if not path.endswith("/"):
            path += "/"
        if path not in self._zf.namelist():
            self._zf.writestr(path, b"")

    # -- Dunder ---------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Pk3Archive {self._filename!r} mode={self._mode!r}>"

    # -- Resource API ---------------------------------------------------------

    @cached_property
    def _by_category(self) -> dict[str, list[Pk3Entry]]:
        """Group all entries by canonical category name."""
        result: dict[str, list[Pk3Entry]] = {}
        for entry in self.infolist():
            raw_cat = entry.category.lower()
            canonical = _CATEGORY_ALIASES.get(raw_cat, raw_cat)
            result.setdefault(canonical, []).append(entry)
        return result

    def _category_dict(self, category: str) -> dict[str, bytes]:
        return {e.lump_name: self.read(e.path) for e in self._by_category.get(category, [])}

    @property
    def sounds(self) -> dict[str, bytes]:
        """All entries under ``sounds/`` (or ``sound/``, ``sfx/``) as lump_name → bytes."""
        return self._category_dict("sounds")

    @property
    def music(self) -> dict[str, bytes]:
        """All entries under ``music/`` (or ``mus/``) as lump_name → bytes."""
        return self._category_dict("music")

    @property
    def sprites(self) -> dict[str, bytes]:
        """All entries under ``sprites/`` (or ``sprite/``) as lump_name → bytes."""
        return self._category_dict("sprites")

    @property
    def flats(self) -> dict[str, bytes]:
        """All entries under ``flats/`` (or ``flat/``) as lump_name → bytes."""
        return self._category_dict("flats")

    @property
    def patches(self) -> dict[str, bytes]:
        """All entries under ``patches/`` (or ``patch/``) as lump_name → bytes."""
        return self._category_dict("patches")

    @property
    def graphics(self) -> dict[str, bytes]:
        """All entries under ``graphics/`` (or ``graphic/``) as lump_name → bytes."""
        return self._category_dict("graphics")

    @property
    def textures(self) -> dict[str, bytes]:
        """All entries under ``textures/`` (or ``texture/``) as lump_name → bytes."""
        return self._category_dict("textures")

    # -- Image decoding -------------------------------------------------------

    @staticmethod
    def _decode_image(data: bytes) -> _PIL.Image:
        """Decode raw image bytes (PNG, JPEG, TGA, …) into a Pillow Image.

        `.load()` is called immediately so the BytesIO buffer can be discarded
        without keeping it alive for the lifetime of the Image object.
        """
        img = _PIL.open(BytesIO(data))
        img.load()
        return img

    def _category_images(self, category: str) -> dict[str, _PIL.Image]:
        """Return lump_name -> decoded Image for every entry in *category*."""
        return {
            e.lump_name: self._decode_image(self.read(e.path))
            for e in self._by_category.get(category, [])
        }

    @property
    def flat_images(self) -> dict[str, _PIL.Image]:
        """All flat entries decoded as Pillow Images (lump_name -> Image)."""
        return self._category_images("flats")

    @property
    def sprite_images(self) -> dict[str, _PIL.Image]:
        """All sprite entries decoded as Pillow Images (lump_name -> Image)."""
        return self._category_images("sprites")

    @property
    def patch_images(self) -> dict[str, _PIL.Image]:
        """All patch entries decoded as Pillow Images (lump_name -> Image)."""
        return self._category_images("patches")

    @property
    def texture_images(self) -> dict[str, _PIL.Image]:
        """All texture entries decoded as Pillow Images (lump_name -> Image)."""
        return self._category_images("textures")

    def find_resource(self, name: str) -> Pk3Entry | None:
        """Find the first entry whose lump name matches *name* (case-insensitive).

        The search is case-insensitive and truncates to 8 characters to match
        WAD lump name semantics.  Returns ``None`` if not found.

        .. note::
            When multiple entries share the same lump name (e.g. two sprites
            that collide after uppercasing and 8-character truncation), only
            the first match in ZIP order is returned.  Use :meth:`find_resources`
            to retrieve all colliding entries.
        """
        name_upper = name.upper()[:8]
        for entry in self.infolist():
            if entry.lump_name == name_upper:
                return entry
        return None

    def find_resources(self, name: str) -> list[Pk3Entry]:
        """Return all entries whose lump name matches *name* (case-insensitive).

        Unlike :meth:`find_resource`, this returns every entry that maps to the
        same WAD-style lump name, in ZIP order.  This is useful when PK3 entries
        collide after uppercasing and 8-character truncation::

            entries = pk3.find_resources("TROGEN")
            # might return both sprites/TROGEN1.png and sprites/TROGEN2.png
            # if both truncate to the same 8-char lump name

        Returns an empty list if no entry matches.
        """
        name_upper = name.upper()[:8]
        return [e for e in self.infolist() if e.lump_name == name_upper]

    def read_resource(self, name: str) -> bytes | None:
        """Read the first entry whose lump name matches *name*.

        Returns the raw bytes of the entry, or ``None`` if not found.
        """
        entry = self.find_resource(name)
        return self.read(entry.path) if entry else None

    @cached_property
    def maps(self) -> dict[str, BaseMapEntry]:
        """Return all maps assembled from this PK3 archive.

        Two PK3 map formats are supported:

        Embedded WAD (``maps/MAP01.wad``)
            The WAD bytes are parsed in memory and assembled exactly as if
            they were a standalone WAD file.

        Decomposed (``maps/MAP01/THINGS.lmp``, ``maps/MAP01/SECTORS.lmp``, …)
            Lump files are grouped by map name and assembled via the standard
            ``attach_map_lumps`` dispatch.

        When both formats contribute the same map name the embedded WAD
        takes precedence (it carries richer data).

        The :attr:`~wadlib.lumps.map.BaseMapEntry.origin` attribute of each
        returned map is set to the path that contributed it — e.g.
        ``"mod.pk3/maps/MAP01.wad"`` or ``"mod.pk3/maps/MAP01/"``.
        """
        from .lumps.map import MapEntry
        from .registry import assemble_maps, attach_map_lumps
        from .source import MemoryLumpSource

        result: dict[str, BaseMapEntry] = {}
        embedded_names: set[str] = set()

        # --- embedded WADs (maps/MAP01.wad) ----------------------------------
        for entry in self.infolist():
            parts = entry.path.replace("\\", "/").split("/")
            if len(parts) != 2:
                continue
            if parts[0].lower() not in ("maps", "map"):
                continue
            if os.path.splitext(parts[1])[1].lower() != ".wad":
                continue
            map_stem = os.path.splitext(parts[1])[0].upper()
            if not (DOOM1_MAP_NAME_REGEX.match(map_stem) or DOOM2_MAP_NAME_REGEX.match(map_stem)):
                continue
            try:
                embedded = WadFile.from_bytes(self.read(entry.path), name=entry.path)
            except (BadHeaderWadException, TruncatedWadError, InvalidDirectoryError):
                continue
            seen, _ = assemble_maps([embedded.directory])
            for map_name, map_entry in seen.items():
                map_entry.origin = f"{self._filename}/maps/{parts[1]}"
                result[map_name] = map_entry
                embedded_names.add(map_name)

        # --- decomposed maps (maps/MAP01/THINGS.lmp) -------------------------
        decomposed: dict[str, list[tuple[str, bytes]]] = {}
        for entry in self.infolist():
            parts = entry.path.replace("\\", "/").split("/")
            if len(parts) != 3:
                continue
            if parts[0].lower() not in ("maps", "map"):
                continue
            map_name = parts[1].upper()
            if not (DOOM1_MAP_NAME_REGEX.match(map_name) or DOOM2_MAP_NAME_REGEX.match(map_name)):
                continue
            lump_name = os.path.splitext(parts[2])[0].upper()[:8]
            decomposed.setdefault(map_name, []).append((lump_name, self.read(entry.path)))

        for map_name, lumps in decomposed.items():
            if map_name in embedded_names:
                continue  # embedded WAD takes precedence
            marker = MemoryLumpSource(map_name, b"")
            try:
                map_entry = MapEntry(marker)
            except ValueError:
                continue
            lump_sources = [MemoryLumpSource(lump_name, data) for lump_name, data in lumps]
            hexen = any(ln == "BEHAVIOR" for ln, _ in lumps)
            attach_map_lumps(map_entry, lump_sources, hexen)
            map_entry.origin = f"{self._filename}/maps/{map_name}/"
            result[map_name] = map_entry

        return result


# ---------------------------------------------------------------------------
# Conversion: WAD <-> pk3
# ---------------------------------------------------------------------------

# pk3 directory categories for known lump types / namespaces
_NAMESPACE_DIRS: dict[str, str] = {
    "F_START": "flats",
    "FF_START": "flats",
    "S_START": "sprites",
    "SS_START": "sprites",
    "P_START": "patches",
    "PP_START": "patches",
}

_NAMESPACE_ENDS: set[str] = {
    "F_END",
    "FF_END",
    "S_END",
    "SS_END",
    "P_END",
    "PP_END",
}


def wad_to_pk3(wad_path: str, pk3_path: str) -> None:
    """Convert a WAD file to a pk3 (ZIP) archive.

    Lumps are organised into directories by type:
    - Flats (between F_START/F_END) -> ``flats/``
    - Sprites (S_START/S_END) -> ``sprites/``
    - Patches (P_START/P_END) -> ``patches/``
    - Map markers + sub-lumps -> ``maps/``
    - Everything else -> ``lumps/``

    Lump data is stored as raw ``.lmp`` files (no format conversion).

    When a WAD contains duplicate lump names within the same namespace,
    last-wins semantics are applied (consistent with Doom's own behaviour),
    so the output PK3 never contains duplicate ZIP entries.
    """
    map_data_names = set(MapData.names())

    with WadFile(wad_path) as wad, Pk3Archive(pk3_path, "w") as pk3:
        # --- Pass 1: compute the zip path for every content entry ----------
        # planned[i] = (DirectoryEntry, zip_path_string)
        planned: list[tuple[DirectoryEntry, str]] = []
        current_ns: str | None = None
        in_map: str | None = None

        for entry in wad.directory:
            name = entry.name

            # Namespace tracking
            if name in _NAMESPACE_DIRS:
                current_ns = _NAMESPACE_DIRS[name]
                continue
            if name in _NAMESPACE_ENDS:
                current_ns = None
                continue

            # Map tracking
            is_map_marker = bool(
                DOOM1_MAP_NAME_REGEX.match(name) or DOOM2_MAP_NAME_REGEX.match(name)
            )
            if is_map_marker:
                in_map = name
                continue
            if in_map and name in map_data_names:
                if entry.size > 0:
                    planned.append((entry, f"maps/{in_map}/{name}.lmp"))
                continue
            if in_map and name not in map_data_names:
                in_map = None  # exited map block

            if entry.size == 0:
                continue  # skip empty markers

            if current_ns:
                planned.append((entry, f"{current_ns}/{name}.lmp"))
            else:
                planned.append((entry, f"lumps/{name}.lmp"))

        # --- Pass 2: last-wins deduplication, then write -------------------
        # For each zip path, record the index of the last entry that maps to it.
        last_index: dict[str, int] = {}
        for i, (_, zip_path) in enumerate(planned):
            last_index[zip_path] = i

        for i, (entry, zip_path) in enumerate(planned):
            if last_index[zip_path] != i:
                continue  # a later entry supersedes this one — skip
            wad.fd.seek(entry.offset)
            data = wad.fd.read(entry.size)
            pk3.writestr(zip_path, data)


def pk3_to_wad(pk3_path: str, wad_path: str) -> None:
    """Convert a pk3 (ZIP) archive to a WAD file.

    Files are mapped back to lumps:
    - ``flats/*.lmp`` -> between F_START/F_END
    - ``sprites/*.lmp`` -> between S_START/S_END
    - ``patches/*.lmp`` -> between P_START/P_END
    - ``maps/<MAP>/`` -> map marker + sub-lumps
    - ``lumps/*.lmp`` -> top-level lumps

    Lump names are derived from filenames (uppercased, extension stripped).
    """
    writer = WadWriter(WadType.PWAD)

    with Pk3Archive(pk3_path, "r") as pk3:
        entries = pk3.infolist()

        # Group by category
        by_cat: dict[str, list[Pk3Entry]] = {}
        for entry in entries:
            cat = entry.category
            by_cat.setdefault(cat, []).append(entry)

        # Top-level lumps first
        for entry in by_cat.get("lumps", []):
            data = pk3.read(entry.path)
            writer.add_lump(entry.lump_name, data)

        # Flats
        flat_entries = by_cat.get("flats", [])
        if flat_entries:
            writer.add_marker("F_START")
            for entry in flat_entries:
                writer.add_lump(entry.lump_name, pk3.read(entry.path))
            writer.add_marker("F_END")

        # Sprites
        sprite_entries = by_cat.get("sprites", [])
        if sprite_entries:
            writer.add_marker("S_START")
            for entry in sprite_entries:
                writer.add_lump(entry.lump_name, pk3.read(entry.path))
            writer.add_marker("S_END")

        # Patches
        patch_entries = by_cat.get("patches", [])
        if patch_entries:
            writer.add_marker("P_START")
            for entry in patch_entries:
                writer.add_lump(entry.lump_name, pk3.read(entry.path))
            writer.add_marker("P_END")

        # Maps — group by map name
        map_entries = by_cat.get("maps", [])
        maps: dict[str, list[Pk3Entry]] = {}
        for entry in map_entries:
            parts = entry.path.replace("\\", "/").split("/")
            if len(parts) >= 3:
                map_name = parts[1].upper()
                maps.setdefault(map_name, []).append(entry)

        for map_name in sorted(maps):
            writer.add_marker(map_name)
            for entry in maps[map_name]:
                writer.add_lump(entry.lump_name, pk3.read(entry.path))

    writer.save(wad_path)
