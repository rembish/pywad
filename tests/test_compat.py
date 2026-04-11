"""Tests for compatibility level detection and conversion."""

from __future__ import annotations

import os
import tempfile

from wadlib.archive import WadArchive
from wadlib.compat import (
    CompLevel,
    CompLevelFeature,
    ConvertAction,
    check_downgrade,
    check_upgrade,
    convert_complevel,
    detect_complevel,
    detect_features,
    plan_downgrade,
)
from wadlib.lumps.animated import animated_to_bytes, AnimatedEntry
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


class TestCompLevel:
    def test_ordering(self) -> None:
        assert CompLevel.VANILLA < CompLevel.BOOM
        assert CompLevel.BOOM < CompLevel.MBF
        assert CompLevel.MBF < CompLevel.ZDOOM
        assert CompLevel.ZDOOM < CompLevel.UDMF

    def test_labels(self) -> None:
        assert CompLevel.VANILLA.label == "Vanilla Doom"
        assert CompLevel.BOOM.label == "Boom"
        assert CompLevel.UDMF.label == "UDMF"


class TestDetectVanilla:
    def test_empty_wad_is_vanilla(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
            with WadFile(path) as wad:
                assert detect_complevel(wad) == CompLevel.VANILLA
        finally:
            os.unlink(path)

    def test_basic_map_is_vanilla(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("THINGS", b"\x00" * 20, validate=False)
                wad.writestr("LINEDEFS", b"\x00" * 14, validate=False)
                wad.writestr("SIDEDEFS", b"\x00" * 30, validate=False)
                wad.writestr("VERTEXES", b"\x00" * 8, validate=False)
                wad.writestr("SECTORS", b"\x00" * 26, validate=False)
            with WadFile(path) as wad:
                assert detect_complevel(wad) == CompLevel.VANILLA
        finally:
            os.unlink(path)


class TestDetectBoom:
    def test_animated_lump(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            anim_data = animated_to_bytes([
                AnimatedEntry("flat", "NUKAGE1", "NUKAGE3", 8),
            ])
            with WadArchive(path, "w") as wad:
                wad.writestr("ANIMATED", anim_data, validate=False)
            with WadFile(path) as wad:
                level = detect_complevel(wad)
                assert level >= CompLevel.BOOM
        finally:
            os.unlink(path)


class TestDetectZDoom:
    def test_zmapinfo(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("ZMAPINFO", b"map MAP01 { }", validate=False)
            with WadFile(path) as wad:
                assert detect_complevel(wad) >= CompLevel.ZDOOM
        finally:
            os.unlink(path)

    def test_sndinfo(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("SNDINFO", b"weapons/pistol DSPISTOL", validate=False)
            with WadFile(path) as wad:
                assert detect_complevel(wad) >= CompLevel.ZDOOM
        finally:
            os.unlink(path)


class TestDetectUdmf:
    def test_textmap(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("TEXTMAP", b'namespace = "zdoom";', validate=False)
                wad.writemarker("ENDMAP")
            with WadFile(path) as wad:
                assert detect_complevel(wad) == CompLevel.UDMF
        finally:
            os.unlink(path)


class TestDowngrade:
    def test_no_issues_for_vanilla(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
            with WadFile(path) as wad:
                issues = check_downgrade(wad, CompLevel.VANILLA)
                assert len(issues) == 0
        finally:
            os.unlink(path)

    def test_boom_to_vanilla_issues(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            anim_data = animated_to_bytes([AnimatedEntry("flat", "A", "B", 8)])
            with WadArchive(path, "w") as wad:
                wad.writestr("ANIMATED", anim_data, validate=False)
            with WadFile(path) as wad:
                issues = check_downgrade(wad, CompLevel.VANILLA)
                assert len(issues) > 0
                assert any("Boom" in i.message for i in issues)
        finally:
            os.unlink(path)

    def test_boom_to_boom_no_issues(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            anim_data = animated_to_bytes([AnimatedEntry("flat", "A", "B", 8)])
            with WadArchive(path, "w") as wad:
                wad.writestr("ANIMATED", anim_data, validate=False)
            with WadFile(path) as wad:
                issues = check_downgrade(wad, CompLevel.BOOM)
                assert len(issues) == 0
        finally:
            os.unlink(path)


class TestUpgrade:
    def test_vanilla_to_boom_suggestions(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
            with WadFile(path) as wad:
                suggestions = check_upgrade(wad, CompLevel.BOOM)
                assert len(suggestions) > 0
                assert any("Boom" in s for s in suggestions)
        finally:
            os.unlink(path)

    def test_vanilla_to_udmf_suggestions(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
            with WadFile(path) as wad:
                suggestions = check_upgrade(wad, CompLevel.UDMF)
                assert len(suggestions) >= 3  # Boom + MBF + ZDoom + UDMF
        finally:
            os.unlink(path)


class TestPlanDowngrade:
    def test_plan_strip_animated(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            anim_data = animated_to_bytes([AnimatedEntry("flat", "A", "B", 8)])
            with WadArchive(path, "w") as wad:
                wad.writestr("ANIMATED", anim_data, validate=False)
            with WadFile(path) as wad:
                actions = plan_downgrade(wad, CompLevel.VANILLA)
                assert any(a.auto and "ANIMATED" in a.description for a in actions)
        finally:
            os.unlink(path)

    def test_plan_generalized_linedefs_not_auto(self) -> None:
        """Generalized Boom linedefs can't be auto-converted."""
        import struct

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        try:
            # Build a map with a generalized linedef (special >= 0x2F80)
            things = b"\x00" * 10
            # linedef with generalized special 0x3000
            linedef = struct.pack("<HHHHHhh", 0, 1, 0, 0x3000, 0, 0, -1)
            verts = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("THINGS", things, validate=False)
                wad.writestr("LINEDEFS", linedef, validate=False)
                wad.writestr("VERTEXES", verts, validate=False)
                wad.writestr("SIDEDEFS", b"\x00" * 30, validate=False)
                wad.writestr("SECTORS", b"\x00" * 26, validate=False)
            with WadFile(path) as wad:
                actions = plan_downgrade(wad, CompLevel.VANILLA)
                gen_actions = [a for a in actions if "generalized" in a.description.lower()]
                assert len(gen_actions) > 0
                assert not gen_actions[0].auto
        finally:
            os.unlink(path)


class TestConvertComplevel:
    def test_strip_animated(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            out_path = f.name
        try:
            anim_data = animated_to_bytes([AnimatedEntry("flat", "A", "B", 8)])
            with WadArchive(path, "w") as wad:
                wad.writestr("PLAYPAL", b"\x00" * (768 * 14), validate=False)
                wad.writestr("ANIMATED", anim_data, validate=False)

            with WadFile(path) as wad:
                assert detect_complevel(wad) >= CompLevel.BOOM
                result = convert_complevel(wad, CompLevel.VANILLA, out_path)
                assert any("ANIMATED" in a for a in result.applied)

            with WadFile(out_path) as wad:
                # ANIMATED should be gone
                assert wad._find_lump("ANIMATED") is None
        finally:
            os.unlink(path)
            os.unlink(out_path)

    def test_strip_zmapinfo(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            out_path = f.name
        try:
            with WadArchive(path, "w") as wad:
                wad.writestr("ZMAPINFO", b"map MAP01 {}", validate=False)

            with WadFile(path) as wad:
                result = convert_complevel(wad, CompLevel.BOOM, out_path)
                assert any("ZMAPINFO" in a for a in result.applied)

            with WadFile(out_path) as wad:
                assert wad._find_lump("ZMAPINFO") is None
        finally:
            os.unlink(path)
            os.unlink(out_path)

    def test_clear_thing_flags(self) -> None:
        import struct

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            out_path = f.name
        try:
            # Thing with NOT_DEATHMATCH flag (0x0020)
            thing = struct.pack("<hhHHH", 0, 0, 0, 1, 0x0027)  # flags = 7 | 0x0020
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("THINGS", thing, validate=False)
                wad.writestr("VERTEXES", b"\x00" * 4, validate=False)
                wad.writestr("LINEDEFS", b"", validate=False)
                wad.writestr("SIDEDEFS", b"", validate=False)
                wad.writestr("SECTORS", b"", validate=False)

            with WadFile(path) as wad:
                result = convert_complevel(wad, CompLevel.VANILLA, out_path)
                assert any("NOT_DEATHMATCH" in a for a in result.applied)

            # Verify flag was cleared
            with WadFile(out_path) as wad:
                m = wad.maps[0]
                assert m.things is not None
                t = list(m.things)[0]
                assert not (int(t.flags) & 0x0020)
                # Original flags should still be present
                assert int(t.flags) & 0x0007
        finally:
            os.unlink(path)
            os.unlink(out_path)

    def test_udmf_to_binary(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            out_path = f.name
        try:
            textmap = b'''namespace = "doom";
thing { x = 64.0; y = 128.0; type = 1; angle = 90; }
vertex { x = 0.0; y = 0.0; }
vertex { x = 256.0; y = 0.0; }
linedef { v1 = 0; v2 = 1; sidefront = 0; }
sidedef { sector = 0; texturemiddle = "BRICK1"; }
sector { heightfloor = 0; heightceiling = 128; texturefloor = "FLAT1"; textureceiling = "CEIL3_5"; lightlevel = 160; }
'''
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("TEXTMAP", textmap, validate=False)
                wad.writemarker("ENDMAP")

            with WadFile(path) as wad:
                assert detect_complevel(wad) == CompLevel.UDMF
                result = convert_complevel(wad, CompLevel.VANILLA, out_path)
                assert any("UDMF" in a for a in result.applied)

            # Should now have binary map data
            with WadFile(out_path) as wad:
                assert wad._find_lump("TEXTMAP") is None
                assert wad._find_lump("ENDMAP") is None
                m = wad.maps[0]
                assert m.things is not None
                t = list(m.things)[0]
                assert t.x == 64
                assert t.y == 128
                assert t.type == 1
        finally:
            os.unlink(path)
            os.unlink(out_path)

    def test_skipped_actions_reported(self) -> None:
        import struct

        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            path = f.name
        with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
            out_path = f.name
        try:
            linedef = struct.pack("<HHHHHhh", 0, 1, 0, 0x3000, 0, 0, -1)
            with WadArchive(path, "w") as wad:
                wad.writemarker("MAP01")
                wad.writestr("THINGS", b"\x00" * 10, validate=False)
                wad.writestr("LINEDEFS", linedef, validate=False)
                wad.writestr("VERTEXES", b"\x00" * 8, validate=False)
                wad.writestr("SIDEDEFS", b"\x00" * 30, validate=False)
                wad.writestr("SECTORS", b"\x00" * 26, validate=False)

            with WadFile(path) as wad:
                result = convert_complevel(wad, CompLevel.VANILLA, out_path)
                assert len(result.skipped) > 0
                assert any("generalized" in s.description.lower() for s in result.skipped)
        finally:
            os.unlink(path)
            os.unlink(out_path)


import pytest


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealWad:
    def test_detect_freedoom2(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            level = detect_complevel(wad)
            features = detect_features(wad)
            assert isinstance(level, CompLevel)
            for f in features:
                assert isinstance(f, CompLevelFeature)
