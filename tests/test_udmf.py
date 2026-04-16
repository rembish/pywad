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


# ---------------------------------------------------------------------------
# Tokenizer correctness — hex integers and escaped strings
# ---------------------------------------------------------------------------


class TestUdmfTokenizer:
    def test_hex_integer(self) -> None:
        """Hex literals like 0x1A must be parsed as integers."""
        # id is a known UdmfThing field — check it directly, not via props
        text = 'namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 1; id = 0x1A; }'
        m = parse_udmf(text)
        assert m.things[0].id == 0x1A

    def test_hex_integer_uppercase(self) -> None:
        # special is a named UdmfLinedef field
        text = 'namespace = "doom";\nlinedef { v1 = 0; v2 = 1; sidefront = 0; special = 0xFF; }'
        m = parse_udmf(text)
        assert m.linedefs[0].special == 255

    def test_hex_integer_negative(self) -> None:
        # arg0 is not a named UdmfThing field, stays in props
        text = 'namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 1; arg0 = -0x10; }'
        m = parse_udmf(text)
        assert m.things[0].props.get("arg0") == -16

    def test_escaped_quote_in_string(self) -> None:
        """Escaped quotes inside UDMF string values must be unescaped."""
        # texturemiddle is a named UdmfSidedef field
        text = r'namespace = "doom";' + "\n" + r'sidedef { texturemiddle = "A\"B"; sector = 0; }'
        m = parse_udmf(text)
        assert m.sidedefs[0].texturemiddle == 'A"B'

    def test_escaped_backslash_in_string(self) -> None:
        text = 'namespace = "doom";\n' + r'sidedef { texturemiddle = "A\\B"; sector = 0; }'
        m = parse_udmf(text)
        assert m.sidedefs[0].texturemiddle == "A\\B"

    def test_decimal_integer_unchanged(self) -> None:
        """Ordinary decimal integers must still parse correctly."""
        text = 'namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 7001; }'
        m = parse_udmf(text)
        assert m.things[0].type == 7001

    def test_negative_decimal_unchanged(self) -> None:
        text = 'namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 1; arg0 = -3; }'
        m = parse_udmf(text)
        assert m.things[0].props.get("arg0") == -3


# ---------------------------------------------------------------------------
# UdmfMap.warnings — namespace and required-field validation
# ---------------------------------------------------------------------------


class TestUdmfWarnings:
    def test_known_namespace_no_warning(self) -> None:
        for ns in ("doom", "heretic", "hexen", "strife", "zdoom", "gzdoom", "eternity", "vavoom"):
            m = parse_udmf(f'namespace = "{ns}";')
            assert not any("namespace" in w for w in m.warnings), f"unexpected warning for {ns!r}"

    def test_unknown_namespace_produces_warning(self) -> None:
        m = parse_udmf('namespace = "myport";')
        assert any("unknown namespace" in w for w in m.warnings)
        assert any("myport" in w for w in m.warnings)

    def test_unknown_namespace_case_insensitive(self) -> None:
        m = parse_udmf('namespace = "Doom";')
        assert not any("namespace" in w for w in m.warnings)

    def test_no_namespace_no_warning(self) -> None:
        m = parse_udmf("thing { x = 0.0; y = 0.0; type = 1; }")
        assert not m.warnings

    def test_vertex_missing_x_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nvertex { y = 1.0; }')
        assert any("vertex" in w and "x" in w for w in m.warnings)

    def test_vertex_missing_y_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nvertex { x = 1.0; }')
        assert any("vertex" in w and "y" in w for w in m.warnings)

    def test_vertex_with_both_coords_no_warning(self) -> None:
        m = parse_udmf('namespace = "doom";\nvertex { x = 0.0; y = 0.0; }')
        assert not m.warnings

    def test_linedef_missing_v1_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nlinedef { v2 = 1; sidefront = 0; }')
        assert any("linedef" in w and "v1" in w for w in m.warnings)

    def test_linedef_missing_v2_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nlinedef { v1 = 0; sidefront = 0; }')
        assert any("linedef" in w and "v2" in w for w in m.warnings)

    def test_linedef_missing_sidefront_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nlinedef { v1 = 0; v2 = 1; }')
        assert any("linedef" in w and "sidefront" in w for w in m.warnings)

    def test_complete_linedef_no_warning(self) -> None:
        # Must include matching vertices, a sidedef, and a sector so that
        # the cross-reference integrity checks do not fire.
        text = (
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; }\n'
            'vertex { x = 64.0; y = 0.0; }\n'
            'sector { texturefloor = "FLAT"; textureceiling = "CEIL"; }\n'
            'sidedef { sector = 0; }\n'
            'linedef { v1 = 0; v2 = 1; sidefront = 0; }'
        )
        m = parse_udmf(text)
        assert not m.warnings

    def test_warnings_field_in_default_udmfmap(self) -> None:
        m = UdmfMap()
        assert m.warnings == []


# ---------------------------------------------------------------------------
# Namespace-specific semantic validation (Step 7)
# ---------------------------------------------------------------------------

# Minimal complete UDMF map used as a clean base for namespace tests.
_MINIMAL_DOOM_MAP = (
    'namespace = "doom";\n'
    'vertex { x = 0.0; y = 0.0; }\n'
    'vertex { x = 64.0; y = 0.0; }\n'
    'sector { texturefloor = "FLAT"; textureceiling = "CEIL"; }\n'
    'sidedef { sector = 0; }\n'
    'linedef { v1 = 0; v2 = 1; sidefront = 0; }\n'
    'thing { x = 32.0; y = 32.0; type = 1; }\n'
)


class TestUdmfRequiredFields:
    """New per-block required-field warnings."""

    def test_thing_missing_type_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nthing { x = 0.0; y = 0.0; }')
        assert any("thing" in w and "type" in w for w in m.warnings)

    def test_thing_with_type_no_required_warning(self) -> None:
        m = parse_udmf('namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 1; }')
        assert not any("missing required field 'type'" in w for w in m.warnings)

    def test_sidedef_missing_sector_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nsidedef { texturemiddle = "BRICK"; }')
        assert any("sidedef" in w and "sector" in w for w in m.warnings)

    def test_sidedef_with_sector_no_required_warning(self) -> None:
        m = parse_udmf('namespace = "doom";\nsidedef { sector = 0; }')
        assert not any("missing required field 'sector'" in w for w in m.warnings)

    def test_sector_missing_texturefloor_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nsector { textureceiling = "CEIL"; }')
        assert any("sector" in w and "texturefloor" in w for w in m.warnings)

    def test_sector_missing_textureceiling_warns(self) -> None:
        m = parse_udmf('namespace = "doom";\nsector { texturefloor = "FLAT"; }')
        assert any("sector" in w and "textureceiling" in w for w in m.warnings)

    def test_sector_with_both_textures_no_required_warning(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'sector { texturefloor = "FLAT"; textureceiling = "CEIL"; }'
        )
        assert not any("missing required field" in w for w in m.warnings)


class TestUdmfCrossReferences:
    """Geometry cross-reference integrity checks."""

    def test_linedef_v1_out_of_range(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; }\n'
            'linedef { v1 = 99; v2 = 0; sidefront = 0; }'
        )
        assert any("v1=99" in w and "out of range" in w for w in m.warnings)

    def test_linedef_v2_out_of_range(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; }\n'
            'linedef { v1 = 0; v2 = 99; sidefront = 0; }'
        )
        assert any("v2=99" in w and "out of range" in w for w in m.warnings)

    def test_linedef_sidefront_out_of_range(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; }\n'
            'vertex { x = 64.0; y = 0.0; }\n'
            'linedef { v1 = 0; v2 = 1; sidefront = 99; }'
        )
        assert any("sidefront=99" in w and "out of range" in w for w in m.warnings)

    def test_linedef_sideback_out_of_range(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; }\n'
            'vertex { x = 64.0; y = 0.0; }\n'
            'sidedef { sector = 0; }\n'
            'linedef { v1 = 0; v2 = 1; sidefront = 0; sideback = 99; }'
        )
        assert any("sideback=99" in w and "out of range" in w for w in m.warnings)

    def test_linedef_sideback_minus_one_not_flagged(self) -> None:
        """sideback = -1 means no back sidedef — must not produce a warning."""
        m = parse_udmf(_MINIMAL_DOOM_MAP)
        assert not any("sideback" in w for w in m.warnings)

    def test_sidedef_sector_out_of_range(self) -> None:
        m = parse_udmf('namespace = "doom";\nsidedef { sector = 99; }')
        assert any("sidedef" in w and "sector=99" in w and "out of range" in w for w in m.warnings)

    def test_valid_minimal_map_no_crossref_warnings(self) -> None:
        m = parse_udmf(_MINIMAL_DOOM_MAP)
        crossref = [w for w in m.warnings if "out of range" in w]
        assert not crossref


class TestUdmfNamespaceFields:
    """Namespace-specific field checks (zfloor/zceiling, arg0-arg4)."""

    def test_doom_vertex_zfloor_warns(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; zfloor = 0.0; }'
        )
        assert any("zfloor" in w and "ZDoom extension" in w for w in m.warnings)

    def test_doom_vertex_zceiling_warns(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'vertex { x = 0.0; y = 0.0; zceiling = 128.0; }'
        )
        assert any("zceiling" in w and "ZDoom extension" in w for w in m.warnings)

    def test_zdoom_vertex_zfloor_no_warning(self) -> None:
        """zdoom namespace supports z-height vertex fields — no warning."""
        m = parse_udmf(
            'namespace = "zdoom";\n'
            'vertex { x = 0.0; y = 0.0; zfloor = 0.0; }'
        )
        assert not any("zfloor" in w for w in m.warnings)

    def test_heretic_vertex_zceiling_warns(self) -> None:
        m = parse_udmf(
            'namespace = "heretic";\n'
            'vertex { x = 0.0; y = 0.0; zceiling = 64.0; }'
        )
        assert any("zceiling" in w for w in m.warnings)

    def test_doom_thing_args_warn(self) -> None:
        m = parse_udmf(
            'namespace = "doom";\n'
            'thing { x = 0.0; y = 0.0; type = 1; arg0 = 5; arg1 = 10; }'
        )
        assert any("arg0" in w and "Hexen/ZDoom" in w for w in m.warnings)

    def test_hexen_thing_args_no_warning(self) -> None:
        """hexen namespace uses arg0-arg4 on things — no warning."""
        m = parse_udmf(
            'namespace = "hexen";\n'
            'thing { x = 0.0; y = 0.0; type = 1; arg0 = 5; arg1 = 10; }'
        )
        assert not any("arg0" in w and "Hexen/ZDoom" in w for w in m.warnings)

    def test_zdoom_thing_args_no_warning(self) -> None:
        m = parse_udmf(
            'namespace = "zdoom";\n'
            'thing { x = 0.0; y = 0.0; type = 1; arg0 = 42; }'
        )
        assert not any("arg0" in w and "Hexen/ZDoom" in w for w in m.warnings)

    def test_strife_thing_args_warn(self) -> None:
        m = parse_udmf(
            'namespace = "strife";\n'
            'thing { x = 0.0; y = 0.0; type = 1; arg0 = 1; }'
        )
        assert any("arg0" in w and "Hexen/ZDoom" in w for w in m.warnings)
