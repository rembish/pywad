"""Tests for UDMF parser and serializer."""

from __future__ import annotations

from wadlib.lumps.udmf import (
    UdmfLinedef,
    UdmfMap,
    UdmfSector,
    UdmfSidedef,
    UdmfThing,
    UdmfVertex,
    parse_udmf,
    serialize_udmf,
)

_SIMPLE_MAP = """
namespace = "zdoom";

thing { x = 64.0; y = -128.0; type = 1; angle = 90; }
thing { x = 128.0; y = 0.0; type = 3004; angle = 270; }

vertex { x = 0.0; y = 0.0; }
vertex { x = 256.0; y = 0.0; }
vertex { x = 256.0; y = 256.0; }
vertex { x = 0.0; y = 256.0; }

linedef { v1 = 0; v2 = 1; sidefront = 0; }
linedef { v1 = 1; v2 = 2; sidefront = 1; }
linedef { v1 = 2; v2 = 3; sidefront = 2; }
linedef { v1 = 3; v2 = 0; sidefront = 3; }

sidedef { sector = 0; texturemiddle = "BRICK1"; }
sidedef { sector = 0; texturemiddle = "BRICK1"; }
sidedef { sector = 0; texturemiddle = "BRICK1"; }
sidedef { sector = 0; texturemiddle = "BRICK1"; }

sector {
    heightfloor = 0;
    heightceiling = 128;
    texturefloor = "FLAT1";
    textureceiling = "CEIL3_5";
    lightlevel = 192;
}
"""


class TestParseUdmf:
    def test_namespace(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert m.namespace == "zdoom"

    def test_things(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert len(m.things) == 2
        assert m.things[0].x == 64.0
        assert m.things[0].y == -128.0
        assert m.things[0].type == 1
        assert m.things[0].angle == 90
        assert m.things[1].type == 3004

    def test_vertices(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert len(m.vertices) == 4
        assert m.vertices[0].x == 0.0
        assert m.vertices[1].x == 256.0

    def test_linedefs(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert len(m.linedefs) == 4
        assert m.linedefs[0].v1 == 0
        assert m.linedefs[0].v2 == 1
        assert m.linedefs[0].sidefront == 0

    def test_sidedefs(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert len(m.sidedefs) == 4
        assert m.sidedefs[0].sector == 0
        assert m.sidedefs[0].texturemiddle == "BRICK1"

    def test_sectors(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        assert len(m.sectors) == 1
        assert m.sectors[0].heightfloor == 0
        assert m.sectors[0].heightceiling == 128
        assert m.sectors[0].texturefloor == "FLAT1"
        assert m.sectors[0].lightlevel == 192


class TestUdmfComments:
    def test_line_comments(self) -> None:
        text = """
namespace = "doom";
// This is a comment
thing { x = 1.0; y = 2.0; type = 1; }
"""
        m = parse_udmf(text)
        assert len(m.things) == 1

    def test_block_comments(self) -> None:
        text = """
namespace = "doom";
/* Multi-line
   comment */
thing { x = 1.0; y = 2.0; type = 1; }
"""
        m = parse_udmf(text)
        assert len(m.things) == 1


class TestUdmfExtendedProps:
    def test_boolean_props(self) -> None:
        text = """
namespace = "zdoom";
thing { x = 0.0; y = 0.0; type = 1; skill1 = true; skill2 = false; }
"""
        m = parse_udmf(text)
        assert m.things[0].props.get("skill1") is True
        assert m.things[0].props.get("skill2") is False

    def test_custom_linedef_props(self) -> None:
        text = """
namespace = "zdoom";
linedef { v1 = 0; v2 = 1; sidefront = 0; blocking = true; arg0 = 42; }
"""
        m = parse_udmf(text)
        assert m.linedefs[0].props.get("blocking") is True
        assert m.linedefs[0].props.get("arg0") == 42

    def test_sector_with_extra_props(self) -> None:
        text = """
namespace = "zdoom";
sector {
    heightfloor = 0; heightceiling = 128;
    texturefloor = "FLAT1"; textureceiling = "CEIL3_5";
    lightlevel = 160;
    xpanningfloor = 32.0;
    lightcolor = 16777215;
}
"""
        m = parse_udmf(text)
        assert m.sectors[0].props.get("xpanningfloor") == 32.0
        assert m.sectors[0].props.get("lightcolor") == 16777215


class TestUdmfEmpty:
    def test_empty_map(self) -> None:
        m = parse_udmf('namespace = "doom";')
        assert m.namespace == "doom"
        assert len(m.things) == 0
        assert len(m.vertices) == 0

    def test_no_namespace(self) -> None:
        m = parse_udmf("thing { x = 0.0; y = 0.0; type = 1; }")
        assert m.namespace == "doom"  # default


class TestSerializeUdmf:
    def test_round_trip(self) -> None:
        m = parse_udmf(_SIMPLE_MAP)
        text = serialize_udmf(m)
        m2 = parse_udmf(text)
        assert m2.namespace == m.namespace
        assert len(m2.things) == len(m.things)
        assert len(m2.vertices) == len(m.vertices)
        assert len(m2.linedefs) == len(m.linedefs)
        assert len(m2.sidedefs) == len(m.sidedefs)
        assert len(m2.sectors) == len(m.sectors)
        # Data integrity
        assert m2.things[0].type == 1
        assert m2.things[0].x == 64.0
        assert m2.sectors[0].texturefloor == "FLAT1"

    def test_serialize_empty(self) -> None:
        m = UdmfMap(namespace="zdoom")
        text = serialize_udmf(m)
        assert 'namespace = "zdoom"' in text

    def test_serialize_custom_props(self) -> None:
        m = UdmfMap(namespace="zdoom")
        m.things.append(UdmfThing(x=10.0, y=20.0, type=1, props={"skill3": True}))
        text = serialize_udmf(m)
        assert "skill3 = true" in text

    def test_serialize_floats(self) -> None:
        m = UdmfMap()
        m.vertices.append(UdmfVertex(x=1.5, y=-3.25))
        text = serialize_udmf(m)
        assert "1.5" in text
        assert "-3.25" in text


class TestUdmfFromScratch:
    def test_build_simple_room(self) -> None:
        """Build a minimal UDMF room and verify it serializes correctly."""
        m = UdmfMap(namespace="zdoom")
        m.things.append(UdmfThing(x=128.0, y=128.0, type=1, angle=90))
        m.vertices = [
            UdmfVertex(0.0, 0.0),
            UdmfVertex(256.0, 0.0),
            UdmfVertex(256.0, 256.0),
            UdmfVertex(0.0, 256.0),
        ]
        m.linedefs = [
            UdmfLinedef(v1=0, v2=1, sidefront=0),
            UdmfLinedef(v1=1, v2=2, sidefront=1),
            UdmfLinedef(v1=2, v2=3, sidefront=2),
            UdmfLinedef(v1=3, v2=0, sidefront=3),
        ]
        m.sidedefs = [UdmfSidedef(sector=0, texturemiddle="BRICK1") for _ in range(4)]
        m.sectors = [
            UdmfSector(
                heightfloor=0, heightceiling=128, texturefloor="FLAT1", textureceiling="CEIL3_5"
            )
        ]

        text = serialize_udmf(m)
        m2 = parse_udmf(text)
        assert len(m2.things) == 1
        assert len(m2.vertices) == 4
        assert len(m2.linedefs) == 4
        assert len(m2.sidedefs) == 4
        assert len(m2.sectors) == 1
