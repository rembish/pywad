"""Tests for the WAD FUSE filesystem layer.

These test the WadFS virtual tree and operations without actually mounting.
"""

from __future__ import annotations

import os
import struct
import tempfile

import pytest

from wadlib.archive import WadArchive
from wadlib.lumps.sound import encode_dmx

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


try:
    from wadlib.fuse import WadFS, _DirNode

    HAS_FUSE = True
except (ImportError, OSError):
    HAS_FUSE = False

pytestmark = pytest.mark.skipif(not HAS_FUSE, reason="fusepy/libfuse not available")


def _make_test_wad() -> str:
    """Create a small test WAD with known contents."""
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        path = f.name

    with WadArchive(path, "w") as wad:
        # Palette (needed for image conversion) — 14 copies of a greyscale ramp
        single_pal = b""
        for i in range(256):
            single_pal += bytes([i, i, i])
        wad.writestr("PLAYPAL", single_pal * 14, validate=False)

        # A flat
        wad.writemarker("F_START")
        wad.writestr("FLAT01", b"\x80" * 4096, validate=False)
        wad.writemarker("F_END")

        # A sound
        dmx = encode_dmx(b"\x80" * 100, rate=11025)
        wad.writestr("DSPISTOL", dmx, validate=False)

        # A map
        wad.writemarker("MAP01")
        wad.writestr("THINGS", b"\x00" * 20, validate=False)
        wad.writestr("LINEDEFS", b"\x00" * 14, validate=False)
        wad.writestr("SIDEDEFS", b"\x00" * 30, validate=False)
        wad.writestr("VERTEXES", b"\x00" * 8, validate=False)
        wad.writestr("SECTORS", b"\x00" * 26, validate=False)

    return path


# ---------------------------------------------------------------------------
# Virtual tree structure
# ---------------------------------------------------------------------------


class TestVirtualTree:
    def test_root_has_subdirectories(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            root = fs._root
            assert isinstance(root, _DirNode)
            for d in ("lumps", "flats", "sprites", "sounds", "music", "maps", "patches"):
                assert d in root.children
                assert isinstance(root.children[d], _DirNode)
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_lumps_dir_contains_all_lumps(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            lumps_dir = fs._root.children["lumps"]
            assert isinstance(lumps_dir, _DirNode)
            names = list(lumps_dir.children.keys())
            assert "PLAYPAL.lmp" in names
            assert "FLAT01.lmp" in names
            assert "DSPISTOL.lmp" in names
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_flats_dir_has_png(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            flats_dir = fs._root.children["flats"]
            assert isinstance(flats_dir, _DirNode)
            assert "FLAT01.png" in flats_dir.children
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_sounds_dir_has_wav(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            sounds_dir = fs._root.children["sounds"]
            assert isinstance(sounds_dir, _DirNode)
            assert "DSPISTOL.wav" in sounds_dir.children
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_maps_dir_has_map_subdir(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            maps_dir = fs._root.children["maps"]
            assert isinstance(maps_dir, _DirNode)
            assert "MAP01" in maps_dir.children
            map01 = maps_dir.children["MAP01"]
            assert isinstance(map01, _DirNode)
            assert "THINGS.lmp" in map01.children
            fs._wad.close()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# FUSE operations — getattr
# ---------------------------------------------------------------------------


class TestGetattr:
    def test_root_is_dir(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            attrs = fs.getattr("/")
            assert attrs["st_mode"] & 0o170000 == 0o040000  # S_IFDIR
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_subdir_is_dir(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            attrs = fs.getattr("/lumps")
            assert attrs["st_mode"] & 0o170000 == 0o040000
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_file_is_regular(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            attrs = fs.getattr("/sounds/DSPISTOL.wav")
            assert attrs["st_mode"] & 0o170000 == 0o100000  # S_IFREG
            assert attrs["st_size"] > 0
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_nonexistent_raises(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            from fuse import FuseOSError

            with pytest.raises(FuseOSError):
                fs.getattr("/nonexistent")
            fs._wad.close()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# FUSE operations — readdir
# ---------------------------------------------------------------------------


class TestReaddir:
    def test_root_listing(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            entries = fs.readdir("/", 0)
            assert "." in entries
            assert ".." in entries
            assert "lumps" in entries
            assert "flats" in entries
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_sounds_listing(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            entries = fs.readdir("/sounds", 0)
            assert "DSPISTOL.wav" in entries
            fs._wad.close()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# FUSE operations — read
# ---------------------------------------------------------------------------


class TestRead:
    def test_read_wav(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fh = fs.open("/sounds/DSPISTOL.wav", 0)
            data = fs.read("/sounds/DSPISTOL.wav", 4, 0, fh)
            assert data == b"RIFF"
            fs.release("/sounds/DSPISTOL.wav", fh)
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_read_raw_lump(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fh = fs.open("/lumps/FLAT01.lmp", 0)
            data = fs.read("/lumps/FLAT01.lmp", 4096, 0, fh)
            assert len(data) == 4096
            assert data == b"\x80" * 4096
            fs.release("/lumps/FLAT01.lmp", fh)
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_read_flat_png(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fh = fs.open("/flats/FLAT01.png", 0)
            data = fs.read("/flats/FLAT01.png", 8, 0, fh)
            # PNG magic bytes
            assert data[:4] == b"\x89PNG"
            fs.release("/flats/FLAT01.png", fh)
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_read_map_lump(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fh = fs.open("/maps/MAP01/THINGS.lmp", 0)
            data = fs.read("/maps/MAP01/THINGS.lmp", 20, 0, fh)
            assert len(data) == 20
            fs.release("/maps/MAP01/THINGS.lmp", fh)
            fs._wad.close()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# FUSE operations — write
# ---------------------------------------------------------------------------


class TestWrite:
    def test_create_and_write(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fh = fs.create("/lumps/NEWLUMP.lmp", 0o644)
            written = fs.write("/lumps/NEWLUMP.lmp", b"hello world", 0, fh)
            assert written == 11
            fs.flush("/lumps/NEWLUMP.lmp", fh)
            fs.release("/lumps/NEWLUMP.lmp", fh)

            # Should be in pending writes
            assert "NEWLUMP" in fs._pending_writes
            assert fs._pending_writes["NEWLUMP"] == b"hello world"
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_wav_auto_conversion(self) -> None:
        """WAV written to sounds/ should be converted to DMX."""
        path = _make_test_wad()
        try:
            fs = WadFS(path)

            # Build a tiny WAV
            pcm = b"\x80" * 50
            wav = struct.pack("<4sI4s", b"RIFF", 36 + len(pcm), b"WAVE")
            wav += struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, 11025, 11025, 1, 8)
            wav += struct.pack("<4sI", b"data", len(pcm)) + pcm

            fh = fs.create("/sounds/NEWSND.wav", 0o644)
            fs.write("/sounds/NEWSND.wav", wav, 0, fh)
            fs.flush("/sounds/NEWSND.wav", fh)
            fs.release("/sounds/NEWSND.wav", fh)

            # Should be DMX format, not WAV
            dmx = fs._pending_writes["NEWSND"]
            fmt = struct.unpack("<H", dmx[:2])[0]
            assert fmt == 3  # DMX format marker
            fs._wad.close()
        finally:
            os.unlink(path)

    def test_unlink(self) -> None:
        path = _make_test_wad()
        try:
            fs = WadFS(path)
            fs.unlink("/sounds/DSPISTOL.wav")
            assert "DSPISTOL" in fs._pending_deletes

            # Should no longer appear in listing
            entries = fs.readdir("/sounds", 0)
            assert "DSPISTOL.wav" not in entries
            fs._wad.close()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Real WAD tree
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealWad:
    def test_freedoom2_tree(self) -> None:
        fs = WadFS(FREEDOOM2, writable=False)
        root = fs._root
        assert isinstance(root, _DirNode)

        # Should have lots of flats
        flats = root.children["flats"]
        assert isinstance(flats, _DirNode)
        assert len(flats.children) > 50

        # Should have sprites
        sprites = root.children["sprites"]
        assert isinstance(sprites, _DirNode)
        assert len(sprites.children) > 100

        # Should have maps
        maps = root.children["maps"]
        assert isinstance(maps, _DirNode)
        assert "MAP01" in maps.children

        # Should have sounds
        sounds = root.children["sounds"]
        assert isinstance(sounds, _DirNode)
        assert len(sounds.children) > 10

        # Should have music
        music = root.children["music"]
        assert isinstance(music, _DirNode)
        assert len(music.children) > 10

        fs._wad.close()

    def test_read_freedoom2_sound(self) -> None:
        fs = WadFS(FREEDOOM2, writable=False)
        entries = fs.readdir("/sounds", 0)
        # Pick a sound and read it
        wav_name = next(e for e in entries if e.endswith(".wav"))
        fh = fs.open(f"/sounds/{wav_name}", 0)
        data = fs.read(f"/sounds/{wav_name}", 4, 0, fh)
        assert data == b"RIFF"
        fs.release(f"/sounds/{wav_name}", fh)
        fs._wad.close()

    def test_read_freedoom2_music(self) -> None:
        fs = WadFS(FREEDOOM2, writable=False)
        entries = fs.readdir("/music", 0)
        mid_name = next(e for e in entries if e.endswith(".mid"))
        fh = fs.open(f"/music/{mid_name}", 0)
        data = fs.read(f"/music/{mid_name}", 4, 0, fh)
        assert data == b"MThd"
        fs.release(f"/music/{mid_name}", fh)
        fs._wad.close()
