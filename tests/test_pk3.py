"""Tests for pk3 (ZIP) archive support and WAD<->pk3 conversion."""

from __future__ import annotations

import os
import tempfile
from io import BytesIO

import pytest
from PIL import Image
from PIL.Image import Image as PilImage

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

    def test_find_resources_single_match(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                results = pk3.find_resources("DSPISTOL")
                assert len(results) == 1
                assert results[0].path == "sounds/DSPISTOL.lmp"
        finally:
            os.unlink(path)

    def test_find_resources_missing_returns_empty(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3.find_resources("NOTHERE") == []
        finally:
            os.unlink(path)

    def test_find_resources_collision(self) -> None:
        """Two entries that collide under the same lump name are both returned."""
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            collision_path = f.name
        try:
            with Pk3Archive(collision_path, "w") as pk3:
                # Both truncate to lump name "LONGNAME" (8 chars)
                pk3.writestr("sprites/LONGNAME_A.lmp", b"first")
                pk3.writestr("sprites/LONGNAME_B.lmp", b"second")
            with Pk3Archive(collision_path, "r") as pk3:
                results = pk3.find_resources("LONGNAME")
                assert len(results) == 2
                paths = {e.path for e in results}
                assert "sprites/LONGNAME_A.lmp" in paths
                assert "sprites/LONGNAME_B.lmp" in paths
        finally:
            os.unlink(collision_path)

    def test_find_resources_case_insensitive(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert len(pk3.find_resources("dspistol")) == 1
                assert len(pk3.find_resources("DsPiStOl")) == 1
        finally:
            os.unlink(path)

    def test_empty_category(self) -> None:
        path = self._make_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                assert pk3._category_dict("voxels") == {}
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Pk3Archive — image API
# ---------------------------------------------------------------------------


def _png_bytes(width: int = 2, height: int = 2, color: str = "RGB") -> bytes:
    """Create a tiny in-memory PNG using Pillow."""
    img = Image.new(color, (width, height), (128, 64, 32) if color == "RGB" else 128)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestPk3ArchiveImageApi:
    def _make_image_pk3(self) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            path = f.name
        flat_png = _png_bytes()
        sprite_png = _png_bytes(4, 8)
        patch_png = _png_bytes(8, 8)
        tex_png = _png_bytes(16, 16)
        with Pk3Archive(path, "w") as pk3:
            pk3.writestr("flats/FLOOR1.png", flat_png)
            pk3.writestr("sprites/TROOA1.png", sprite_png)
            pk3.writestr("patches/WALL01.png", patch_png)
            pk3.writestr("textures/BRICK1.png", tex_png)
        return path

    def test_flat_images_returns_dict(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                imgs = pk3.flat_images
                assert "FLOOR1" in imgs
        finally:
            os.unlink(path)

    def test_flat_image_dimensions(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                img = pk3.flat_images["FLOOR1"]
                assert img.size == (2, 2)
        finally:
            os.unlink(path)

    def test_sprite_images(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                imgs = pk3.sprite_images
                assert "TROOA1" in imgs
                assert imgs["TROOA1"].size == (4, 8)
        finally:
            os.unlink(path)

    def test_patch_images(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                imgs = pk3.patch_images
                assert "WALL01" in imgs
                assert imgs["WALL01"].size == (8, 8)
        finally:
            os.unlink(path)

    def test_texture_images(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                imgs = pk3.texture_images
                assert "BRICK1" in imgs
                assert imgs["BRICK1"].size == (16, 16)
        finally:
            os.unlink(path)

    def test_empty_category_images(self) -> None:
        path = self._make_image_pk3()
        try:
            with Pk3Archive(path, "r") as pk3:
                # No graphics/ entries in this archive
                assert pk3._category_images("graphics") == {}
        finally:
            os.unlink(path)

    def test_decode_image_static(self) -> None:
        data = _png_bytes(3, 3)
        img = Pk3Archive._decode_image(data)
        assert isinstance(img, PilImage)
        assert img.size == (3, 3)


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


# ---------------------------------------------------------------------------
# WAD/PK3 conversion edge cases
# ---------------------------------------------------------------------------


class TestWadToPk3EdgeCases:
    """Conversion edge cases: duplicates, name truncation, alias preservation."""

    def _make_wad_with_duplicate(self) -> str:
        """WAD containing two lumps with the same name in a namespace."""
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with WadArchive(path, "w") as wad:
            wad.writemarker("F_START")
            wad.writestr("FLAT01", b"\xaa" * 4096, validate=False)
            wad.writestr("FLAT01", b"\xbb" * 4096, validate=False)  # duplicate
            wad.writemarker("F_END")
        return path

    def _make_wad_with_long_names(self) -> str:
        """WAD where two different flat names truncate to the same 8-char lump name."""
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with WadArchive(path, "w") as wad:
            wad.writemarker("F_START")
            # Both "FLOORTILE" and "FLOORTILE" already collide, but here we use
            # lump names that are exactly 8 chars — no truncation needed in WAD.
            wad.writestr("FLAT0001", b"\x11" * 4096, validate=False)
            wad.writestr("FLAT0002", b"\x22" * 4096, validate=False)
            wad.writemarker("F_END")
            wad.writemarker("S_START")
            wad.writestr("TROOA1", b"\x33" * 100, validate=False)
            wad.writemarker("S_END")
            wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
        return path

    def test_duplicate_flat_in_wad_does_not_crash(self) -> None:
        """WAD→PK3 conversion with duplicate flat names must not crash."""
        wad_path = self._make_wad_with_duplicate()
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        try:
            wad_to_pk3(wad_path, pk3_path)
            with Pk3Archive(pk3_path, "r") as pk3:
                names = pk3.namelist()
                flat_entries = [n for n in names if n.startswith("flats/")]
                # Both duplicates or at least one must be present
                assert len(flat_entries) >= 1
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)

    def test_namespace_aliases_preserved_through_round_trip(self) -> None:
        """Flats and sprites end up in flats/ and sprites/ after WAD→PK3→WAD."""
        wad_path = self._make_wad_with_long_names()
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad2_path = f.name
        try:
            wad_to_pk3(wad_path, pk3_path)
            with Pk3Archive(pk3_path, "r") as pk3:
                names = pk3.namelist()
                assert any(n.startswith("flats/") for n in names)
                assert any(n.startswith("sprites/") for n in names)
                assert any(n.startswith("lumps/") for n in names)

            pk3_to_wad(pk3_path, wad2_path)
            with WadArchive(wad2_path, "r") as wad:
                restored = wad.namelist()
                assert "F_START" in restored
                assert "F_END" in restored
                assert "S_START" in restored
                assert "S_END" in restored
                assert "FLAT0001" in restored
                assert "FLAT0002" in restored
                assert "TROOA1" in restored
                assert wad.read("FLAT0001") == b"\x11" * 4096
                assert wad.read("FLAT0002") == b"\x22" * 4096
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)
            os.unlink(wad2_path)

    def test_pk3_colliding_truncated_names_do_not_crash(self) -> None:
        """PK3 entries whose lump_name truncates to the same 8 chars must not crash."""
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad_path = f.name
        try:
            with Pk3Archive(pk3_path, "w") as pk3:
                # Both filenames truncate to "LONGNAME" when stripped to 8 chars
                pk3.writestr("lumps/LONGNAME1.lmp", b"data1")
                pk3.writestr("lumps/LONGNAME2.lmp", b"data2")
            # Conversion must not raise
            pk3_to_wad(pk3_path, wad_path)
            with WadArchive(wad_path, "r") as wad:
                names = wad.namelist()
                assert len(names) >= 1
        finally:
            os.unlink(pk3_path)
            os.unlink(wad_path)

    def test_data_integrity_through_round_trip(self) -> None:
        """Lump data must survive WAD→PK3→WAD intact."""
        wad_path = self._make_wad_with_long_names()
        with tempfile.NamedTemporaryFile(suffix=".pk3", delete=False) as f:
            pk3_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            wad2_path = f.name
        try:
            wad_to_pk3(wad_path, pk3_path)
            pk3_to_wad(pk3_path, wad2_path)
            with WadArchive(wad2_path, "r") as wad:
                # Data must be byte-for-byte identical
                assert wad.read("FLAT0001") == b"\x11" * 4096
                assert wad.read("FLAT0002") == b"\x22" * 4096
                assert wad.read("TROOA1") == b"\x33" * 100
        finally:
            os.unlink(wad_path)
            os.unlink(pk3_path)
            os.unlink(wad2_path)
