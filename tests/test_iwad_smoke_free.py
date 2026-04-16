"""Smoke tests against freely-licensed IWADs committed to the repository.

These tests are NOT marked slow — the WADs are GPL/BSD and always present.
They provide feature coverage that does not require licensed content.

Coverage targets:
  - freedoom1.wad  — Freedoom Phase 1 (GPL), Doom-episode format
  - freedoom2.wad  — Freedoom Phase 2 (GPL), Doom II map format
  - blasphem.wad   — Blasphemer (BSD-3), free Heretic IWAD replacement
"""

from __future__ import annotations

import pytest

from wadlib.analysis import Severity, ValidationReport, analyze
from wadlib.wad import WadFile


def _map_by_name(wad: WadFile, name: str):  # type: ignore[return]
    for m in wad.maps:
        if m.name == name:
            return m
    return None


# ===========================================================================
# freedoom1.wad — GPL Doom-episode replacement
# ===========================================================================


class TestFreedoom1:
    def test_is_iwad(self, freedoom1_wad: WadFile) -> None:
        assert freedoom1_wad.wad_type.name == "IWAD"

    def test_lump_count(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.directory) > 1_000

    def test_episode_maps_present(self, freedoom1_wad: WadFile) -> None:
        map_names = {m.name for m in freedoom1_wad.maps}
        for ep in range(1, 5):
            assert f"E{ep}M1" in map_names, f"E{ep}M1 missing"

    def test_total_map_count(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.maps) >= 36

    def test_e1m1_things(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_e1m1_linedefs(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.lines is not None
        assert len(m.lines) > 50

    def test_e1m1_sidedefs(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.sidedefs is not None
        assert len(m.sidedefs) > 50

    def test_e1m1_sectors(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.sectors is not None
        assert len(m.sectors) > 5

    def test_e1m1_has_blockmap(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.blockmap is not None

    def test_e1m1_has_reject(self, freedoom1_wad: WadFile) -> None:
        m = _map_by_name(freedoom1_wad, "E1M1")
        assert m is not None
        assert m.reject is not None

    def test_has_playpal(self, freedoom1_wad: WadFile) -> None:
        assert freedoom1_wad.playpal is not None
        assert freedoom1_wad.playpal.num_palettes >= 14

    def test_has_colormap(self, freedoom1_wad: WadFile) -> None:
        assert freedoom1_wad.colormap is not None

    def test_has_endoom(self, freedoom1_wad: WadFile) -> None:
        assert freedoom1_wad.endoom is not None
        assert len(freedoom1_wad.endoom.raw()) == 4000

    def test_has_texture1(self, freedoom1_wad: WadFile) -> None:
        assert freedoom1_wad.get_lump("TEXTURE1") is not None

    def test_has_sounds(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.sounds) > 50

    def test_has_sprites(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.sprites) > 100

    def test_has_flats(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.flats) > 20

    def test_stcfn_font(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.stcfn) >= 64

    def test_has_music(self, freedoom1_wad: WadFile) -> None:
        assert len(freedoom1_wad.music) > 0

    @pytest.mark.slow
    def test_analyze_no_crash(self, freedoom1_wad: WadFile) -> None:
        report = analyze(freedoom1_wad)
        assert isinstance(report, ValidationReport)

    @pytest.mark.slow
    def test_analyze_no_fatal_errors(self, freedoom1_wad: WadFile) -> None:
        report = analyze(freedoom1_wad)
        fatal = [i for i in report.items if i.severity == Severity.ERROR]
        assert fatal == [], f"Unexpected fatal errors: {[i.code for i in fatal]}"


# ===========================================================================
# freedoom2.wad — GPL Doom II replacement
# ===========================================================================


class TestFreedoom2:
    def test_is_iwad(self, freedoom2_wad: WadFile) -> None:
        assert freedoom2_wad.wad_type.name == "IWAD"

    def test_lump_count(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.directory) > 2_000

    def test_maps_map_format(self, freedoom2_wad: WadFile) -> None:
        map_names = {m.name for m in freedoom2_wad.maps}
        for n in range(1, 31):
            assert f"MAP{n:02d}" in map_names, f"MAP{n:02d} missing"

    def test_map01_things(self, freedoom2_wad: WadFile) -> None:
        m = _map_by_name(freedoom2_wad, "MAP01")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_map01_linedefs(self, freedoom2_wad: WadFile) -> None:
        m = _map_by_name(freedoom2_wad, "MAP01")
        assert m is not None
        assert m.lines is not None
        assert len(m.lines) > 50

    def test_map01_sidedefs(self, freedoom2_wad: WadFile) -> None:
        m = _map_by_name(freedoom2_wad, "MAP01")
        assert m is not None
        assert m.sidedefs is not None
        assert len(m.sidedefs) > 50

    def test_map01_has_blockmap(self, freedoom2_wad: WadFile) -> None:
        m = _map_by_name(freedoom2_wad, "MAP01")
        assert m is not None
        assert m.blockmap is not None

    def test_map01_has_reject(self, freedoom2_wad: WadFile) -> None:
        m = _map_by_name(freedoom2_wad, "MAP01")
        assert m is not None
        assert m.reject is not None

    def test_has_playpal(self, freedoom2_wad: WadFile) -> None:
        assert freedoom2_wad.playpal is not None
        assert freedoom2_wad.playpal.num_palettes >= 14

    def test_has_endoom(self, freedoom2_wad: WadFile) -> None:
        assert freedoom2_wad.endoom is not None
        assert len(freedoom2_wad.endoom.raw()) == 4000

    def test_has_texture1(self, freedoom2_wad: WadFile) -> None:
        assert freedoom2_wad.get_lump("TEXTURE1") is not None

    def test_has_sounds(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.sounds) > 50

    def test_has_sprites(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.sprites) > 100

    def test_has_flats(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.flats) > 20

    def test_stcfn_font(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.stcfn) >= 64

    def test_has_music(self, freedoom2_wad: WadFile) -> None:
        assert len(freedoom2_wad.music) > 0

    @pytest.mark.slow
    def test_analyze_no_crash(self, freedoom2_wad: WadFile) -> None:
        report = analyze(freedoom2_wad)
        assert isinstance(report, ValidationReport)

    @pytest.mark.slow
    def test_analyze_no_fatal_errors(self, freedoom2_wad: WadFile) -> None:
        report = analyze(freedoom2_wad)
        fatal = [i for i in report.items if i.severity == Severity.ERROR]
        assert fatal == [], f"Unexpected fatal errors: {[i.code for i in fatal]}"


# ===========================================================================
# blasphem.wad — BSD-3 Heretic replacement
# ===========================================================================


class TestBlasphemer:
    def test_is_iwad(self, blasphemer_wad: WadFile) -> None:
        assert blasphemer_wad.wad_type.name == "IWAD"

    def test_episode_maps_present(self, blasphemer_wad: WadFile) -> None:
        map_names = {m.name for m in blasphemer_wad.maps}
        for ep in range(1, 5):
            assert f"E{ep}M1" in map_names, f"E{ep}M1 missing"

    def test_map_count(self, blasphemer_wad: WadFile) -> None:
        # Blasphemer has 5 episodes x 9 maps + secret levels
        assert len(blasphemer_wad.maps) >= 45

    def test_e1m1_things(self, blasphemer_wad: WadFile) -> None:
        m = _map_by_name(blasphemer_wad, "E1M1")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_e1m1_linedefs(self, blasphemer_wad: WadFile) -> None:
        m = _map_by_name(blasphemer_wad, "E1M1")
        assert m is not None
        assert m.lines is not None
        assert len(m.lines) > 20

    def test_e1m1_sidedefs(self, blasphemer_wad: WadFile) -> None:
        m = _map_by_name(blasphemer_wad, "E1M1")
        assert m is not None
        assert m.sidedefs is not None
        assert len(m.sidedefs) > 20

    def test_e1m1_sectors(self, blasphemer_wad: WadFile) -> None:
        m = _map_by_name(blasphemer_wad, "E1M1")
        assert m is not None
        assert m.sectors is not None
        assert len(m.sectors) > 5

    def test_has_playpal(self, blasphemer_wad: WadFile) -> None:
        assert blasphemer_wad.playpal is not None

    def test_has_colormap(self, blasphemer_wad: WadFile) -> None:
        assert blasphemer_wad.colormap is not None

    def test_fonta_glyphs(self, blasphemer_wad: WadFile) -> None:
        # Heretic/Blasphemer use FONTA for the main font
        assert len(blasphemer_wad.fonta) >= 59

    def test_has_sounds(self, blasphemer_wad: WadFile) -> None:
        assert len(blasphemer_wad.sounds) > 50

    def test_has_sprites(self, blasphemer_wad: WadFile) -> None:
        assert len(blasphemer_wad.sprites) > 50

    def test_has_flats(self, blasphemer_wad: WadFile) -> None:
        assert len(blasphemer_wad.flats) > 10

    def test_has_music(self, blasphemer_wad: WadFile) -> None:
        assert len(blasphemer_wad.music) > 0

    def test_doom_format_things(self, blasphemer_wad: WadFile) -> None:
        from wadlib.lumps.hexen import HexenThing
        from wadlib.lumps.things import Thing

        t = blasphemer_wad.maps[0].things[0]
        assert isinstance(t, Thing)
        assert not isinstance(t, HexenThing)

    @pytest.mark.slow
    def test_analyze_no_crash(self, blasphemer_wad: WadFile) -> None:
        report = analyze(blasphemer_wad)
        assert isinstance(report, ValidationReport)
