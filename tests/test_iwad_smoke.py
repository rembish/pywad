"""Smoke tests against real commercial IWADs.

All tests are marked @pytest.mark.slow and gate on fixture availability.
WADs live in wads/ and are never committed (licensed content).

Coverage targets:
  - DOOM.WAD      — Ultimate Doom BFG Edition (ships as PWAD)
  - DOOM2.WAD     — Doom II v1.666
  - HERETIC.WAD   — Heretic v1.2 (3 episodes)
  - HEXEN.WAD     — Hexen retail
  - PLUTONIA.WAD  — Final Doom: The Plutonia Experiment
  - TNT.WAD       — Final Doom: TNT Evilution
  - STRIFE1.WAD   — Strife v1.2 (full, SCRIPT?? conversation lumps)
  - VOICES.WAD    — Strife voice archive
"""

from __future__ import annotations

import json

import pytest

from wadlib.analysis import Severity, ValidationReport, analyze
from wadlib.lumps.strife_conversation import ConversationLump, conversation_to_bytes
from wadlib.wad import WadFile

pytestmark = pytest.mark.slow


def _map_by_name(wad: WadFile, name: str):  # type: ignore[return]
    """Return the first map matching *name*, or None."""
    for m in wad.maps:
        if m.name == name:
            return m
    return None


# ===========================================================================
# DOOM.WAD  (BFG Edition ships as PWAD)
# ===========================================================================


class TestDoomIwad:
    def test_wad_type(self, doom1_wad: WadFile) -> None:
        # BFG Edition ships as PWAD; other editions ship as IWAD
        assert doom1_wad.wad_type.name in ("IWAD", "PWAD")

    def test_lump_count_sanity(self, doom1_wad: WadFile) -> None:
        assert len(doom1_wad.directory) > 1_000

    def test_has_playpal(self, doom1_wad: WadFile) -> None:
        assert doom1_wad.playpal is not None
        pal = doom1_wad.playpal.get_palette(0)
        assert len(pal) == 256

    def test_has_colormap(self, doom1_wad: WadFile) -> None:
        assert doom1_wad.colormap is not None
        assert doom1_wad.colormap.count == 34

    def test_episode_1_maps_present(self, doom1_wad: WadFile) -> None:
        map_names = {m.name for m in doom1_wad.maps}
        for n in range(1, 10):
            assert f"E1M{n}" in map_names, f"E1M{n} missing"

    def test_episode_4_present(self, doom1_wad: WadFile) -> None:
        map_names = {m.name for m in doom1_wad.maps}
        assert "E4M1" in map_names

    def test_total_map_count(self, doom1_wad: WadFile) -> None:
        # 4 episodes x 9 maps = 36
        assert len(doom1_wad.maps) >= 36

    def test_e1m1_has_things(self, doom1_wad: WadFile) -> None:
        m = _map_by_name(doom1_wad, "E1M1")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_e1m1_has_linedefs(self, doom1_wad: WadFile) -> None:
        m = _map_by_name(doom1_wad, "E1M1")
        assert m is not None
        assert m.lines is not None
        assert len(m.lines) > 100

    def test_e1m1_has_sectors(self, doom1_wad: WadFile) -> None:
        m = _map_by_name(doom1_wad, "E1M1")
        assert m is not None
        assert m.sectors is not None
        assert len(m.sectors) > 20

    def test_e1m1_has_vertices(self, doom1_wad: WadFile) -> None:
        m = _map_by_name(doom1_wad, "E1M1")
        assert m is not None
        assert m.vertices is not None
        assert len(m.vertices) > 100

    def test_texture1_lump_exists(self, doom1_wad: WadFile) -> None:
        lump = doom1_wad.get_lump("TEXTURE1")
        assert lump is not None
        assert len(lump.raw()) > 0

    def test_pnames_exists(self, doom1_wad: WadFile) -> None:
        assert doom1_wad.get_lump("PNAMES") is not None

    def test_has_music(self, doom1_wad: WadFile) -> None:
        assert len(doom1_wad.music) > 0


# ===========================================================================
# DOOM2.WAD
# ===========================================================================


class TestDoom2Iwad:
    def test_is_iwad(self, doom2_wad: WadFile) -> None:
        assert doom2_wad.wad_type.name == "IWAD"

    def test_lump_count_sanity(self, doom2_wad: WadFile) -> None:
        assert len(doom2_wad.directory) > 2_000

    def test_maps_map_format(self, doom2_wad: WadFile) -> None:
        map_names = {m.name for m in doom2_wad.maps}
        for n in range(1, 31):
            assert f"MAP{n:02d}" in map_names, f"MAP{n:02d} missing"

    def test_secret_levels_present(self, doom2_wad: WadFile) -> None:
        map_names = {m.name for m in doom2_wad.maps}
        assert "MAP31" in map_names  # Wolfenstein
        assert "MAP32" in map_names  # Grosse

    def test_map01_things(self, doom2_wad: WadFile) -> None:
        m = _map_by_name(doom2_wad, "MAP01")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_map01_linedefs(self, doom2_wad: WadFile) -> None:
        m = _map_by_name(doom2_wad, "MAP01")
        assert m is not None
        assert m.lines is not None
        assert len(m.lines) > 50

    def test_has_texture1(self, doom2_wad: WadFile) -> None:
        assert doom2_wad.get_lump("TEXTURE1") is not None

    def test_has_texture2(self, doom2_wad: WadFile) -> None:
        # Doom II v1.666 uses only TEXTURE1 (some ports add TEXTURE2 in PWADs)
        assert doom2_wad.get_lump("TEXTURE1") is not None

    def test_playpal_14_palettes(self, doom2_wad: WadFile) -> None:
        assert doom2_wad.playpal is not None
        assert doom2_wad.playpal.num_palettes == 14


# ===========================================================================
# HERETIC.WAD  (v1.2 registered — 3 episodes)
# ===========================================================================


class TestHereticIwad:
    def test_is_iwad(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.wad_type.name == "IWAD"

    def test_episodes_1_to_3_present(self, heretic_wad: WadFile) -> None:
        map_names = {m.name for m in heretic_wad.maps}
        for ep in range(1, 4):
            assert f"E{ep}M1" in map_names, f"E{ep}M1 missing"

    def test_map_count(self, heretic_wad: WadFile) -> None:
        # v1.2 registered: 3 episodes x 9 = 27 + optional secret E4M1
        assert len(heretic_wad.maps) >= 27

    def test_e1m1_things(self, heretic_wad: WadFile) -> None:
        m = _map_by_name(heretic_wad, "E1M1")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 10

    def test_e1m1_sectors(self, heretic_wad: WadFile) -> None:
        m = _map_by_name(heretic_wad, "E1M1")
        assert m is not None
        assert m.sectors is not None
        assert len(m.sectors) > 5

    def test_playpal(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.playpal is not None

    def test_colormap(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.colormap is not None


# ===========================================================================
# HEXEN.WAD
# ===========================================================================


class TestHexenIwad:
    def test_is_iwad(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.wad_type.name == "IWAD"

    def test_has_mapinfo(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.mapinfo is not None
        assert len(hexen_wad.mapinfo.maps) > 0

    def test_maps_present(self, hexen_wad: WadFile) -> None:
        map_names = {m.name for m in hexen_wad.maps}
        assert "MAP01" in map_names

    def test_map01_hexen_format(self, hexen_wad: WadFile) -> None:
        m = hexen_wad.maps[0]
        assert m is not None
        assert m.behavior is not None

    def test_map01_things(self, hexen_wad: WadFile) -> None:
        m = hexen_wad.maps[0]
        assert m.things is not None
        assert len(m.things) > 0

    def test_map01_linedefs(self, hexen_wad: WadFile) -> None:
        m = hexen_wad.maps[0]
        assert m.lines is not None
        assert len(m.lines) > 50

    def test_playpal(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.playpal is not None


# ===========================================================================
# PLUTONIA.WAD
# ===========================================================================


class TestPlutoniWad:
    def test_is_iwad(self, plutonia_wad: WadFile) -> None:
        assert plutonia_wad.wad_type.name == "IWAD"

    def test_maps_map_format(self, plutonia_wad: WadFile) -> None:
        map_names = {m.name for m in plutonia_wad.maps}
        for n in range(1, 31):
            assert f"MAP{n:02d}" in map_names, f"MAP{n:02d} missing"

    def test_secret_levels(self, plutonia_wad: WadFile) -> None:
        map_names = {m.name for m in plutonia_wad.maps}
        assert "MAP31" in map_names
        assert "MAP32" in map_names

    def test_map01_playable(self, plutonia_wad: WadFile) -> None:
        m = _map_by_name(plutonia_wad, "MAP01")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0
        assert m.lines is not None
        assert len(m.lines) > 0

    def test_playpal(self, plutonia_wad: WadFile) -> None:
        assert plutonia_wad.playpal is not None


# ===========================================================================
# TNT.WAD
# ===========================================================================


class TestTntWad:
    def test_is_iwad(self, tnt_wad: WadFile) -> None:
        assert tnt_wad.wad_type.name == "IWAD"

    def test_maps_map_format(self, tnt_wad: WadFile) -> None:
        map_names = {m.name for m in tnt_wad.maps}
        for n in range(1, 31):
            assert f"MAP{n:02d}" in map_names, f"MAP{n:02d} missing"

    def test_map01_playable(self, tnt_wad: WadFile) -> None:
        m = _map_by_name(tnt_wad, "MAP01")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_playpal(self, tnt_wad: WadFile) -> None:
        assert tnt_wad.playpal is not None


# ===========================================================================
# STRIFE1.WAD  — conversation data in SCRIPT?? lumps, not DIALOGUE
# ===========================================================================


class TestStrifeIwad:
    def test_is_iwad(self, strife1_wad: WadFile) -> None:
        assert strife1_wad.wad_type.name == "IWAD"

    def test_lump_count_sanity(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.directory) > 2_000

    def test_has_maps(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.maps) > 20

    def test_map01_present(self, strife1_wad: WadFile) -> None:
        m = _map_by_name(strife1_wad, "MAP01")
        assert m is not None
        assert m.things is not None
        assert len(m.things) > 0

    def test_dialogue_property_returns_script00(self, strife1_wad: WadFile) -> None:
        # Retail Strife uses SCRIPT?? naming; dialogue falls back to SCRIPT00
        dlg = strife1_wad.dialogue
        assert dlg is not None
        assert isinstance(dlg, ConversationLump)

    def test_dialogue_has_pages(self, strife1_wad: WadFile) -> None:
        dlg = strife1_wad.dialogue
        assert dlg is not None
        assert len(dlg.pages) > 0

    def test_dialogue_page_structure(self, strife1_wad: WadFile) -> None:
        dlg = strife1_wad.dialogue
        assert dlg is not None
        page = dlg.pages[0]
        assert len(page.choices) == 5

    def test_dialogue_roundtrip(self, strife1_wad: WadFile) -> None:
        """conversation_to_bytes(parsed pages) must reproduce the original bytes."""
        dlg = strife1_wad.dialogue
        assert dlg is not None
        original = dlg.raw()
        reconstructed = conversation_to_bytes(dlg.pages)
        assert reconstructed == original

    def test_playpal(self, strife1_wad: WadFile) -> None:
        assert strife1_wad.playpal is not None


# ===========================================================================
# VOICES.WAD
# ===========================================================================


class TestVoicesWad:
    def test_opens(self, voices_wad: WadFile) -> None:
        assert voices_wad is not None

    def test_has_lumps(self, voices_wad: WadFile) -> None:
        assert len(voices_wad.directory) > 0

    def test_lump_names_are_strings(self, voices_wad: WadFile) -> None:
        for entry in voices_wad.directory[:10]:
            assert isinstance(entry.name, str)


# ===========================================================================
# analyze() on real IWADs
# ===========================================================================


class TestAnalyzeRealIwads:
    def test_analyze_doom1_no_crash(self, doom1_wad: WadFile) -> None:
        report = analyze(doom1_wad)
        assert isinstance(report, ValidationReport)

    def test_analyze_doom2_no_crash(self, doom2_wad: WadFile) -> None:
        report = analyze(doom2_wad)
        assert isinstance(report, ValidationReport)

    def test_analyze_heretic_no_crash(self, heretic_wad: WadFile) -> None:
        report = analyze(heretic_wad)
        assert isinstance(report, ValidationReport)

    def test_analyze_strife_no_crash(self, strife1_wad: WadFile) -> None:
        report = analyze(strife1_wad)
        assert isinstance(report, ValidationReport)

    def test_analyze_doom1_no_fatal_errors(self, doom1_wad: WadFile) -> None:
        report = analyze(doom1_wad)
        fatal = [i for i in report.items if i.severity == Severity.ERROR]
        assert fatal == [], f"Unexpected fatal errors: {[i.code for i in fatal]}"

    def test_analyze_doom2_no_fatal_errors(self, doom2_wad: WadFile) -> None:
        report = analyze(doom2_wad)
        fatal = [i for i in report.items if i.severity == Severity.ERROR]
        assert fatal == [], f"Unexpected fatal errors: {[i.code for i in fatal]}"

    def test_analyze_report_json_serializable(self, doom1_wad: WadFile) -> None:
        report = analyze(doom1_wad)
        data = report.to_dict()
        json.dumps(data)  # must not raise
