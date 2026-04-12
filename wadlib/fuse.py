"""FUSE filesystem for WAD files — mount any WAD as a virtual directory.

Lumps are organised into typed subdirectories and auto-converted to/from
standard formats on access::

    wadmount DOOM2.WAD /mnt/doom2

    /mnt/doom2/
    +-- flats/FLOOR0_1.png        # 64x64 flat -> PNG on read
    +-- sprites/TROOA1.png         # picture -> PNG on read
    +-- sounds/DSPISTOL.wav        # DMX -> WAV on read
    +-- music/D_RUNNIN.mid         # MUS/MIDI -> MIDI on read
    +-- maps/MAP01/THINGS.lmp      # raw map data
    +-- lumps/PLAYPAL.lmp          # raw access to every lump

Writing is supported: drop a .wav into sounds/ and it becomes a DMX lump,
drop a .mid into music/ and it becomes MUS, etc.

Requires ``fusepy`` (``pip install wadlib[fuse]``).
"""

from __future__ import annotations

import errno
import stat
import time
from io import BytesIO
from typing import Any

from .lumps.flat import Flat, encode_flat
from .lumps.mid2mus import midi_to_mus
from .lumps.mus import Mus
from .lumps.ogg import MidiLump, Mp3Lump, OggLump
from .lumps.picture import Picture, encode_picture
from .lumps.playpal import Palette
from .lumps.sound import wav_to_dmx
from .wad import WadFile
from .writer import WadWriter

try:
    from fuse import FuseOSError, Operations
except ImportError as _exc:
    raise ImportError(
        "fusepy is required for WAD FUSE mounting. Install it with: pip install fusepy"
    ) from _exc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIR_ATTRS = {
    "st_mode": stat.S_IFDIR | 0o755,
    "st_nlink": 2,
}

_NOW = time.time()


def _file_attrs(size: int) -> dict[str, Any]:
    return {
        "st_mode": stat.S_IFREG | 0o644,
        "st_nlink": 1,
        "st_size": size,
        "st_ctime": _NOW,
        "st_mtime": _NOW,
        "st_atime": _NOW,
    }


# ---------------------------------------------------------------------------
# Virtual node types
# ---------------------------------------------------------------------------


class _VNode:
    """A node in the virtual filesystem tree."""


class _DirNode(_VNode):
    """A virtual directory."""

    def __init__(self) -> None:
        self.children: dict[str, _VNode] = {}


class _FileNode(_VNode):  # pylint: disable=too-few-public-methods
    """A virtual file with content generated on access."""

    def __init__(self, data_fn: Any, size: int) -> None:
        self.data_fn = data_fn  # callable() -> bytes
        self.size = size  # may be updated lazily on first access


class _WritableFileNode(_VNode):
    """A file that was written by the user (pending flush to WAD)."""

    def __init__(self, data: bytes) -> None:
        self.data = data


# ---------------------------------------------------------------------------
# WadFS — the FUSE Operations implementation
# ---------------------------------------------------------------------------


class WadFS(Operations):  # type: ignore[misc]
    """FUSE filesystem backed by a WAD file.

    Read-write: modifications are collected in memory and flushed to
    the WAD file on ``destroy()`` (unmount).
    """

    def __init__(self, wad_path: str, *, writable: bool = True) -> None:
        self._wad_path = wad_path
        self._writable = writable
        self._wad = WadFile(wad_path)
        self._palette: Palette | None = None
        if self._wad.playpal:
            self._palette = self._wad.playpal.get_palette(0)

        # Pending writes: virtual_path -> raw_lump_bytes
        self._pending_writes: dict[str, bytes] = {}
        # Pending deletes
        self._pending_deletes: set[str] = set()
        # Open file handles: fh -> BytesIO
        self._handles: dict[int, BytesIO] = {}
        self._next_fh = 1

        # Build the virtual tree
        self._root = _DirNode()
        self._build_tree()

    # -- Tree construction --------------------------------------------------

    def _build_tree(self) -> None:  # pylint: disable=too-many-branches
        root = self._root

        # Top-level directories
        for d in ("lumps", "flats", "sprites", "sounds", "music", "maps", "patches"):
            root.children[d] = _DirNode()

        lumps_dir = root.children["lumps"]
        assert isinstance(lumps_dir, _DirNode)
        flats_dir = root.children["flats"]
        assert isinstance(flats_dir, _DirNode)
        sprites_dir = root.children["sprites"]
        assert isinstance(sprites_dir, _DirNode)
        sounds_dir = root.children["sounds"]
        assert isinstance(sounds_dir, _DirNode)
        music_dir = root.children["music"]
        assert isinstance(music_dir, _DirNode)
        maps_dir = root.children["maps"]
        assert isinstance(maps_dir, _DirNode)
        patches_dir = root.children["patches"]
        assert isinstance(patches_dir, _DirNode)

        # All lumps as raw .lmp files
        for entry in self._wad.directory:
            data = self._read_raw(entry.name, entry.offset, entry.size)
            lumps_dir.children[f"{entry.name}.lmp"] = _FileNode(data, entry.size)

        # Flats -> PNG
        for name, flat in self._wad.flats.items():
            node = self._make_flat_node(name, flat)
            flats_dir.children[f"{name}.png"] = node

        # Sprites -> PNG
        for name, pic in self._wad.sprites.items():
            node = self._make_picture_node(name, pic)
            sprites_dir.children[f"{name}.png"] = node

        # Sounds -> WAV
        for name, snd in self._wad.sounds.items():
            wav_data = snd.to_wav()
            sounds_dir.children[f"{name}.wav"] = _FileNode(lambda d=wav_data: d, len(wav_data))

        # Music -> MIDI
        for name, mus in self._wad.music.items():
            if isinstance(mus, Mus):
                midi_data = mus.to_midi()
                music_dir.children[f"{name}.mid"] = _FileNode(lambda d=midi_data: d, len(midi_data))
            elif isinstance(mus, MidiLump):
                raw = mus.raw()
                music_dir.children[f"{name}.mid"] = _FileNode(lambda d=raw: d, len(raw))
            elif isinstance(mus, OggLump):
                raw = mus.raw()
                music_dir.children[f"{name}.ogg"] = _FileNode(lambda d=raw: d, len(raw))
            elif isinstance(mus, Mp3Lump):
                raw = mus.raw()
                music_dir.children[f"{name}.mp3"] = _FileNode(lambda d=raw: d, len(raw))

        # Maps -> subdirectories with raw lumps
        for m in self._wad.maps:
            map_dir = _DirNode()
            maps_dir.children[m.name] = map_dir
            # Gather map sub-lumps by scanning directory
            for lump_name, lump_obj in [
                ("THINGS", m.things),
                ("LINEDEFS", m.lines),
                ("SIDEDEFS", m.sidedefs),
                ("VERTEXES", m.vertices),
                ("SEGS", m.segs),
                ("SSECTORS", m.ssectors),
                ("NODES", m.nodes),
                ("SECTORS", m.sectors),
            ]:
                if lump_obj is not None and hasattr(lump_obj, "raw"):
                    raw = lump_obj.raw()
                    map_dir.children[f"{lump_name}.lmp"] = _FileNode(lambda d=raw: d, len(raw))
            if m.reject is not None:
                rdata = m.reject.to_bytes()
                map_dir.children["REJECT.lmp"] = _FileNode(lambda d=rdata: d, len(rdata))
            if m.blockmap is not None:
                bdata = m.blockmap.to_bytes()
                map_dir.children["BLOCKMAP.lmp"] = _FileNode(lambda d=bdata: d, len(bdata))

        # Patches (from PNAMES) -> PNG
        if self._wad.pnames:
            for pname in self._wad.pnames.names:
                patch_pic = self._wad.get_picture(pname)
                if patch_pic is not None:
                    node = self._make_picture_node(pname, patch_pic)
                    patches_dir.children[f"{pname}.png"] = node

    def _read_raw(self, name: str, offset: int, size: int) -> Any:
        """Return a callable that reads raw bytes from the WAD."""

        def _reader(_name: str = name, _off: int = offset, _sz: int = size) -> bytes:
            if _sz == 0:
                return b""
            self._wad.fd.seek(_off)
            return self._wad.fd.read(_sz)

        return _reader

    def _make_flat_node(self, name: str, flat: Flat) -> _FileNode:
        """Create a file node that decodes a flat to PNG on read."""

        def _gen(f: Flat = flat, p: Palette | None = self._palette) -> bytes:
            if p is None:
                return f.raw()
            img = f.decode(p)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        # Estimate size (actual PNG size varies; use raw + overhead)
        return _FileNode(_gen, 0)  # size=0 means compute on access

    def _make_picture_node(self, name: str, pic: Picture) -> _FileNode:
        """Create a file node that decodes a picture to PNG on read."""

        def _gen(p: Picture = pic, pal: Palette | None = self._palette) -> bytes:
            if pal is None:
                return p.raw()
            img = p.decode(pal)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        return _FileNode(_gen, 0)

    # -- Path resolution ----------------------------------------------------

    def _resolve(self, path: str) -> _VNode | None:
        """Resolve a path to a virtual node."""
        if path == "/":
            return self._root
        parts = path.strip("/").split("/")
        node: _VNode = self._root
        for part in parts:
            if not isinstance(node, _DirNode):
                return None
            node = node.children.get(part)  # type: ignore[assignment]
            if node is None:
                return None
        return node

    # -- FUSE operations (read) ---------------------------------------------

    def getattr(self, path: str, fh: int | None = None) -> dict[str, Any]:
        node = self._resolve(path)
        if node is None:
            raise FuseOSError(errno.ENOENT)
        if isinstance(node, _DirNode):
            return {**_DIR_ATTRS, "st_ctime": _NOW, "st_mtime": _NOW, "st_atime": _NOW}
        if isinstance(node, _WritableFileNode):
            return _file_attrs(len(node.data))
        if isinstance(node, _FileNode):
            if node.size == 0:
                # Compute actual size
                data = node.data_fn()
                node.size = len(data)
            return _file_attrs(node.size)
        raise FuseOSError(errno.ENOENT)

    def readdir(self, path: str, fh: int) -> list[str]:
        node = self._resolve(path)
        if not isinstance(node, _DirNode):
            raise FuseOSError(errno.ENOTDIR)
        return [".", "..", *node.children.keys()]

    def open(self, path: str, flags: int) -> int:
        node = self._resolve(path)
        if node is None:
            raise FuseOSError(errno.ENOENT)
        if isinstance(node, _FileNode):
            data = node.data_fn()
            node.size = len(data)
        elif isinstance(node, _WritableFileNode):
            data = node.data
        else:
            raise FuseOSError(errno.EISDIR)
        fh = self._next_fh
        self._next_fh += 1
        self._handles[fh] = BytesIO(data)
        return fh

    def read(self, path: str, size: int, offset: int, fh: int) -> bytes:
        bio = self._handles.get(fh)
        if bio is None:
            raise FuseOSError(errno.EBADF)
        bio.seek(offset)
        return bio.read(size)

    def release(self, path: str, fh: int) -> int:
        self._handles.pop(fh, None)
        return 0

    # -- FUSE operations (write) --------------------------------------------

    def create(self, path: str, mode: int, fi: object = None) -> int:
        if not self._writable:
            raise FuseOSError(errno.EROFS)

        parts = path.strip("/").split("/")
        if len(parts) < 2:
            raise FuseOSError(errno.EACCES)

        # Resolve parent directory
        parent_path = "/" + "/".join(parts[:-1])
        parent = self._resolve(parent_path)
        if not isinstance(parent, _DirNode):
            raise FuseOSError(errno.ENOENT)

        filename = parts[-1]
        node = _WritableFileNode(b"")
        parent.children[filename] = node

        fh = self._next_fh
        self._next_fh += 1
        self._handles[fh] = BytesIO()
        return fh

    def write(self, path: str, data: bytes, offset: int, fh: int) -> int:
        if not self._writable:
            raise FuseOSError(errno.EROFS)
        bio = self._handles.get(fh)
        if bio is None:
            raise FuseOSError(errno.EBADF)
        bio.seek(offset)
        bio.write(data)
        return len(data)

    def truncate(self, path: str, length: int, fh: int | None = None) -> None:
        if fh and fh in self._handles:
            self._handles[fh].truncate(length)

    def flush(self, path: str, fh: int) -> int:
        bio = self._handles.get(fh)
        if bio is None:
            return 0

        # Update the node with written data
        node = self._resolve(path)
        if isinstance(node, _WritableFileNode):
            bio.seek(0)
            raw = bio.read()
            node.data = raw

            # Convert based on directory and extension
            parts = path.strip("/").split("/")
            if len(parts) >= 2:
                category = parts[0]
                filename = parts[-1]
                lump_name = filename.rsplit(".", 1)[0].upper()[:8]
                lump_data = self._convert_for_write(category, filename, raw)
                self._pending_writes[lump_name] = lump_data

        return 0

    def unlink(self, path: str) -> None:
        if not self._writable:
            raise FuseOSError(errno.EROFS)

        parts = path.strip("/").split("/")
        if len(parts) < 2:
            raise FuseOSError(errno.EACCES)

        parent_path = "/" + "/".join(parts[:-1])
        parent = self._resolve(parent_path)
        if not isinstance(parent, _DirNode):
            raise FuseOSError(errno.ENOENT)

        filename = parts[-1]
        if filename not in parent.children:
            raise FuseOSError(errno.ENOENT)

        del parent.children[filename]
        lump_name = filename.rsplit(".", 1)[0].upper()[:8]
        self._pending_deletes.add(lump_name)

    # -- Format conversion for writes --------------------------------------

    def _convert_for_write(self, category: str, filename: str, data: bytes) -> bytes:
        """Convert user-provided file data to WAD lump format based on category."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if category == "sounds" and ext == "wav":
            return wav_to_dmx(data)

        if category == "music" and ext == "mid":
            return midi_to_mus(data)

        if category == "flats" and ext == "png" and self._palette:
            from PIL import Image

            img = Image.open(BytesIO(data))
            return encode_flat(img, self._palette)

        if category in ("sprites", "patches") and ext == "png" and self._palette:
            from PIL import Image

            img = Image.open(BytesIO(data))
            return encode_picture(img, self._palette)

        # For lumps/ or unknown formats, store raw
        return data

    # -- Lifecycle ----------------------------------------------------------

    def destroy(self, path: str) -> None:
        """Called on unmount — flush all pending writes to the WAD."""
        if self._writable and (self._pending_writes or self._pending_deletes):
            writer = WadWriter.from_wad(self._wad)

            for name in self._pending_deletes:
                writer.remove_lump(name)

            for name, data in self._pending_writes.items():
                if not writer.replace_lump(name, data):
                    writer.add_lump(name, data)

            writer.save(self._wad_path)

        self._wad.close()


def mount(
    wad_path: str, mountpoint: str, *, foreground: bool = True, writable: bool = True
) -> None:
    """Mount a WAD file as a FUSE filesystem.

    Parameters:
        wad_path:    Path to the WAD file.
        mountpoint:  Directory to mount on (must exist).
        foreground:  Run in foreground (default True).
        writable:    Allow write operations (default True).
    """
    from fuse import FUSE

    fs = WadFS(wad_path, writable=writable)
    FUSE(fs, mountpoint, foreground=foreground, nothreads=True, allow_other=False)
