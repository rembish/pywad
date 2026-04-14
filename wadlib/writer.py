"""WAD file writer — create and modify WAD files.

Supports creating new WAD files from scratch, copying/modifying existing ones
(round-trip), and building lumps from typed Python objects.

WAD binary layout:
  [0..3]   Magic: "IWAD" or "PWAD" (4 bytes ASCII)
  [4..7]   Number of lumps (int32 LE)
  [8..11]  Directory offset (int32 LE)
  ... lump data (variable) ...
  [dir]    Directory: [offset(4) + size(4) + name(8)] x num_lumps
"""

from __future__ import annotations

import os
import tempfile
from struct import pack
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .constants import HEADER_FORMAT
from .enums import WadType

if TYPE_CHECKING:
    from .wad import WadFile


@runtime_checkable
class Serializable(Protocol):
    """Any object with a ``to_bytes()`` method."""

    def to_bytes(self) -> bytes: ...


_HEADER_SIZE = 12  # 4 (magic) + 4 (numlumps) + 4 (diroffset)
_DIR_ENTRY_SIZE = 16  # 4 (offset) + 4 (size) + 8 (name)


def _encode_name(name: str) -> bytes:
    """Encode a lump name to 8-byte null-padded ASCII."""
    return name.encode("ascii")[:8].ljust(8, b"\x00")


class WriterEntry:
    """A single lump entry in the writer's lump list."""

    __slots__ = ("data", "name")

    def __init__(self, name: str, data: bytes = b"") -> None:
        if len(name) > 8:
            raise ValueError(f"Lump name too long (max 8 chars): {name!r}")
        self.name = name.upper()
        self.data = data

    def __repr__(self) -> str:
        return f"<WriterEntry {self.name!r} {len(self.data)} bytes>"


class WadWriter:
    """Create, modify, and write WAD files.

    Basic usage::

        writer = WadWriter(WadType.PWAD)
        writer.add_lump("PLAYPAL", palette_bytes)
        writer.add_marker("MAP01")
        writer.add_lump("THINGS", things_bytes)
        writer.save("output.wad")

    Round-trip from existing WAD::

        with WadFile("DOOM2.WAD") as wad:
            writer = WadWriter.from_wad(wad)
            writer.replace_lump("ENDOOM", new_endoom_bytes)
            writer.save("modified.wad")
    """

    def __init__(self, wad_type: WadType = WadType.PWAD) -> None:
        self.wad_type = wad_type
        self.lumps: list[WriterEntry] = []

    @classmethod
    def from_wad(cls, wad: WadFile) -> WadWriter:
        """Create a writer pre-populated with all lumps from an existing WAD.

        Reads each lump's raw bytes from the file, making the writer
        independent of the original file descriptor.
        """
        writer = cls(wad.wad_type)
        for entry in wad.directory:
            if entry.size > 0:
                wad.fd.seek(entry.offset)
                data = wad.fd.read(entry.size)
            else:
                data = b""
            writer.lumps.append(WriterEntry(entry.name, data))
        return writer

    # -- Lump manipulation ---------------------------------------------------

    def add_lump(self, name: str, data: bytes = b"") -> int:
        """Append a lump. Returns its index."""
        entry = WriterEntry(name, data)
        self.lumps.append(entry)
        return len(self.lumps) - 1

    def add_marker(self, name: str) -> int:
        """Append a zero-length marker lump. Returns its index."""
        return self.add_lump(name, b"")

    def insert_lump(self, index: int, name: str, data: bytes = b"") -> None:
        """Insert a lump at *index*, shifting subsequent lumps right."""
        self.lumps.insert(index, WriterEntry(name, data))

    def replace_lump(self, name: str, data: bytes, *, occurrence: int = 0) -> bool:
        """Replace the *occurrence*-th lump named *name*. Returns True if found."""
        upper = name.upper()
        seen = 0
        for i, entry in enumerate(self.lumps):
            if entry.name == upper:
                if seen == occurrence:
                    self.lumps[i] = WriterEntry(upper, data)
                    return True
                seen += 1
        return False

    def remove_lump(self, name: str, *, occurrence: int = 0) -> bool:
        """Remove the *occurrence*-th lump named *name*. Returns True if found."""
        upper = name.upper()
        seen = 0
        for i, entry in enumerate(self.lumps):
            if entry.name == upper:
                if seen == occurrence:
                    del self.lumps[i]
                    return True
                seen += 1
        return False

    def find_lump(self, name: str, *, start: int = 0) -> int:
        """Return index of first lump named *name* at or after *start*, or -1."""
        upper = name.upper()
        for i in range(start, len(self.lumps)):
            if self.lumps[i].name == upper:
                return i
        return -1

    def get_lump(self, name: str, *, occurrence: int = 0) -> bytes | None:
        """Return the raw data of the *occurrence*-th lump named *name*, or None."""
        upper = name.upper()
        seen = 0
        for entry in self.lumps:
            if entry.name == upper:
                if seen == occurrence:
                    return entry.data
                seen += 1
        return None

    @property
    def lump_count(self) -> int:
        return len(self.lumps)

    @property
    def lump_names(self) -> list[str]:
        """Return the ordered list of lump names."""
        return [e.name for e in self.lumps]

    # -- Namespace helpers ---------------------------------------------------

    def _find_namespace(self, start_marker: str, end_marker: str) -> tuple[int, int]:
        """Return (start_idx, end_idx) for a namespace block, or (-1, -1)."""
        s = self.find_lump(start_marker)
        if s == -1:
            return (-1, -1)
        e = self.find_lump(end_marker, start=s + 1)
        if e == -1:
            return (-1, -1)
        return (s, e)

    def add_flat(self, name: str, data: bytes) -> None:
        """Add a flat inside the F_START/F_END namespace.

        Creates the namespace markers if they don't exist yet.
        """
        s, e = self._find_namespace("F_START", "F_END")
        if s == -1:
            self.add_marker("F_START")
            self.add_lump(name, data)
            self.add_marker("F_END")
        else:
            self.insert_lump(e, name, data)

    def add_sprite(self, name: str, data: bytes) -> None:
        """Add a sprite inside the S_START/S_END namespace.

        Creates the namespace markers if they don't exist yet.
        """
        s, e = self._find_namespace("S_START", "S_END")
        if s == -1:
            self.add_marker("S_START")
            self.add_lump(name, data)
            self.add_marker("S_END")
        else:
            self.insert_lump(e, name, data)

    def add_patch(self, name: str, data: bytes) -> None:
        """Add a patch inside the P_START/P_END namespace.

        Creates the namespace markers if they don't exist yet.
        """
        s, e = self._find_namespace("P_START", "P_END")
        if s == -1:
            self.add_marker("P_START")
            self.add_lump(name, data)
            self.add_marker("P_END")
        else:
            self.insert_lump(e, name, data)

    # -- Typed lump builders --------------------------------------------------

    def add_typed_lump(self, name: str, items: list[Serializable]) -> int:
        """Serialize a list of typed items and add as a single lump.

        Each item must have a ``to_bytes()`` method (e.g. ``Thing``,
        ``Vertex``, ``LineDefinition``, etc.).
        """
        data = b"".join(item.to_bytes() for item in items)
        return self.add_lump(name, data)

    def insert_typed_lump(self, index: int, name: str, items: list[Serializable]) -> None:
        """Serialize a list of typed items and insert at *index*."""
        data = b"".join(item.to_bytes() for item in items)
        self.insert_lump(index, name, data)

    def add_map(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        name: str,
        *,
        things: list[Serializable] | None = None,
        vertices: list[Serializable] | None = None,
        linedefs: list[Serializable] | None = None,
        sidedefs: list[Serializable] | None = None,
        sectors: list[Serializable] | None = None,
        segs: list[Serializable] | None = None,
        ssectors: list[Serializable] | None = None,
        nodes: list[Serializable] | None = None,
        reject: bytes | None = None,
        blockmap: bytes | None = None,
        behavior: bytes | None = None,
    ) -> int:
        """Add a complete map with all its sub-lumps.

        Returns the index of the map marker lump.  Each parameter accepts
        a list of typed items (``Thing``, ``Vertex``, etc.) that will be
        serialized, or raw bytes for ``reject`` / ``blockmap`` / ``behavior``.

        Example::

            writer.add_map(
                "MAP01",
                things=[Thing(0, 0, 0, 1, Flags(7))],
                vertices=[Vertex(0, 0), Vertex(64, 0), Vertex(64, 64), Vertex(0, 64)],
                linedefs=[...],
                sidedefs=[...],
                sectors=[...],
            )
        """
        marker_idx = self.add_marker(name)

        # Standard Doom map lump order
        map_lumps: list[tuple[str, list[Serializable] | None, bytes | None]] = [
            ("THINGS", things, None),
            ("LINEDEFS", linedefs, None),
            ("SIDEDEFS", sidedefs, None),
            ("VERTEXES", vertices, None),
            ("SEGS", segs, None),
            ("SSECTORS", ssectors, None),
            ("NODES", nodes, None),
            ("SECTORS", sectors, None),
            ("REJECT", None, reject),
            ("BLOCKMAP", None, blockmap),
        ]

        for lump_name, typed_items, raw_data in map_lumps:
            if typed_items is not None:
                self.add_typed_lump(lump_name, typed_items)
            elif raw_data is not None:
                self.add_lump(lump_name, raw_data)
            else:
                # Empty lump — still required by some engines
                self.add_lump(lump_name, b"")

        # Hexen BEHAVIOR lump (optional — marks map as Hexen format)
        if behavior is not None:
            self.add_lump("BEHAVIOR", behavior)

        return marker_idx

    # -- Serialisation -------------------------------------------------------

    def to_bytes(self) -> bytes:
        """Serialize the entire WAD to a byte string.

        Layout: header (12 bytes) + lump data + directory.
        """
        magic = self.wad_type.name.encode("ascii")

        # Accumulate lump data and record directory info
        lump_blob = bytearray()
        dir_entries: list[tuple[int, int, str]] = []  # (offset, size, name)
        offset = _HEADER_SIZE

        for entry in self.lumps:
            size = len(entry.data)
            if size > 0:
                dir_entries.append((offset, size, entry.name))
                lump_blob.extend(entry.data)
                offset += size
            else:
                # Zero-size marker — offset points to current position
                dir_entries.append((offset, 0, entry.name))

        dir_offset = _HEADER_SIZE + len(lump_blob)

        # Header
        header = pack(HEADER_FORMAT, magic, len(self.lumps), dir_offset)

        # Directory
        dir_bytes = bytearray()
        for off, size, name in dir_entries:
            dir_bytes.extend(pack("<II8s", off, size, _encode_name(name)))

        return bytes(header) + bytes(lump_blob) + bytes(dir_bytes)

    def save(self, filename: str) -> None:
        """Write the WAD to *filename* atomically.

        Data is first written to a temporary file in the same directory, then
        renamed over the target with ``os.replace()``.  If the write fails the
        original file is left untouched.
        """
        data = self.to_bytes()
        dir_path = os.path.dirname(os.path.abspath(filename))
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_path, filename)
        except Exception:
            os.unlink(tmp_path)
            raise

    # -- Dunder helpers ------------------------------------------------------

    def __len__(self) -> int:
        return len(self.lumps)

    def __repr__(self) -> str:
        return f"<WadWriter {self.wad_type.name} {len(self.lumps)} lumps>"
