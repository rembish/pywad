"""Unified archive interface for WAD files — modelled after ``zipfile.ZipFile``.

Provides a single ``WadArchive`` class that handles reading, writing, and
appending to WAD files with a familiar Pythonic API::

    # Read
    with WadArchive("DOOM2.WAD") as wad:
        print(wad.namelist())
        data = wad.read("PLAYPAL")

    # Write
    with WadArchive("patch.wad", "w") as wad:
        wad.writestr("DEHACKED", deh_bytes)

    # Append (read-modify-write)
    with WadArchive("mod.wad", "a") as wad:
        wad.writestr("PLAYPAL", new_palette)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, overload

from .enums import WadType
from .wad import WadFile
from .writer import WadWriter


@dataclass(frozen=True)
class LumpInfo:
    """Metadata for a single lump inside a WAD archive (analogous to ``ZipInfo``)."""

    name: str
    size: int
    index: int

    def __repr__(self) -> str:
        return f"<LumpInfo {self.name!r} {self.size} bytes>"


class WadArchive:
    """Unified read/write interface for WAD files.

    Modes:

    ``"r"``  Read an existing WAD.  Write operations raise ``ValueError``.
    ``"w"``  Create a new WAD from scratch.  Read operations raise ``ValueError``.
    ``"a"``  Open an existing WAD for modification (read-modify-write on close).

    In all modes the object acts as a context manager.  In ``"w"`` and ``"a"``
    modes, the WAD is written on ``.close()`` (or when the ``with`` block exits).
    """

    def __init__(
        self,
        file: str,
        mode: Literal["r", "w", "a"] = "r",
        wad_type: WadType = WadType.PWAD,
    ) -> None:
        if mode not in ("r", "w", "a"):
            raise ValueError(f"Invalid mode: {mode!r} (expected 'r', 'w', or 'a')")

        self._filename: str = file
        self._mode: str = mode
        self._closed: bool = False

        if mode == "r":
            self._reader: WadFile | None = WadFile(file)
            self._writer: WadWriter | None = None
        elif mode == "w":
            self._reader = None
            self._writer = WadWriter(wad_type)
        else:  # "a"
            reader = WadFile(file)
            self._writer = WadWriter.from_wad(reader)
            reader.close()
            self._reader = None

    # -- Properties -----------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def wad_type(self) -> WadType:
        if self._reader is not None:
            return self._reader.wad_type
        assert self._writer is not None
        return self._writer.wad_type

    # -- Context manager ------------------------------------------------------

    def __enter__(self) -> WadArchive:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def close(self) -> None:
        """Flush pending writes (if writable) and release resources."""
        if self._closed:
            return
        self._closed = True
        if self._mode in ("w", "a") and self._writer is not None:
            self._writer.save(self._filename)
        if self._reader is not None:
            self._reader.close()

    # -- Helpers --------------------------------------------------------------

    def _check_readable(self) -> None:
        if self._closed:
            raise ValueError("I/O operation on closed archive")
        if self._mode == "w":
            raise ValueError("read operation on write-only archive")

    def _check_writable(self) -> None:
        if self._closed:
            raise ValueError("I/O operation on closed archive")
        if self._mode == "r":
            raise ValueError("write operation on read-only archive")

    # -- Read interface -------------------------------------------------------

    def namelist(self) -> list[str]:
        """Return a list of lump names in directory order."""
        self._check_readable()
        if self._reader is not None:
            return [e.name for e in self._reader.directory]
        assert self._writer is not None
        return self._writer.lump_names

    def infolist(self) -> list[LumpInfo]:
        """Return a list of ``LumpInfo`` objects for every lump."""
        self._check_readable()
        if self._reader is not None:
            return [
                LumpInfo(name=e.name, size=e.size, index=i)
                for i, e in enumerate(self._reader.directory)
            ]
        assert self._writer is not None
        return [
            LumpInfo(name=e.name, size=len(e.data), index=i)
            for i, e in enumerate(self._writer._lumps)
        ]

    def getinfo(self, name: str) -> LumpInfo:
        """Return a ``LumpInfo`` for the named lump.

        Raises ``KeyError`` if the lump does not exist.
        """
        upper = name.upper()
        for info in self.infolist():
            if info.name == upper:
                return info
        raise KeyError(name)

    def read(self, name: str) -> bytes:
        """Return the raw bytes of the named lump.

        Raises ``KeyError`` if the lump does not exist.
        """
        self._check_readable()
        upper = name.upper()
        if self._reader is not None:
            for entry in self._reader.directory:
                if entry.name == upper:
                    if entry.size == 0:
                        return b""
                    self._reader.fd.seek(entry.offset)
                    return self._reader.fd.read(entry.size)
            raise KeyError(name)
        # append mode — data is in the writer
        assert self._writer is not None
        data = self._writer.get_lump(upper)
        if data is None:
            raise KeyError(name)
        return data

    def __contains__(self, name: str) -> bool:
        """Return ``True`` if a lump named *name* exists."""
        try:
            self._check_readable()
        except ValueError:
            return False
        upper = name.upper()
        if self._reader is not None:
            return any(e.name == upper for e in self._reader.directory)
        assert self._writer is not None
        return self._writer.find_lump(upper) != -1

    def __iter__(self) -> WadArchive:
        self._check_readable()
        self._iter_index = 0
        return self

    def __next__(self) -> LumpInfo:
        infos = self.infolist()
        if self._iter_index >= len(infos):
            raise StopIteration
        info = infos[self._iter_index]
        self._iter_index += 1
        return info

    def __len__(self) -> int:
        if self._reader is not None:
            return int(self._reader.directory_size)
        if self._writer is not None:
            return self._writer.lump_count
        return 0

    # -- Write interface ------------------------------------------------------

    def writestr(self, name: str, data: bytes) -> None:
        """Write raw bytes as a lump.  Appends to the directory."""
        self._check_writable()
        assert self._writer is not None
        self._writer.add_lump(name, data)

    @overload
    def write(self, filename: str) -> None: ...
    @overload
    def write(self, filename: str, arcname: str) -> None: ...

    def write(self, filename: str, arcname: str | None = None) -> None:
        """Read a file from disk and add it as a lump.

        *arcname* overrides the lump name (defaults to the uppercased basename
        without extension, truncated to 8 chars).
        """
        self._check_writable()
        assert self._writer is not None
        if arcname is None:
            base = os.path.basename(filename)
            arcname = os.path.splitext(base)[0].upper()[:8]
        with open(filename, "rb") as f:
            data = f.read()
        self._writer.add_lump(arcname, data)

    def writemarker(self, name: str) -> None:
        """Add a zero-length marker lump (e.g. ``MAP01``, ``F_START``)."""
        self._check_writable()
        assert self._writer is not None
        self._writer.add_marker(name)

    def remove(self, name: str) -> bool:
        """Remove the first lump named *name*.  Returns ``True`` if found."""
        self._check_writable()
        assert self._writer is not None
        return self._writer.remove_lump(name)

    def replace(self, name: str, data: bytes) -> bool:
        """Replace the first lump named *name*.  Returns ``True`` if found."""
        self._check_writable()
        assert self._writer is not None
        return self._writer.replace_lump(name, data)

    # -- Extract interface ----------------------------------------------------

    def extract(self, name: str, path: str = ".") -> str:
        """Extract a single lump to *path* as a raw ``.lmp`` file.

        Returns the full path of the written file.
        """
        self._check_readable()
        data = self.read(name)
        upper = name.upper()
        dest = os.path.join(path, f"{upper}.lmp")
        os.makedirs(path, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return dest

    def extractall(self, path: str = ".") -> list[str]:
        """Extract all lumps to *path* as raw ``.lmp`` files.

        Returns a list of written file paths.  Zero-length marker lumps are
        skipped.
        """
        self._check_readable()
        written: list[str] = []
        for info in self.infolist():
            if info.size == 0:
                continue
            written.append(self.extract(info.name, path))
        return written

    # -- Dunder ---------------------------------------------------------------

    def __repr__(self) -> str:
        state = "closed" if self._closed else self._mode
        return f"<WadArchive {self._filename!r} mode={state!r}>"
