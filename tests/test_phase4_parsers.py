"""Phase 4 parser maturity tests — ZMAPINFO, UDMF, TEXTURES, DECORATE."""

from __future__ import annotations

import pytest

from wadlib.lumps.decorate import DecorateLump
from wadlib.lumps.texturex import TexturesDef, TexturesPatch, parse_textures, serialize_textures
from wadlib.lumps.udmf import UdmfParseError, parse_udmf
from wadlib.lumps.zmapinfo import ZMapInfoLump
from wadlib.source import MemoryLumpSource

# ---------------------------------------------------------------------------
# ZMAPINFO helpers
# ---------------------------------------------------------------------------


def _zmapinfo_lump(text: str) -> ZMapInfoLump:
    data = text.encode("latin-1")
    src = MemoryLumpSource("ZMAPINFO", data)
    return ZMapInfoLump(entry=src)


def _decorate_lump(text: str) -> DecorateLump:
    data = text.encode("utf-8")
    src = MemoryLumpSource("DECORATE", data)
    return DecorateLump(entry=src)


# ---------------------------------------------------------------------------
# ZMAPINFO — props catch-all
# ---------------------------------------------------------------------------


class TestZMapInfoProps:
    def test_unknown_key_goes_to_props(self):
        lump = _zmapinfo_lump('map MAP01 "Test"\n{\n    levelnum = 1\n    nointermission\n}\n')
        entry = lump.maps[0]
        assert entry.map_name == "MAP01"
        assert entry.levelnum == 1
        assert "nointermission" in entry.props

    def test_multiple_unknown_keys(self):
        lump = _zmapinfo_lump(
            'map E1M1 "Episode 1"\n{\n    fogdensity = 128\n    gravity = 800\n}\n'
        )
        entry = lump.maps[0]
        assert entry.props["fogdensity"] == "128"
        assert entry.props["gravity"] == "800"

    def test_known_keys_not_in_props(self):
        lump = _zmapinfo_lump('map MAP02 "Test"\n{\n    next = "MAP03"\n    sky1 = "SKY1"\n}\n')
        entry = lump.maps[0]
        assert entry.next == "MAP03"
        assert entry.sky1 == "SKY1"
        assert "next" not in entry.props
        assert "sky1" not in entry.props


# ---------------------------------------------------------------------------
# ZMAPINFO — episode blocks
# ---------------------------------------------------------------------------


class TestZMapInfoEpisode:
    def test_episode_basic(self):
        lump = _zmapinfo_lump(
            'episode E1M1 "Knee-Deep in the Dead"\n{\n    picname = "M_EPI1"\n    key = "k"\n}\n'
        )
        assert len(lump.episodes) == 1
        ep = lump.episodes[0]
        assert ep.map == "E1M1"
        assert ep.name == "Knee-Deep in the Dead"
        assert ep.pic_name == "M_EPI1"
        assert ep.key == "k"

    def test_episode_lookup_name(self):
        lump = _zmapinfo_lump('episode E1M1 lookup "HUSTR_E1"\n{\n    picname = "M_EPI1"\n}\n')
        ep = lump.episodes[0]
        assert ep.name == ""
        assert ep.name_lookup == "HUSTR_E1"

    def test_episode_noskillmenu(self):
        lump = _zmapinfo_lump('episode E1M1 "Test"\n{\n    noskillmenu\n}\n')
        assert lump.episodes[0].no_skill_menu is True

    def test_multiple_episodes(self):
        lump = _zmapinfo_lump('episode E1M1 "Ep1"\n{\n}\nepisode E2M1 "Ep2"\n{\n}\n')
        assert len(lump.episodes) == 2
        assert lump.episodes[0].map == "E1M1"
        assert lump.episodes[1].map == "E2M1"


# ---------------------------------------------------------------------------
# ZMAPINFO — cluster blocks
# ---------------------------------------------------------------------------


class TestZMapInfoCluster:
    def test_cluster_basic(self):
        lump = _zmapinfo_lump(
            'cluster 1\n{\n    exittext = "You finished!"\n    music = "D_VICTOR"\n}\n'
        )
        assert len(lump.clusters) == 1
        cl = lump.clusters[0]
        assert cl.cluster_num == 1
        assert cl.exittext == "You finished!"
        assert cl.music == "D_VICTOR"

    def test_cluster_islump_flags(self):
        lump = _zmapinfo_lump(
            "cluster 2\n{\n"
            '    exittext = "ENDTEXT"\n    exittextislump\n'
            '    entertext = "INTRO"\n    entertextislump\n}\n'
        )
        cl = lump.clusters[0]
        assert cl.exittextislump is True
        assert cl.entertextislump is True

    def test_cluster_flat(self):
        lump = _zmapinfo_lump('cluster 3\n{\n    flat = "INTERPIC"\n}\n')
        assert lump.clusters[0].flat == "INTERPIC"


# ---------------------------------------------------------------------------
# ZMAPINFO — defaultmap baseline
# ---------------------------------------------------------------------------


class TestZMapInfoDefaultmap:
    def test_defaultmap_baseline_applied(self):
        lump = _zmapinfo_lump(
            'defaultmap\n{\n    sky1 = "SKY1"\n    music = "D_RUNNIN"\n}\n'
            'map MAP01 "Test"\n{\n    levelnum = 1\n}\n'
        )
        entry = lump.maps[0]
        assert entry.sky1 == "SKY1"
        assert entry.music == "D_RUNNIN"
        assert entry.levelnum == 1

    def test_map_overrides_defaultmap(self):
        lump = _zmapinfo_lump(
            'defaultmap\n{\n    sky1 = "SKY1"\n    music = "D_RUNNIN"\n}\n'
            'map MAP01 "Test"\n{\n    sky1 = "SKY2"\n}\n'
        )
        entry = lump.maps[0]
        assert entry.sky1 == "SKY2"
        assert entry.music == "D_RUNNIN"

    def test_defaultmap_property(self):
        lump = _zmapinfo_lump('defaultmap\n{\n    sky1 = "SKY1"\n}\n')
        assert lump.defaultmap is not None
        assert lump.defaultmap.sky1 == "SKY1"

    def test_no_defaultmap_returns_none(self):
        lump = _zmapinfo_lump('map MAP01 "Test"\n{\n}\n')
        assert lump.defaultmap is None

    def test_defaultmap_does_not_appear_in_maps(self):
        lump = _zmapinfo_lump('defaultmap\n{\n    sky1 = "SKY1"\n}\nmap MAP01 "Test"\n{\n}\n')
        assert len(lump.maps) == 1
        assert lump.maps[0].map_name == "MAP01"


# ---------------------------------------------------------------------------
# UDMF — UdmfParseError + strict mode
# ---------------------------------------------------------------------------


class TestUdmfParseError:
    def test_importable_from_top_level(self):
        from wadlib import UdmfParseError as E

        assert E is UdmfParseError

    def test_is_value_error_subclass(self):
        assert issubclass(UdmfParseError, ValueError)

    def test_strict_missing_namespace_raises(self):
        text = "thing { x = 0.0; y = 0.0; type = 1; }"
        with pytest.raises(UdmfParseError, match="namespace"):
            parse_udmf(text, strict=True)

    def test_strict_empty_text_no_raise(self):
        parse_udmf("", strict=True)
        parse_udmf("   \n  ", strict=True)

    def test_strict_valid_text_no_raise(self):
        text = 'namespace = "doom";\nthing { x = 0.0; y = 0.0; type = 1; }'
        result = parse_udmf(text, strict=True)
        assert result.namespace == "doom"
        assert len(result.things) == 1

    def test_non_strict_missing_namespace_no_raise(self):
        text = "thing { x = 0.0; y = 0.0; type = 1; }"
        result = parse_udmf(text, strict=False)
        assert result.namespace == "doom"  # default unchanged


# ---------------------------------------------------------------------------
# TEXTURES — translation / blend / raw_props
# ---------------------------------------------------------------------------


class TestTexturesPatchFields:
    def test_default_empty_fields(self):
        p = TexturesPatch(name="FOO")
        assert p.translation == ""
        assert p.blend == ""
        assert p.raw_props == {}

    def test_translation_parsed(self):
        text = (
            'Texture "MYBRICK", 64, 64\n{\n'
            '    Patch "WALL00_1", 0, 0\n    {\n'
            '        Translation "0:255=128:255"\n'
            "    }\n}\n"
        )
        defs = parse_textures(text)
        patch = defs[0].patches[0]
        assert patch.translation == '"0:255=128:255"'

    def test_blend_parsed(self):
        text = (
            'Texture "MYWALL", 64, 64\n{\n'
            '    Patch "WALL00_1", 0, 0\n    {\n'
            '        Blend "ff0000", 0.5\n'
            "    }\n}\n"
        )
        defs = parse_textures(text)
        patch = defs[0].patches[0]
        assert patch.blend == '"ff0000", 0.5'

    def test_raw_props_catches_unknown(self):
        text = (
            'Texture "TEST", 64, 64\n{\n'
            '    Patch "WALL00_1", 0, 0\n    {\n'
            "        UseWorldPanning\n"
            "    }\n}\n"
        )
        defs = parse_textures(text)
        patch = defs[0].patches[0]
        assert "useworldpanning" in patch.raw_props

    def test_serializer_emits_translation(self):
        p = TexturesPatch(name="WALL", x=0, y=0, translation="0:255=64:255")
        td = TexturesDef(kind="texture", name="TEST", width=64, height=64, patches=[p])
        out = serialize_textures([td])
        assert "Translation 0:255=64:255" in out

    def test_serializer_emits_blend(self):
        p = TexturesPatch(name="WALL", x=0, y=0, blend="red")
        td = TexturesDef(kind="texture", name="TEST", width=64, height=64, patches=[p])
        out = serialize_textures([td])
        assert "Blend red" in out

    def test_serializer_plain_patch_no_block(self):
        p = TexturesPatch(name="WALL", x=0, y=0)
        td = TexturesDef(kind="texture", name="TEST", width=64, height=64, patches=[p])
        out = serialize_textures([td])
        # No inner braces for a plain patch — only the outer texture { }
        stripped = [line.strip() for line in out.splitlines()]
        inner_braces = [line for line in stripped if line in ("{", "}")]
        assert len(inner_braces) == 2

    def test_raw_props_emitted_in_serializer(self):
        p = TexturesPatch(name="WALL", x=0, y=0)
        p.raw_props["useworldpanning"] = "UseWorldPanning"
        td = TexturesDef(kind="texture", name="TEST", width=64, height=64, patches=[p])
        out = serialize_textures([td])
        assert "UseWorldPanning" in out


# ---------------------------------------------------------------------------
# DECORATE — includes / replacements
# ---------------------------------------------------------------------------


class TestDecorateLumpIncludes:
    def test_collects_includes(self):
        text = (
            '#include "actors/monsters.dec"\n'
            '#include "actors/weapons.dec"\n'
            "Actor MyThing 9001\n{\n}\n"
        )
        lump = _decorate_lump(text)
        assert lump.includes == ["actors/monsters.dec", "actors/weapons.dec"]

    def test_no_includes(self):
        text = "Actor MyThing 9001\n{\n}\n"
        lump = _decorate_lump(text)
        assert lump.includes == []

    def test_includes_not_in_line_comments(self):
        text = '// #include "commented_out.dec"\n#include "real.dec"\n'
        lump = _decorate_lump(text)
        assert lump.includes == ["real.dec"]

    def test_includes_not_in_block_comments(self):
        text = '/* #include "nope.dec" */\n#include "yes.dec"\n'
        lump = _decorate_lump(text)
        assert lump.includes == ["yes.dec"]


class TestDecorateLumpReplacements:
    def test_replacements_mapping(self):
        text = (
            "Actor MyZombie replaces ZombieMan 9001\n{\n}\n"
            "Actor MyImp replaces DoomImp 9002\n{\n}\n"
        )
        lump = _decorate_lump(text)
        assert lump.replacements == {
            "ZombieMan": "MyZombie",
            "DoomImp": "MyImp",
        }

    def test_no_replacements(self):
        text = "Actor MyThing 9001\n{\n}\n"
        lump = _decorate_lump(text)
        assert lump.replacements == {}

    def test_only_replacing_actors_in_dict(self):
        text = "Actor Foo 9001\n{\n}\nActor Bar replaces Baz 9002\n{\n}\n"
        lump = _decorate_lump(text)
        assert lump.replacements == {"Baz": "Bar"}
