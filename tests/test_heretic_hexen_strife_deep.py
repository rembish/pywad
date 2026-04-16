"""Deep feature tests for Heretic, Hexen, and Strife IWAD-specific lumps.

All tests are @pytest.mark.slow and gate on commercial WAD fixtures.
These tests go beyond "does it open" — they verify that engine-specific
APIs parse meaningful content and that the data is internally consistent.

Coverage:
  - Heretic: Doom-format things, fonta glyphs as Picture, DmxSound fields,
             absence of Hexen-only lumps (MAPINFO, SNDINFO, ENDOOM)
  - Hexen:   MAPINFO entry fields + get_map(), SNDINFO logical→lump mapping,
             SNDSEQ sequences + commands, BEHAVIOR (ACS0) script directory +
             string table + disassembly, HexenThing/HexenLineDef fields
  - Strife:  strife_scripts dict completeness, ConversationPage/Choice field
             content, all-script round-trip, Doom-format things
"""

from __future__ import annotations

import pytest

from wadlib.lumps.hexen import HexenLineDef, HexenThing
from wadlib.lumps.picture import Picture
from wadlib.lumps.sound import DmxSound
from wadlib.lumps.strife_conversation import conversation_to_bytes
from wadlib.lumps.things import Flags, Thing
from wadlib.wad import WadFile

pytestmark = pytest.mark.slow


def _map_by_name(wad: WadFile, name: str):  # type: ignore[return]
    for m in wad.maps:
        if m.name == name:
            return m
    return None


# ===========================================================================
# Heretic
# ===========================================================================


class TestHereticDeep:
    # ---- Map geometry -------------------------------------------------

    def test_e1m1_thing_count(self, heretic_wad: WadFile) -> None:
        m = _map_by_name(heretic_wad, "E1M1")
        assert m is not None
        assert len(m.things) == 242

    def test_e1m1_linedef_count(self, heretic_wad: WadFile) -> None:
        assert len(_map_by_name(heretic_wad, "E1M1").lines) == 777

    def test_e1m1_sidedef_count(self, heretic_wad: WadFile) -> None:
        assert len(_map_by_name(heretic_wad, "E1M1").sidedefs) == 1033

    def test_e1m1_sector_count(self, heretic_wad: WadFile) -> None:
        assert len(_map_by_name(heretic_wad, "E1M1").sectors) == 154

    def test_e1m1_has_blockmap(self, heretic_wad: WadFile) -> None:
        assert _map_by_name(heretic_wad, "E1M1").blockmap is not None

    def test_e1m1_has_reject(self, heretic_wad: WadFile) -> None:
        assert _map_by_name(heretic_wad, "E1M1").reject is not None

    # ---- Things are Doom-format (not Hexen) ---------------------------

    def test_things_are_doom_format(self, heretic_wad: WadFile) -> None:
        t = _map_by_name(heretic_wad, "E1M1").things[0]
        assert isinstance(t, Thing)
        assert not isinstance(t, HexenThing)

    def test_thing_has_doom_fields(self, heretic_wad: WadFile) -> None:
        t = _map_by_name(heretic_wad, "E1M1").things[0]
        assert isinstance(t.type, int)
        assert isinstance(t.x, int)
        assert isinstance(t.y, int)
        assert isinstance(t.flags, Flags)

    def test_player_start_present(self, heretic_wad: WadFile) -> None:
        # Heretic player 1 start = type 1 (same as Doom)
        things = _map_by_name(heretic_wad, "E1M1").things
        assert any(t.type == 1 for t in things), "No player 1 start in E1M1"

    # ---- FONTA glyphs -------------------------------------------------

    def test_fonta_glyph_count(self, heretic_wad: WadFile) -> None:
        assert len(heretic_wad.fonta) == 59

    def test_fonta_keys_are_ascii_ordinals(self, heretic_wad: WadFile) -> None:
        for key in heretic_wad.fonta:
            assert isinstance(key, int)
            assert key >= 33, f"Key {key} is below '!' (33)"

    def test_fonta_glyphs_are_pictures(self, heretic_wad: WadFile) -> None:
        for ordinal, glyph in heretic_wad.fonta.items():
            assert isinstance(glyph, Picture), f"fonta[{ordinal}] is not a Picture"

    def test_fonta_glyphs_have_dimensions(self, heretic_wad: WadFile) -> None:
        for ordinal, glyph in heretic_wad.fonta.items():
            assert glyph.pic_width > 0, f"fonta[{ordinal}] has zero width"
            assert glyph.pic_height > 0, f"fonta[{ordinal}] has zero height"

    # ---- Sounds -------------------------------------------------------

    def test_sounds_count(self, heretic_wad: WadFile) -> None:
        assert len(heretic_wad.sounds) == 132

    def test_sounds_are_dmx(self, heretic_wad: WadFile) -> None:
        for name, snd in list(heretic_wad.sounds.items())[:10]:
            assert isinstance(snd, DmxSound), f"{name} is not DmxSound"

    def test_sound_sample_rate(self, heretic_wad: WadFile) -> None:
        snd = next(iter(heretic_wad.sounds.values()))
        assert snd.rate in (11025, 22050), f"Unexpected rate {snd.rate}"

    def test_sound_has_samples(self, heretic_wad: WadFile) -> None:
        snd = next(iter(heretic_wad.sounds.values()))
        assert snd.sample_count > 0

    def test_sound_to_wav(self, heretic_wad: WadFile) -> None:
        snd = next(iter(heretic_wad.sounds.values()))
        wav = snd.to_wav()
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"

    # ---- Sprites ------------------------------------------------------

    def test_sprites_count(self, heretic_wad: WadFile) -> None:
        assert len(heretic_wad.sprites) == 1490

    def test_sprites_are_pictures(self, heretic_wad: WadFile) -> None:
        for name, spr in list(heretic_wad.sprites.items())[:20]:
            assert isinstance(spr, Picture), f"{name} is not a Picture"

    def test_sprite_dimensions_positive(self, heretic_wad: WadFile) -> None:
        for name, spr in list(heretic_wad.sprites.items())[:20]:
            assert spr.pic_width > 0, f"{name} has zero width"
            assert spr.pic_height > 0, f"{name} has zero height"

    # ---- Hexen-only lumps absent in Heretic ---------------------------

    def test_no_mapinfo(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.mapinfo is None

    def test_no_sndinfo(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.sndinfo is None

    def test_no_endoom(self, heretic_wad: WadFile) -> None:
        assert heretic_wad.endoom is None


# ===========================================================================
# Hexen
# ===========================================================================


class TestHexenMapInfo:
    def test_entry_count(self, hexen_wad: WadFile) -> None:
        assert len(hexen_wad.mapinfo.maps) == 50

    def test_map01_title(self, hexen_wad: WadFile) -> None:
        e = hexen_wad.mapinfo.get_map(1)
        assert e is not None
        assert e.title == "WINNOWING HALL"

    def test_map01_next(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.mapinfo.get_map(1).next == 2

    def test_map01_sky(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.mapinfo.get_map(1).sky1 == "SKY2"

    def test_map01_cluster(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.mapinfo.get_map(1).cluster is not None

    def test_sky_lump_exists_in_wad(self, hexen_wad: WadFile) -> None:
        sky = hexen_wad.mapinfo.get_map(1).sky1
        assert sky is not None
        assert hexen_wad.get_lump(sky) is not None, f"Sky lump {sky!r} not found"

    def test_lightning_maps(self, hexen_wad: WadFile) -> None:
        lightning = [e for e in hexen_wad.mapinfo.maps if e.lightning]
        assert len(lightning) == 13

    def test_get_map_by_number(self, hexen_wad: WadFile) -> None:
        e = hexen_wad.mapinfo.get_map(10)
        assert e is not None
        assert e.title == "WASTELANDS"

    def test_get_map_nonexistent(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.mapinfo.get_map(999) is None

    def test_all_entries_have_titles(self, hexen_wad: WadFile) -> None:
        for e in hexen_wad.mapinfo.maps:
            assert isinstance(e.title, str)
            assert e.title != ""


class TestHexenSndInfo:
    def test_entry_count(self, hexen_wad: WadFile) -> None:
        assert len(hexen_wad.sndinfo.sounds) == 244

    def test_values_are_uppercase_lump_names(self, hexen_wad: WadFile) -> None:
        for logical, lump in hexen_wad.sndinfo.sounds.items():
            assert lump == lump.upper(), f"{logical!r} → {lump!r} not uppercase"

    def test_referenced_lumps_exist(self, hexen_wad: WadFile) -> None:
        sounds = hexen_wad.sndinfo.sounds
        # Spot-check 10 logical sound names
        for logical, lump in list(sounds.items())[:10]:
            entry = hexen_wad.get_lump(lump)
            assert entry is not None, f"SNDINFO: {logical!r} → {lump!r} not in WAD"

    def test_fighter_sounds_present(self, hexen_wad: WadFile) -> None:
        sounds = hexen_wad.sndinfo.sounds
        fighter = {k: v for k, v in sounds.items() if "Fighter" in k}
        assert len(fighter) > 0, "No fighter sounds in SNDINFO"


class TestHexenSndSeq:
    def test_sequence_count(self, hexen_wad: WadFile) -> None:
        assert len(hexen_wad.sndseq.sequences) == 13

    def test_get_platform_sequence(self, hexen_wad: WadFile) -> None:
        seq = hexen_wad.sndseq.get_sequence("Platform")
        assert seq is not None
        assert seq.name == "Platform"

    def test_get_sequence_case_insensitive(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.sndseq.get_sequence("platform") is not None

    def test_get_nonexistent_sequence(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.sndseq.get_sequence("DoesNotExist") is None

    def test_platform_commands(self, hexen_wad: WadFile) -> None:
        seq = hexen_wad.sndseq.get_sequence("Platform")
        assert len(seq.commands) == 3

    def test_command_fields(self, hexen_wad: WadFile) -> None:
        seq = hexen_wad.sndseq.get_sequence("Platform")
        cmd = seq.commands[0]
        assert isinstance(cmd.command, str) and cmd.command
        assert isinstance(cmd.sound, str) and cmd.sound

    def test_playtime_command_has_tics(self, hexen_wad: WadFile) -> None:
        # "PlatformMetal" uses playtime with a tic count
        seq = hexen_wad.sndseq.get_sequence("PlatformMetal")
        assert seq is not None
        playtime_cmds = [c for c in seq.commands if c.command == "playtime"]
        assert playtime_cmds, "Expected at least one playtime command"
        assert playtime_cmds[0].tics is not None

    def test_most_sequences_have_commands(self, hexen_wad: WadFile) -> None:
        # "Silence" is deliberately empty (plays nothing); all others must have commands
        for seq in hexen_wad.sndseq.sequences:
            if seq.name != "Silence":
                assert len(seq.commands) > 0, f"Sequence {seq.name!r} has no commands"


class TestHexenBehavior:
    def test_all_maps_have_behavior(self, hexen_wad: WadFile) -> None:
        for m in hexen_wad.maps:
            assert m.behavior is not None, f"{m.name} has no BEHAVIOR lump"

    def test_map01_format_acs0(self, hexen_wad: WadFile) -> None:
        assert hexen_wad.maps[0].behavior.format == "ACS0"

    def test_map01_script_count(self, hexen_wad: WadFile) -> None:
        assert len(hexen_wad.maps[0].behavior.scripts) == 19

    def test_map01_string_count(self, hexen_wad: WadFile) -> None:
        assert len(hexen_wad.maps[0].behavior.strings) == 11

    def test_map01_strings_content(self, hexen_wad: WadFile) -> None:
        strings = hexen_wad.maps[0].behavior.strings
        assert "GlassShatter" in strings

    def test_script_fields(self, hexen_wad: WadFile) -> None:
        script = hexen_wad.maps[0].behavior.scripts[0]
        assert isinstance(script.number, int)
        assert isinstance(script.script_type, int)
        assert isinstance(script.arg_count, int)
        assert isinstance(script.offset, int)
        assert isinstance(script.type_name, str)

    def test_script_type_names_known(self, hexen_wad: WadFile) -> None:
        known = {"closed", "open", "respawn", "death", "enter", "lightning"}
        for m in hexen_wad.maps:
            for s in m.behavior.scripts:
                # type_name must be a known name or "unknown(N)"
                assert s.type_name in known or s.type_name.startswith("unknown("), (
                    f"{m.name} script {s.number}: unexpected type_name {s.type_name!r}"
                )

    def test_disassembly_returns_string(self, hexen_wad: WadFile) -> None:
        asm = hexen_wad.maps[0].behavior.disassemble(0)
        assert isinstance(asm, str)
        assert len(asm) > 0

    def test_disassembly_contains_instructions(self, hexen_wad: WadFile) -> None:
        asm = hexen_wad.maps[0].behavior.disassemble(0)
        lines = [ln for ln in asm.splitlines() if ln.strip()]
        assert len(lines) > 5, "Disassembly is suspiciously short"

    def test_map05_has_most_scripts(self, hexen_wad: WadFile) -> None:
        m = _map_by_name(hexen_wad, "MAP05")
        assert m is not None
        assert len(m.behavior.scripts) == 48


class TestHexenThingsAndLineDefs:
    def test_map01_hexen_things(self, hexen_wad: WadFile) -> None:
        for t in list(hexen_wad.maps[0].things)[:10]:
            assert isinstance(t, HexenThing)

    def test_hexen_thing_core_fields(self, hexen_wad: WadFile) -> None:
        t = hexen_wad.maps[0].things[0]
        assert isinstance(t.type, int)
        assert isinstance(t.x, int)
        assert isinstance(t.y, int)
        assert isinstance(t.z, int)
        assert isinstance(t.tid, int)
        assert isinstance(t.angle, int)
        assert isinstance(t.flags, Flags)

    def test_hexen_thing_action_and_args(self, hexen_wad: WadFile) -> None:
        t = hexen_wad.maps[0].things[0]
        assert isinstance(t.action, int)
        for attr in ("arg0", "arg1", "arg2", "arg3", "arg4"):
            assert isinstance(getattr(t, attr), int), f"{attr} is not int"

    def test_map01_has_four_player_starts(self, hexen_wad: WadFile) -> None:
        starts = [t for t in hexen_wad.maps[0].things if t.type in (1, 2, 3, 4)]
        assert len(starts) == 4

    def test_map01_hexen_linedefs(self, hexen_wad: WadFile) -> None:
        for line in list(hexen_wad.maps[0].lines)[:10]:
            assert isinstance(line, HexenLineDef)

    def test_hexen_linedef_vertex_fields(self, hexen_wad: WadFile) -> None:
        line = hexen_wad.maps[0].lines[0]
        assert isinstance(line.start_vertex, int)
        assert isinstance(line.finish_vertex, int)
        assert line.start_vertex != line.finish_vertex

    def test_hexen_linedef_special_and_args(self, hexen_wad: WadFile) -> None:
        line = hexen_wad.maps[0].lines[0]
        assert isinstance(line.special_type, int)
        for attr in ("arg0", "arg1", "arg2", "arg3", "arg4"):
            assert isinstance(getattr(line, attr), int), f"{attr} is not int"

    def test_hexen_linedef_sidedef_refs(self, hexen_wad: WadFile) -> None:
        line = hexen_wad.maps[0].lines[0]
        # right sidedef must always exist (never -1 for valid geometry)
        assert line.right_sidedef >= 0


# ===========================================================================
# Strife
# ===========================================================================


class TestStrifeDeep:
    # ---- strife_scripts dict ------------------------------------------

    def test_script_lump_count(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.strife_scripts) == 23

    def test_script_keys_are_script_names(self, strife1_wad: WadFile) -> None:
        for key in strife1_wad.strife_scripts:
            assert key.startswith("SCRIPT"), f"Unexpected key: {key}"

    def test_script00_page_count(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.strife_scripts["SCRIPT00"].pages) == 42

    def test_script02_is_largest(self, strife1_wad: WadFile) -> None:
        # SCRIPT02 has 70 pages — the most of any script lump
        assert len(strife1_wad.strife_scripts["SCRIPT02"].pages) == 70

    def test_total_conversation_pages(self, strife1_wad: WadFile) -> None:
        total = sum(len(lump.pages) for lump in strife1_wad.strife_scripts.values())
        assert total >= 390

    def test_scripts_are_sorted(self, strife1_wad: WadFile) -> None:
        keys = list(strife1_wad.strife_scripts)
        assert keys == sorted(keys)

    # ---- ConversationPage content -------------------------------------

    def test_page_speaker_id_is_int(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        assert isinstance(p.speaker_id, int)

    def test_page_name_is_string(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        assert isinstance(p.name, str)

    def test_page_text_is_string(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        assert isinstance(p.text, str)

    def test_page_always_has_five_choices(self, strife1_wad: WadFile) -> None:
        for lump in strife1_wad.strife_scripts.values():
            for page in lump.pages:
                assert len(page.choices) == 5, (
                    f"Page in {lump.name!r} has {len(page.choices)} choices"
                )

    def test_page_name_content(self, strife1_wad: WadFile) -> None:
        # SCRIPT00 page 0 is a generic peasant dialogue
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        assert p.name == "PEASANT"

    # ---- ConversationChoice content ----------------------------------

    def test_choice_give_item_is_int(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        for c in p.choices:
            assert isinstance(c.give_item, int)

    def test_choice_text_is_string(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        for c in p.choices:
            assert isinstance(c.text, str)

    def test_choice_next_is_int(self, strife1_wad: WadFile) -> None:
        p = strife1_wad.strife_scripts["SCRIPT00"].pages[0]
        for c in p.choices:
            assert isinstance(c.next, int)

    # ---- Round-trip --------------------------------------------------

    def test_all_scripts_round_trip(self, strife1_wad: WadFile) -> None:
        """conversation_to_bytes must reproduce raw bytes for every SCRIPT lump."""
        for name, lump in strife1_wad.strife_scripts.items():
            original = lump.raw()
            reconstructed = conversation_to_bytes(lump.pages)
            assert reconstructed == original, (
                f"{name}: round-trip failed "
                f"(orig={len(original)} bytes, got={len(reconstructed)} bytes)"
            )

    # ---- Things are Doom-format (Strife does not use HexenThing) -----

    def test_strife_things_doom_format(self, strife1_wad: WadFile) -> None:
        m = _map_by_name(strife1_wad, "MAP01")
        assert m is not None
        for t in list(m.things)[:10]:
            assert isinstance(t, Thing)
            assert not isinstance(t, HexenThing)

    # ---- Sound and sprite sanity -------------------------------------

    def test_sounds_count(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.sounds) == 135

    def test_sprites_count(self, strife1_wad: WadFile) -> None:
        assert len(strife1_wad.sprites) == 2004
