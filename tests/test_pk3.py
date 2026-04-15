"""Tests for pk3 (ZIP) archive support and WAD<->pk3 conversion."""

from __future__ import annotations

import os
import tempfile

import pytest

from wadlib.archive import WadArchive
from wadlib.lumps.sound import encode_dmx
from wadlib.pk3 import Pk3Archive, Pk3Entry, pk3_to_wad, wad_to_pk3

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# Pk3Entry
# ---------------------------------------------------------------------------


class TestPk3Entry:
    def test_name(self) -> None:
        e = Pk3Entry(path="flats/FLOOR0_1.lmp", size=4096, compressed_size=100)
        assert e.name == "FLOOR0_1.lmp"

    def test_lump_name(self) -> None:
        e = Pk3Entry(path="flats/FLOOR0_1.lmp", size=4096, compressed_size=100)
        assert e.lump_name == "FLOOR0_1"

    def test_lump_name_truncated(self) -> None:
        e = Pk3Entry(path="lumps/TOOLONGNAME.lmp", size=10, compressed_size=10)
        assert len(e.lump_name) <= 8

    def test_category(self) -> None:
        assert Pk3Entry("flats/X.lmp", 0, 0).category == "flats"
        assert Pk3Entry("sprites/Y.lmp", 0, 0).category == "sprites"
        assert Pk3Entry("toplevel.lmp", 0, 0).category == ""

    def test_category_backslash(self) -> None:
        e = Pk3Entry("maps\\MAP01\\THINGS.lmp", 0, 0)
        assert e.category == "maps"


# ---------------------------------------------------------------------------
# Pk3Archive — basic operations
# ---------------------------------------------------------------------------


class TestPk3Archive:
    def test_create_and_read(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        try:
            with Pk3Archive(path, "w") as pk3:
                pk3.writestr("lumps/PLAYPAL.lmp", b"\x00" * 768)
                pk3.writestr("flats/FLOOR1.lmp", b"\x80" * 4096)

            with Pk3Archive(path, "r") as pk3:
                assert len(pk3) == 2
                names = pk3.namelist()
                assert "lumps/PLAYPAL.lmp" in names
                assert "flats/FLOOR1.lmp" in names
                assert pk3.read("lumps/PLAYPAL.lmp") == b"\x00" * 768
        finally:
            os.unlink(path)

    def test_infolist(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        try:
            with Pk3Archive(path, "w") as pk3:
                pk3.writestr("lumps/TEST.lmp", b"hello")

            with Pk3Archive(path, "r") as pk3:
                infos = pk3.infolist()
                assert len(infos) == 1
                assert infos[0].path == "lumps/TEST.lmp"
                assert infos[0].size == 5
        finally:
            os.unlink(path)

    def test_contains(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        try:
            with Pk3Archive(path, "w") as pk3:
                pk3.writestr("lumps/X.lmp", b"x")

            with Pk3Archive(path, "r") as pk3:
                assert "lumps/X.lmp" in pk3
                assert "lumps/Y.lmp" not in pk3
        finally:
            os.unlink(path)

    def test_repr(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        try:
            with Pk3Archive(path, "w") as pk3:
                assert "mode='w'" in repr(pk3)
        finally:
            os.unlink(path)

    def test_append_mode(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        try:
            with Pk3Archive(path, "w") as pk3:
                pk3.writestr("lumps/A.lmp", b"aaa")

            with Pk3Archive(path, "a") as pk3:
                pk3.writestr("lumps/B.lmp", b"bbb")

            with Pk3Archive(path, "r") as pk3:
                assert len(pk3) == 2
                assert pk3.read("lumps/A.lmp") == b"aaa"
                assert pk3.read("lumps/B.lmp") == b"bbb"
        finally:
            os.unlink(path)

    def test_write_file_from_disk(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".lmp", delete=False) as lmp:
            lmp.write(b"file_data")
            lmp_path = lmp.name

        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name

        try:
            with Pk3Archive(pk3_path, "w") as pk3:
                pk3.write(lmp_path, "lumps/FILELMP.lmp")

            with Pk3Archive(pk3_path, "r") as pk3:
                assert pk3.read("lumps/FILELMP.lmp") == b"file_data"
        finally:
            os.unlink(lmp_path)
            os.unlink(pk3_path)


# ---------------------------------------------------------------------------
# WAD -> pk3 conversion
# ---------------------------------------------------------------------------


def _make_test_wad() -> str:
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        path = f.name
    with WadArchive(path, "w") as wad:
        wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
        wad.writemarker("F_START")
        wad.writestr("FLAT01", b"\x80" * 4096, validate=False)
        wad.writemarker("F_END")
        wad.writemarker("S_START")
        wad.writestr("TROOA1", b"\x42" * 100, validate=False)
        wad.writemarker("S_END")
        dmx = encode_dmx(b"\x80" * 50)
        wad.writestr("DSPISTOL", dmx, validate=False)
        wad.writemarker("MAP01")
        wad.writestr("THINGS", b"\x00" * 20, validate=False)
        wad.writestr("LINEDEFS", b"\x00" * 14, validate=False)
    return path


class TestWadToPk3:
    def test_basic_conversion(self) -> None:
        wad_path = _make_test_wad()
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        try:
            wad_to_pk3(wad_path, pk3_path)

            with Pk3Archive(pk3_path, "r") as pk3:
                names = pk3.namelist()
                # Flats should be in flats/
                assert "flats/FLAT01.lmp" in names
                # Sprites in sprites/
                assert "sprites/TROOA1.lmp" in names
                # Other lumps in lumps/
                assert "lumps/PLAYPAL.lmp" in names
                assert "lumps/DSPISTOL.lmp" in names
                # Map data in maps/MAP01/
                assert "maps/MAP01/THINGS.lmp" in names
                assert "maps/MAP01/LINEDEFS.lmp" in names
                # Markers should NOT appear
                assert "lumps/F_START.lmp" not in names
                assert "lumps/MAP01.lmp" not in names

                # Data integrity
                assert pk3.read("flats/FLAT01.lmp") == b"\x80" * 4096
                assert pk3.read("sprites/TROOA1.lmp") == b"\x42" * 100
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)


class TestPk3ToWad:
    def test_round_trip(self) -> None:
        """WAD -> pk3 -> WAD should preserve lump data."""
        wad_path = _make_test_wad()
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad2_path = f.name

        try:
            wad_to_pk3(wad_path, pk3_path)
            pk3_to_wad(pk3_path, wad2_path)

            with WadArchive(wad2_path, "r") as wad:
                names = wad.namelist()
                # Should have PLAYPAL
                assert "PLAYPAL" in names
                assert wad.read("PLAYPAL") == b"\x00" * (768 * 14)
                # Should have flat namespace
                assert "F_START" in names
                assert "FLAT01" in names
                assert "F_END" in names
                assert wad.read("FLAT01") == b"\x80" * 4096
                # Should have map
                assert "MAP01" in names
                assert "THINGS" in names
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)
            os.unlink(wad2_path)


# ---------------------------------------------------------------------------
# Pk3Archive — resource API
# ---------------------------------------------------------------------------


class TestPk3ArchiveResourceApi:
    def _make_pk3(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        with Pk3Archive(path, "w") as pk3:
            pk3.writestr("sounds/DSPISTOL.lmp", b"snd1")
            pk3.writestr("sfx/DSGUNSHOT.lmp", b"snd2")
            pk3.writestr("music/D_RUNNIN.lmp", b"mus1")
            pk3.writestr("mus/D_INTER.lmp", b"mus2")
            pk3.writestr("sprites/TROOA1.lmp", b"spr1")
            pk3.writestr("flats/FLOOR0_1.lmp", b"flt1")
            pk3.writestr("patches/WALL00_1.lmp", b"pat1")
            pk3.writestr("graphics/TITLEPIC.lmp", b"gfx1")
            pk3.writestr("textures/BRICK7.lmp", b"tex1")
            pk3.writestr("lumps/PLAYPAL.lmp", b"lmp1")
        return path

    def test_sounds_canonical(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                s = pk3.sounds
                assert "DSPISTOL" in s
                assert s["DSPISTOL"] == b"snd1"
        finally:
            os.unlink(path)

    def test_sounds_alias(self) -> None:
        """sfx/ should normalize to sounds category."""
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                s = pk3.sounds
                # DSGUNSHOT is 9 chars; lump_name truncates to 8 → DSGUNSHO
                assert "DSGUNSHO" in s
                assert s["DSGUNSHO"] == b"snd2"
        finally:
            os.unlink(path)

    def test_music_canonical_and_alias(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                m = pk3.music
                assert "D_RUNNIN" in m
                assert "D_INTER" in m
        finally:
            os.unlink(path)

    def test_sprites(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert "TROOA1" in pk3.sprites
        finally:
            os.unlink(path)

    def test_flats(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert "FLOOR0_1" in pk3.flats
        finally:
            os.unlink(path)

    def test_patches(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert "WALL00_1" in pk3.patches
        finally:
            os.unlink(path)

    def test_graphics(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert "TITLEPIC" in pk3.graphics
        finally:
            os.unlink(path)

    def test_textures(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert "BRICK7" in pk3.textures
        finally:
            os.unlink(path)

    def test_find_resource(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                entry = pk3.find_resource("DSPISTOL")
                assert entry is not None
                assert entry.path == "sounds/DSPISTOL.lmp"
        finally:
            os.unlink(path)

    def test_find_resource_case_insensitive(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3.find_resource("dspistol") is not None
                assert pk3.find_resource("DsPiStOl") is not None
        finally:
            os.unlink(path)

    def test_find_resource_missing(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3.find_resource("NOTHERE") is None
        finally:
            os.unlink(path)

    def test_read_resource(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3.read_resource("DSPISTOL") == b"snd1"
        finally:
            os.unlink(path)

    def test_read_resource_missing(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3.read_resource("NOTHERE") is None
        finally:
            os.unlink(path)

    def test_empty_category(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                # No voxels in this archive
                from wadlib.pk3 import Pk3Archive as _A  # noqa: F401
                assert pk3._category_dict("voxels") == {}
        finally:
            os.unlink(path)


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealWadToPk3:
    def test_convert_freedoom2(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        try:
            wad_to_pk3(FREEDOOM2, pk3_path)
            with Pk3Archive(pk3_path, "r") as pk3:
                names = pk3.namelist()
                assert len(names) > 100
                # Should have organised flats, sprites, maps
                flat_count = sum(1 for n in names if n.startswith("flats/"))
                sprite_count = sum(1 for n in names if n.startswith("sprites/"))
                map_count = sum(1 for n in names if n.startswith("maps/"))
                assert flat_count > 50
                assert sprite_count > 100
                assert map_count > 0
        finally:
            os.unlink(pk3_path)
