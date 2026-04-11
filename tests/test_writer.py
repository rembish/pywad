"""Tests for the WAD writer and round-trip serialization."""

from __future__ import annotations

import os
import struct
import tempfile

import pytest

from wadlib.enums import WadType
from wadlib.lumps.blockmap import BlockMap, Reject
from wadlib.lumps.flat import FLAT_BYTES, encode_flat
from wadlib.lumps.hexen import HexenLineDef, HexenThing
from wadlib.lumps.lines import LineDefinition
from wadlib.lumps.nodes import Node
from wadlib.lumps.picture import encode_picture
from wadlib.lumps.playpal import palette_to_bytes, palettes_to_bytes
from wadlib.lumps.sectors import Sector
from wadlib.lumps.segs import Seg, SubSector
from wadlib.lumps.sidedefs import SideDef
from wadlib.lumps.sound import encode_dmx
from wadlib.lumps.textures import (
    PatchDescriptor,
    TextureDef,
    pnames_to_bytes,
    texturelist_to_bytes,
)
from wadlib.lumps.things import Flags, Thing
from wadlib.lumps.vertices import Vertex
from wadlib.wad import WadFile
from wadlib.writer import WadWriter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# WadWriter basic operations
# ---------------------------------------------------------------------------


class TestWadWriterBasic:
    def test_create_empty_pwad(self) -> None:
        w = WadWriter(WadType.PWAD)
        assert w.wad_type == WadType.PWAD
        assert w.lump_count == 0
        assert len(w) == 0
        assert repr(w) == "<WadWriter PWAD 0 lumps>"

    def test_create_empty_iwad(self) -> None:
        w = WadWriter(WadType.IWAD)
        assert w.wad_type == WadType.IWAD
        data = w.to_bytes()
        assert data[:4] == b"IWAD"

    def test_add_lump(self) -> None:
        w = WadWriter()
        idx = w.add_lump("TEST", b"\x01\x02\x03")
        assert idx == 0
        assert w.lump_count == 1
        assert w.lump_names == ["TEST"]

    def test_add_marker(self) -> None:
        w = WadWriter()
        idx = w.add_marker("MAP01")
        assert idx == 0
        assert w.get_lump("MAP01") == b""

    def test_insert_lump(self) -> None:
        w = WadWriter()
        w.add_lump("A", b"aaa")
        w.add_lump("C", b"ccc")
        w.insert_lump(1, "B", b"bbb")
        assert w.lump_names == ["A", "B", "C"]

    def test_replace_lump(self) -> None:
        w = WadWriter()
        w.add_lump("TEST", b"old")
        assert w.replace_lump("TEST", b"new")
        assert w.get_lump("TEST") == b"new"

    def test_replace_lump_not_found(self) -> None:
        w = WadWriter()
        assert not w.replace_lump("MISSING", b"data")

    def test_replace_lump_occurrence(self) -> None:
        w = WadWriter()
        w.add_lump("X", b"first")
        w.add_lump("X", b"second")
        assert w.replace_lump("X", b"replaced", occurrence=1)
        assert w.get_lump("X", occurrence=0) == b"first"
        assert w.get_lump("X", occurrence=1) == b"replaced"

    def test_remove_lump(self) -> None:
        w = WadWriter()
        w.add_lump("A", b"a")
        w.add_lump("B", b"b")
        assert w.remove_lump("A")
        assert w.lump_names == ["B"]

    def test_remove_lump_not_found(self) -> None:
        w = WadWriter()
        assert not w.remove_lump("MISSING")

    def test_remove_lump_occurrence(self) -> None:
        w = WadWriter()
        w.add_lump("X", b"first")
        w.add_lump("X", b"second")
        assert w.remove_lump("X", occurrence=1)
        assert w.lump_count == 1
        assert w.get_lump("X") == b"first"

    def test_find_lump(self) -> None:
        w = WadWriter()
        w.add_lump("A", b"a")
        w.add_lump("B", b"b")
        w.add_lump("A", b"a2")
        assert w.find_lump("A") == 0
        assert w.find_lump("A", start=1) == 2
        assert w.find_lump("B") == 1
        assert w.find_lump("MISSING") == -1

    def test_get_lump_none(self) -> None:
        w = WadWriter()
        assert w.get_lump("MISSING") is None

    def test_name_too_long(self) -> None:
        w = WadWriter()
        with pytest.raises(ValueError, match="Lump name too long"):
            w.add_lump("TOOLONGNAME", b"x")

    def test_name_uppercased(self) -> None:
        w = WadWriter()
        w.add_lump("lower", b"data")
        assert w.lump_names == ["LOWER"]
        assert w.get_lump("lower") == b"data"


# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------


class TestNamespaceHelpers:
    def test_add_flat_creates_namespace(self) -> None:
        w = WadWriter()
        w.add_flat("FLAT01", b"\x00" * 4096)
        assert w.lump_names == ["F_START", "FLAT01", "F_END"]

    def test_add_flat_inserts_before_end(self) -> None:
        w = WadWriter()
        w.add_flat("FLAT01", b"\x00" * 4096)
        w.add_flat("FLAT02", b"\x01" * 4096)
        assert w.lump_names == ["F_START", "FLAT01", "FLAT02", "F_END"]

    def test_add_sprite_creates_namespace(self) -> None:
        w = WadWriter()
        w.add_sprite("TROO", b"\xFF")
        assert w.lump_names == ["S_START", "TROO", "S_END"]

    def test_add_patch_creates_namespace(self) -> None:
        w = WadWriter()
        w.add_patch("WALL01", b"\xAA")
        assert w.lump_names == ["P_START", "WALL01", "P_END"]


# ---------------------------------------------------------------------------
# WAD binary format
# ---------------------------------------------------------------------------


class TestWadBinaryFormat:
    def test_empty_wad_structure(self) -> None:
        w = WadWriter(WadType.PWAD)
        data = w.to_bytes()
        # Header: magic(4) + numlumps(4) + diroffset(4)
        assert len(data) == 12
        magic, numlumps, diroffset = struct.unpack("<4sII", data)
        assert magic == b"PWAD"
        assert numlumps == 0
        assert diroffset == 12

    def test_single_lump_structure(self) -> None:
        w = WadWriter(WadType.PWAD)
        w.add_lump("TEST", b"\x01\x02\x03\x04")
        data = w.to_bytes()

        # Header
        magic, numlumps, diroffset = struct.unpack("<4sII", data[:12])
        assert magic == b"PWAD"
        assert numlumps == 1
        assert diroffset == 16  # 12 header + 4 data

        # Lump data at offset 12
        assert data[12:16] == b"\x01\x02\x03\x04"

        # Directory at offset 16
        offset, size, name = struct.unpack("<II8s", data[16:32])
        assert offset == 12
        assert size == 4
        assert name == b"TEST\x00\x00\x00\x00"

    def test_marker_lump_structure(self) -> None:
        w = WadWriter()
        w.add_marker("MAP01")
        w.add_lump("THINGS", b"\x00" * 10)
        data = w.to_bytes()

        _, numlumps, diroffset = struct.unpack("<4sII", data[:12])
        assert numlumps == 2

        # First dir entry: marker (size 0)
        off1, sz1, _ = struct.unpack("<II8s", data[diroffset : diroffset + 16])
        assert sz1 == 0

        # Second dir entry: THINGS
        off2, sz2, _ = struct.unpack("<II8s", data[diroffset + 16 : diroffset + 32])
        assert sz2 == 10

    def test_save_and_reload(self) -> None:
        w = WadWriter(WadType.PWAD)
        w.add_lump("PLAYPAL", b"\x00" * 768)
        w.add_marker("MAP01")
        w.add_lump("THINGS", b"\xFF" * 20)

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name

        try:
            w.save(path)
            with WadFile(path) as wad:
                assert wad.wad_type == WadType.PWAD
                assert wad.directory_size == 3
                names = [e.name for e in wad.directory]
                assert names == ["PLAYPAL", "MAP01", "THINGS"]
                # Verify data
                entry = wad.directory[0]
                wad.fd.seek(entry.offset)
                assert wad.fd.read(entry.size) == b"\x00" * 768
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Data type serialization — round-trip (struct → bytes → struct)
# ---------------------------------------------------------------------------


class TestThingSerialization:
    def test_round_trip(self) -> None:
        t = Thing(x=100, y=-200, direction=90, type=3004, flags=Flags(7))
        raw = t.to_bytes()
        assert len(raw) == 10  # Doom thing = 10 bytes
        # Unpack and compare
        x, y, d, tp, fl = struct.unpack("<hhHHH", raw)
        assert x == 100
        assert y == -200
        assert d == 90
        assert tp == 3004
        assert fl == 7


class TestVertexSerialization:
    def test_round_trip(self) -> None:
        v = Vertex(x=-32000, y=16000)
        raw = v.to_bytes()
        assert len(raw) == 4
        x, y = struct.unpack("<hh", raw)
        assert x == -32000
        assert y == 16000


class TestLineDefSerialization:
    def test_round_trip(self) -> None:
        ld = LineDefinition(
            start_vertex=0,
            finish_vertex=1,
            flags=1,
            special_type=0,
            sector_tag=0,
            right_sidedef=0,
            left_sidedef=-1,
        )
        raw = ld.to_bytes()
        assert len(raw) == 14  # Doom linedef = 14 bytes
        sv, fv, fl, st, stag, rsd, lsd = struct.unpack("<HHHHHhh", raw)
        assert sv == 0
        assert fv == 1
        assert fl == 1
        assert lsd == -1


class TestSideDefSerialization:
    def test_round_trip(self) -> None:
        sd = SideDef(
            x_offset=0,
            y_offset=0,
            upper_texture="-",
            lower_texture="-",
            middle_texture="BRICK1",
            sector=0,
        )
        raw = sd.to_bytes()
        assert len(raw) == 30  # Doom sidedef = 30 bytes
        xo, yo, ut, lt, mt, sec = struct.unpack("<hh8s8s8sH", raw)
        assert mt.rstrip(b"\x00") == b"BRICK1"
        assert ut.rstrip(b"\x00") == b"-"

    def test_texture_name_truncated(self) -> None:
        sd = SideDef(0, 0, "TOOLONGNAME", "-", "-", 0)
        raw = sd.to_bytes()
        _, _, ut, _, _, _ = struct.unpack("<hh8s8s8sH", raw)
        assert len(ut) == 8


class TestSectorSerialization:
    def test_round_trip(self) -> None:
        s = Sector(
            floor_height=0,
            ceiling_height=128,
            floor_texture="FLAT1",
            ceiling_texture="CEIL3_5",
            light_level=160,
            special=0,
            tag=0,
        )
        raw = s.to_bytes()
        assert len(raw) == 26  # Doom sector = 26 bytes
        fh, ch, ft, ct, ll, sp, tg = struct.unpack("<hh8s8sHHH", raw)
        assert fh == 0
        assert ch == 128
        assert ft.rstrip(b"\x00") == b"FLAT1"
        assert ct.rstrip(b"\x00") == b"CEIL3_5"
        assert ll == 160


class TestSegSerialization:
    def test_round_trip(self) -> None:
        s = Seg(start_vertex=0, end_vertex=1, angle=16384, linedef=0, direction=0, offset=0)
        raw = s.to_bytes()
        assert len(raw) == 12  # Doom seg = 12 bytes


class TestSubSectorSerialization:
    def test_round_trip(self) -> None:
        ss = SubSector(seg_count=4, first_seg=0)
        raw = ss.to_bytes()
        assert len(raw) == 4
        sc, fs = struct.unpack("<HH", raw)
        assert sc == 4
        assert fs == 0


class TestNodeSerialization:
    def test_round_trip(self) -> None:
        n = Node(
            x=0, y=0, dx=64, dy=0,
            right_top=64, right_bottom=0, right_left=0, right_right=64,
            left_top=0, left_bottom=-64, left_left=0, left_right=64,
            right_child=0, left_child=0x8001,
        )
        raw = n.to_bytes()
        assert len(raw) == 28  # Doom node = 28 bytes
        values = struct.unpack("<hhhhhhhhhhhhHH", raw)
        assert values[2] == 64  # dx
        assert values[13] == 0x8001  # left_child with SSECTOR flag


class TestHexenThingSerialization:
    def test_round_trip(self) -> None:
        t = HexenThing(
            tid=1, x=100, y=200, z=0, angle=90, type=1, flags=Flags(7),
            action=0, arg0=0, arg1=0, arg2=0, arg3=0, arg4=0,
        )
        raw = t.to_bytes()
        assert len(raw) == 20  # Hexen thing = 20 bytes


class TestHexenLineDefSerialization:
    def test_round_trip(self) -> None:
        ld = HexenLineDef(
            start_vertex=0, finish_vertex=1, flags=1, special_type=0,
            arg0=0, arg1=0, arg2=0, arg3=0, arg4=0,
            right_sidedef=0, left_sidedef=-1,
        )
        raw = ld.to_bytes()
        assert len(raw) == 16  # Hexen linedef = 16 bytes


# ---------------------------------------------------------------------------
# Reject and BlockMap
# ---------------------------------------------------------------------------


class TestRejectSerialization:
    def test_build_empty(self) -> None:
        r = Reject.build(4)
        assert len(r.data) == 2  # 16 bits = 2 bytes
        assert r.can_see(0, 1, 4)
        assert r.to_bytes() == r.data

    def test_build_with_rejections(self) -> None:
        r = Reject.build(4, rejected={(0, 1), (1, 0)})
        assert not r.can_see(0, 1, 4)
        assert not r.can_see(1, 0, 4)
        assert r.can_see(0, 0, 4)

    def test_from_bytes(self) -> None:
        data = b"\xFF\xFF"
        r = Reject.from_bytes(data)
        assert r.to_bytes() == data


# ---------------------------------------------------------------------------
# Texture serialization
# ---------------------------------------------------------------------------


class TestTextureSerialization:
    def test_patch_descriptor(self) -> None:
        pd = PatchDescriptor(origin_x=10, origin_y=20, patch_index=5)
        raw = pd.to_bytes()
        assert len(raw) == 10  # 2+2+2+2+2

    def test_texture_def(self) -> None:
        td = TextureDef(
            name="BRICK7",
            width=64,
            height=128,
            patches=[PatchDescriptor(0, 0, 0)],
        )
        raw = td.to_bytes()
        # Header: 8+4+2+2+4+2 = 22, plus 1 patch × 10 = 32
        assert len(raw) == 32

    def test_pnames_round_trip(self) -> None:
        names = ["WALL00_1", "WALL00_2", "RW1_1"]
        raw = pnames_to_bytes(names)
        count = struct.unpack("<I", raw[:4])[0]
        assert count == 3
        parsed: list[str] = []
        for i in range(count):
            off = 4 + i * 8
            parsed.append(raw[off : off + 8].rstrip(b"\x00").decode("ascii"))
        assert parsed == names

    def test_texturelist_round_trip(self) -> None:
        textures = [
            TextureDef("BRICK1", 64, 128, [PatchDescriptor(0, 0, 0)]),
            TextureDef("BRICK2", 128, 128, [PatchDescriptor(0, 0, 1), PatchDescriptor(64, 0, 2)]),
        ]
        raw = texturelist_to_bytes(textures)
        # Parse back
        count = struct.unpack("<I", raw[:4])[0]
        assert count == 2


# ---------------------------------------------------------------------------
# PlayPal serialization
# ---------------------------------------------------------------------------


class TestPlayPalSerialization:
    def test_palette_to_bytes(self) -> None:
        pal = [(i, i, i) for i in range(256)]
        raw = palette_to_bytes(pal)
        assert len(raw) == 768
        assert raw[0] == 0
        assert raw[3] == 1  # second colour R
        assert raw[765] == 255  # last colour R

    def test_palettes_to_bytes(self) -> None:
        pals = [[(i, i, i) for i in range(256)] for _ in range(14)]
        raw = palettes_to_bytes(pals)
        assert len(raw) == 768 * 14


# ---------------------------------------------------------------------------
# Flat encoding
# ---------------------------------------------------------------------------


class TestFlatEncoding:
    def test_encode_solid_colour(self) -> None:
        from PIL import Image

        palette = [(i, i, i) for i in range(256)]
        img = Image.new("RGB", (64, 64), (128, 128, 128))
        raw = encode_flat(img, palette)
        assert len(raw) == FLAT_BYTES
        # Every pixel should be palette index 128
        assert raw[0] == 128
        assert raw[4095] == 128

    def test_encode_resizes(self) -> None:
        from PIL import Image

        palette = [(0, 0, 0)] * 256
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        raw = encode_flat(img, palette)
        assert len(raw) == FLAT_BYTES


# ---------------------------------------------------------------------------
# Picture encoding
# ---------------------------------------------------------------------------


class TestPictureEncoding:
    def test_encode_solid(self) -> None:
        from PIL import Image

        palette = [(i, 0, 0) for i in range(256)]
        img = Image.new("RGBA", (4, 4), (100, 0, 0, 255))
        raw = encode_picture(img, palette)
        # Should be valid picture format
        w, h, lx, ty = struct.unpack("<HHhh", raw[:8])
        assert w == 4
        assert h == 4
        assert lx == 0
        assert ty == 0

    def test_encode_with_transparency(self) -> None:
        from PIL import Image

        palette = [(i, 0, 0) for i in range(256)]
        img = Image.new("RGBA", (2, 4), (0, 0, 0, 0))
        # Make top half opaque
        for y in range(2):
            for x in range(2):
                img.putpixel((x, y), (50, 0, 0, 255))
        raw = encode_picture(img, palette)
        w, h, _, _ = struct.unpack("<HHhh", raw[:8])
        assert w == 2
        assert h == 4

    def test_encode_with_offsets(self) -> None:
        from PIL import Image

        palette = [(0, 0, 0)] * 256
        img = Image.new("RGBA", (8, 16), (0, 0, 0, 255))
        raw = encode_picture(img, palette, left_offset=4, top_offset=15)
        _, _, lx, ty = struct.unpack("<HHhh", raw[:8])
        assert lx == 4
        assert ty == 15


# ---------------------------------------------------------------------------
# DMX sound encoding
# ---------------------------------------------------------------------------


class TestDmxSoundEncoding:
    def test_encode_basic(self) -> None:
        pcm = bytes([0x80] * 100)  # silence
        raw = encode_dmx(pcm, rate=11025)
        # Header: fmt(2) + rate(2) + num_samples(4) = 8 bytes
        fmt, rate, ns = struct.unpack("<HHI", raw[:8])
        assert fmt == 3
        assert rate == 11025
        assert ns == 100 + 16  # pcm + padding
        # Padding (16 bytes of 0x80)
        assert raw[8:24] == b"\x80" * 16
        # PCM data
        assert raw[24:] == pcm

    def test_encode_custom_rate(self) -> None:
        pcm = bytes([0x80] * 50)
        raw = encode_dmx(pcm, rate=22050)
        _, rate, _ = struct.unpack("<HHI", raw[:8])
        assert rate == 22050


# ---------------------------------------------------------------------------
# add_map helper
# ---------------------------------------------------------------------------


class TestAddMap:
    def test_add_simple_map(self) -> None:
        w = WadWriter()
        things = [Thing(0, 0, 0, 1, Flags(7))]
        verts = [Vertex(0, 0), Vertex(64, 0), Vertex(64, 64), Vertex(0, 64)]
        w.add_map("MAP01", things=things, vertices=verts)
        names = w.lump_names
        assert names[0] == "MAP01"
        assert "THINGS" in names
        assert "VERTEXES" in names
        assert "LINEDEFS" in names
        assert "SIDEDEFS" in names
        assert "SECTORS" in names
        assert "SEGS" in names
        assert "SSECTORS" in names
        assert "NODES" in names
        assert "REJECT" in names
        assert "BLOCKMAP" in names

    def test_add_map_with_behavior(self) -> None:
        w = WadWriter()
        w.add_map("MAP01", behavior=b"\x00" * 4)
        assert "BEHAVIOR" in w.lump_names

    def test_add_map_data_integrity(self) -> None:
        w = WadWriter()
        things = [
            Thing(100, 200, 90, 3004, Flags(7)),
            Thing(-50, 300, 270, 3001, Flags(7)),
        ]
        w.add_map("MAP01", things=things)
        things_data = w.get_lump("THINGS")
        assert things_data is not None
        assert len(things_data) == 20  # 2 things × 10 bytes


# ---------------------------------------------------------------------------
# Round-trip with real WADs
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRoundTrip:
    def test_from_wad_preserves_directory(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            writer = WadWriter.from_wad(wad)
            assert writer.wad_type == wad.wad_type
            assert writer.lump_count == wad.directory_size
            # Lump names match
            orig_names = [e.name for e in wad.directory]
            assert writer.lump_names == orig_names

    def test_from_wad_preserves_lump_sizes(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            writer = WadWriter.from_wad(wad)
            # Check by index since names can repeat (e.g. THINGS per map)
            for i, entry in enumerate(wad.directory):
                writer_data = writer._lumps[i].data
                assert len(writer_data) == entry.size, (
                    f"Size mismatch at index {i} ({entry.name}): "
                    f"{len(writer_data)} != {entry.size}"
                )

    def test_round_trip_reload(self) -> None:
        """Write a WAD, reload it, verify the directory matches."""
        with WadFile(FREEDOOM2) as wad:
            writer = WadWriter.from_wad(wad)

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name

        try:
            writer.save(path)
            with WadFile(path) as reloaded:
                assert reloaded.wad_type == WadType.IWAD
                assert reloaded.directory_size == writer.lump_count
                # Check a few specific lumps
                for name in ("PLAYPAL", "COLORMAP", "PNAMES"):
                    orig = writer.get_lump(name)
                    entry = next(e for e in reloaded.directory if e.name == name)
                    reloaded.fd.seek(entry.offset)
                    reloaded_data = reloaded.fd.read(entry.size)
                    assert reloaded_data == orig, f"Mismatch in {name}"
        finally:
            os.unlink(path)

    def test_round_trip_maps_work(self) -> None:
        """After round-trip, maps should still be parseable."""
        with WadFile(FREEDOOM2) as wad:
            writer = WadWriter.from_wad(wad)

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name

        try:
            writer.save(path)
            with WadFile(path) as reloaded:
                assert len(reloaded.maps) > 0
                m = reloaded.maps[0]
                assert m.things is not None
                assert len(list(m.things)) > 0
        finally:
            os.unlink(path)

    def test_round_trip_thing_serialization(self) -> None:
        """Read things from a real WAD, serialize, compare bytes."""
        with WadFile(FREEDOOM2) as wad:
            m = wad.maps[0]
            assert m.things is not None
            # Read original raw bytes
            orig_raw = m.things.raw()
            # Serialize each thing and concatenate
            rebuilt = b"".join(t.to_bytes() for t in m.things)
            assert rebuilt == orig_raw

    def test_round_trip_vertex_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            m = wad.maps[0]
            assert m.vertices is not None
            orig_raw = m.vertices.raw()
            rebuilt = b"".join(v.to_bytes() for v in m.vertices)
            assert rebuilt == orig_raw

    def test_round_trip_linedef_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            m = wad.maps[0]
            assert m.lines is not None
            orig_raw = m.lines.raw()
            rebuilt = b"".join(ld.to_bytes() for ld in m.lines)
            assert rebuilt == orig_raw

    def test_round_trip_sidedef_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            m = wad.maps[0]
            assert m.sidedefs is not None
            orig_raw = m.sidedefs.raw()
            rebuilt = b"".join(sd.to_bytes() for sd in m.sidedefs)
            assert rebuilt == orig_raw

    def test_round_trip_sector_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            m = wad.maps[0]
            assert m.sectors is not None
            orig_raw = m.sectors.raw()
            rebuilt = b"".join(s.to_bytes() for s in m.sectors)
            assert rebuilt == orig_raw

    def test_round_trip_seg_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            # Find a map with vanilla segs (not ZNODES)
            for m in wad.maps:
                if m.segs is not None and hasattr(m.segs, "raw"):
                    orig_raw = m.segs.raw()
                    if orig_raw:
                        rebuilt = b"".join(s.to_bytes() for s in m.segs)
                        assert rebuilt == orig_raw
                        return
            pytest.skip("No map with vanilla segs found")

    def test_round_trip_node_serialization(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            for m in wad.maps:
                if m.nodes is not None and hasattr(m.nodes, "raw"):
                    orig_raw = m.nodes.raw()
                    if orig_raw:
                        rebuilt = b"".join(n.to_bytes() for n in m.nodes)
                        assert rebuilt == orig_raw
                        return
            pytest.skip("No map with vanilla nodes found")

    def test_modify_and_save(self) -> None:
        """Modify a lump in a round-tripped WAD and verify."""
        with WadFile(FREEDOOM2) as wad:
            writer = WadWriter.from_wad(wad)

        # Replace ENDOOM with custom data
        custom_endoom = b"\x20\x07" * 2000  # 4000 bytes (80x25x2)
        writer.replace_lump("ENDOOM", custom_endoom)

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name

        try:
            writer.save(path)
            with WadFile(path) as reloaded:
                entry = next(e for e in reloaded.directory if e.name == "ENDOOM")
                reloaded.fd.seek(entry.offset)
                assert reloaded.fd.read(entry.size) == custom_endoom
        finally:
            os.unlink(path)
