"""Tests for compatibility level detection and conversion."""

from __future__ import annotations

import os
import tempfile

from wadlib.archive import WadArchive
from wadlib.compat import (
    CompLevel,
    CompLevelFeature,
    check_downgrade,
    check_upgrade,
    detect_complevel,
    detect_features,
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


import pytest


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestRealWad:
    def test_detect_freedoom2(self) -> None:
        with WadFile(FREEDOOM2) as wad:
            level = detect_complevel(wad)
            features = detect_features(wad)
            # freedoom2 should be detectable
            assert isinstance(level, CompLevel)
            # Print for visibility
            for f in features:
                assert isinstance(f, CompLevelFeature)
