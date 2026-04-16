"""Unit tests for DEHACKED parser — pointer blocks and cheat codes."""

from __future__ import annotations

from wadlib.lumps.dehacked.parser import parse_dehacked

# ---------------------------------------------------------------------------
# Pointer block storage
# ---------------------------------------------------------------------------

_POINTER_PATCH = """\
Doom version = 19
Patch format = 6

Pointer 162 (Frame 162)
Codep Frame = 219

Pointer 163 (Frame 163)
Codep Frame = 220
"""


class TestDehackedPointers:
    def test_pointer_block_stored(self) -> None:
        patch = parse_dehacked(_POINTER_PATCH)
        assert 162 in patch.pointers
        assert patch.pointers[162] == 219

    def test_multiple_pointers(self) -> None:
        patch = parse_dehacked(_POINTER_PATCH)
        assert patch.pointers[162] == 219
        assert patch.pointers[163] == 220

    def test_pointer_default_empty(self) -> None:
        patch = parse_dehacked("")
        assert patch.pointers == {}

    def test_pointer_index_zero(self) -> None:
        text = "Pointer 0 (Frame 0)\nCodep Frame = 5\n\n"
        patch = parse_dehacked(text)
        assert patch.pointers[0] == 5

    def test_pointer_non_integer_codep_ignored(self) -> None:
        text = "Pointer 1 (Frame 1)\nCodep Frame = bad\n\n"
        patch = parse_dehacked(text)
        assert 1 not in patch.pointers

    def test_pointer_does_not_affect_frames(self) -> None:
        patch = parse_dehacked(_POINTER_PATCH)
        assert patch.frames == {}


# ---------------------------------------------------------------------------
# [CHEATS] section parsing
# ---------------------------------------------------------------------------

_CHEATS_PATCH = """\
Doom version = 19
Patch format = 6

[CHEATS]
IDDQD = god
IDKFA = idkfa
IDFA = idfa
"""


class TestDehackedCheats:
    def test_cheat_keys_parsed(self) -> None:
        patch = parse_dehacked(_CHEATS_PATCH)
        assert "IDDQD" in patch.cheats
        assert patch.cheats["IDDQD"] == "god"

    def test_multiple_cheats(self) -> None:
        patch = parse_dehacked(_CHEATS_PATCH)
        assert patch.cheats["IDKFA"] == "idkfa"
        assert patch.cheats["IDFA"] == "idfa"

    def test_cheats_default_empty(self) -> None:
        patch = parse_dehacked("")
        assert patch.cheats == {}

    def test_cheats_does_not_affect_other_blocks(self) -> None:
        patch = parse_dehacked(_CHEATS_PATCH)
        assert patch.all_things == {}
        assert patch.frames == {}

    def test_cheats_section_stops_at_next_section(self) -> None:
        text = "[CHEATS]\nIDDQD = god\n\n[STRINGS]\nGOTARMOR = Got armor!\n"
        patch = parse_dehacked(text)
        assert patch.cheats == {"IDDQD": "god"}
        assert patch.bex_strings == {"GOTARMOR": "Got armor!"}

    def test_cheat_comment_lines_skipped(self) -> None:
        text = "[CHEATS]\n# This is a comment\nIDDQD = god\n"
        patch = parse_dehacked(text)
        assert patch.cheats == {"IDDQD": "god"}

    def test_cheat_blank_lines_skipped(self) -> None:
        text = "[CHEATS]\n\nIDDQD = god\n\nIDKFA = idkfa\n"
        patch = parse_dehacked(text)
        assert "IDDQD" in patch.cheats
        assert "IDKFA" in patch.cheats


# ---------------------------------------------------------------------------
# Combined — pointer and cheats alongside existing block types
# ---------------------------------------------------------------------------


_COMBINED_PATCH = """\
Doom version = 19
Patch format = 6

Thing 1 (ZombieMan)
Bits = 4194310

Frame 100
Duration = 8

Pointer 100 (Frame 100)
Codep Frame = 101

[CHEATS]
IDDQD = god
"""


class TestDehackedCombined:
    def test_all_block_types_coexist(self) -> None:
        patch = parse_dehacked(_COMBINED_PATCH)
        assert patch.doom_version == 19
        assert 1 in patch.all_things
        assert 100 in patch.frames
        assert patch.pointers[100] == 101
        assert patch.cheats["IDDQD"] == "god"
