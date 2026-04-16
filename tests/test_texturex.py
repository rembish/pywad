"""Tests for ZDoom TEXTURES lump parser."""

from wadlib.lumps.texturex import TexturesDef, TexturesPatch, parse_textures, serialize_textures

_SIMPLE = """
Texture "MYBRICK", 128, 64
{
    Patch "WALL00_1", 0, 0
    Patch "WALL00_2", 64, 0
}
"""

_WITH_PROPS = """
Texture "FANCY", 256, 128
{
    Offset 10, 20
    XScale 2.0
    YScale 0.5
    WorldPanning
    Patch "BASE", 0, 0
    Patch "OVERLAY", 0, 0
    {
        FlipX
        Alpha 0.5
        Style Translucent
    }
}
"""

_FLAT = """
Flat "MYFLOOR", 64, 64
{
    Patch "FLAT01", 0, 0
}
"""

_SPRITE = """
Sprite "MYSPRITE", 32, 56
{
    Offset 16, 55
    Patch "TROOA1", 0, 0
}
"""


class TestParse:
    def test_simple(self) -> None:
        defs = parse_textures(_SIMPLE)
        assert len(defs) == 1
        assert defs[0].name == "MYBRICK"
        assert defs[0].width == 128
        assert defs[0].height == 64
        assert defs[0].kind == "texture"
        assert len(defs[0].patches) == 2
        assert defs[0].patches[0].name == "WALL00_1"
        assert defs[0].patches[1].name == "WALL00_2"
        assert defs[0].patches[1].x == 64

    def test_with_properties(self) -> None:
        defs = parse_textures(_WITH_PROPS)
        assert len(defs) == 1
        t = defs[0]
        assert t.x_offset == 10
        assert t.y_offset == 20
        assert t.x_scale == 2.0
        assert t.y_scale == 0.5
        assert t.world_panning
        assert len(t.patches) == 2
        overlay = t.patches[1]
        assert overlay.flip_x
        assert overlay.alpha == 0.5
        assert overlay.style == "Translucent"

    def test_flat(self) -> None:
        defs = parse_textures(_FLAT)
        assert len(defs) == 1
        assert defs[0].kind == "flat"
        assert defs[0].width == 64

    def test_sprite(self) -> None:
        defs = parse_textures(_SPRITE)
        assert len(defs) == 1
        assert defs[0].kind == "sprite"
        assert defs[0].x_offset == 16
        assert defs[0].y_offset == 55

    def test_multiple(self) -> None:
        text = _SIMPLE + _FLAT + _SPRITE
        defs = parse_textures(text)
        assert len(defs) == 3

    def test_comments(self) -> None:
        text = """
// This is a comment
Texture "TEST", 64, 64
{
    // Another comment
    Patch "P1", 0, 0
}
"""
        defs = parse_textures(text)
        assert len(defs) == 1

    def test_empty(self) -> None:
        assert parse_textures("") == []
        assert parse_textures("// just comments") == []


class TestSerialize:
    def test_round_trip(self) -> None:
        defs = parse_textures(_SIMPLE)
        text = serialize_textures(defs)
        defs2 = parse_textures(text)
        assert len(defs2) == 1
        assert defs2[0].name == defs[0].name
        assert defs2[0].width == defs[0].width
        assert len(defs2[0].patches) == len(defs[0].patches)

    def test_round_trip_with_props(self) -> None:
        defs = parse_textures(_WITH_PROPS)
        text = serialize_textures(defs)
        defs2 = parse_textures(text)
        assert defs2[0].world_panning
        assert defs2[0].patches[1].flip_x

    def test_serialize_empty(self) -> None:
        assert serialize_textures([]) == ""

    def test_serialize_from_scratch(self) -> None:
        d = TexturesDef(
            kind="texture",
            name="NEW",
            width=64,
            height=64,
            patches=[TexturesPatch(name="P1", x=0, y=0)],
        )
        text = serialize_textures([d])
        assert 'Texture "NEW", 64, 64' in text
        assert '"P1"' in text


# ---------------------------------------------------------------------------
# TexturesDef.raw_props — texture-level unknown properties
# ---------------------------------------------------------------------------


class TestTexturesDefRawProps:
    def test_default_empty(self) -> None:
        d = TexturesDef(kind="texture", name="T", width=64, height=64)
        assert d.raw_props == {}

    def test_unknown_texture_level_line_captured(self) -> None:
        text = 'Texture "TEST", 64, 64\n{\n    NullTexture\n    Patch "P1", 0, 0\n}\n'
        defs = parse_textures(text)
        assert len(defs) == 1
        assert "nulltexture" in defs[0].raw_props
        assert defs[0].raw_props["nulltexture"] == "NullTexture"

    def test_multiple_unknown_texture_props(self) -> None:
        text = (
            'Texture "TEST", 64, 64\n{\n    NullTexture\n    Brightmap\n    Patch "P1", 0, 0\n}\n'
        )
        defs = parse_textures(text)
        assert "nulltexture" in defs[0].raw_props
        assert "brightmap" in defs[0].raw_props

    def test_known_props_not_in_raw(self) -> None:
        text = (
            'Texture "TEST", 64, 64\n{\n'
            "    WorldPanning\n"
            "    Optional\n"
            "    NoDecals\n"
            '    Patch "P1", 0, 0\n'
            "}\n"
        )
        defs = parse_textures(text)
        assert defs[0].raw_props == {}

    def test_serializer_emits_texture_raw_props(self) -> None:
        d = TexturesDef(
            kind="texture",
            name="TEST",
            width=64,
            height=64,
            raw_props={"nulltexture": "NullTexture", "brightmap": "Brightmap"},
        )
        text = serialize_textures([d])
        assert "NullTexture" in text
        assert "Brightmap" in text

    def test_texture_raw_props_round_trip(self) -> None:
        text = 'Texture "TEST", 64, 64\n{\n    NullTexture\n    Patch "P1", 0, 0\n}\n'
        defs = parse_textures(text)
        out = serialize_textures(defs)
        defs2 = parse_textures(out)
        assert "nulltexture" in defs2[0].raw_props
