"""Tests for the DECORATE lump parser and WadFile.decorate property."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.decorate import DecorateLump, parse_decorate
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# parse_decorate — unit tests, no WAD needed
# ---------------------------------------------------------------------------


def test_parse_simple_actor() -> None:
    text = "actor ZombieMan 3001\n{\n    Health 20\n    +SOLID\n}\n"
    actors = parse_decorate(text)
    assert len(actors) == 1
    assert actors[0].name == "ZombieMan"
    assert actors[0].doomednum == 3001
    assert actors[0].health == 20
    assert "SOLID" in actors[0].flags


def test_parse_actor_with_parent() -> None:
    text = "actor FastZombie : ZombieMan 3100\n{\n    Speed 12\n}\n"
    actors = parse_decorate(text)
    assert actors[0].parent == "ZombieMan"
    assert actors[0].doomednum == 3100


def test_parse_actor_replaces() -> None:
    text = "actor MyZombie replaces ZombieMan\n{\n}\n"
    actors = parse_decorate(text)
    assert actors[0].replaces == "ZombieMan"
    assert actors[0].doomednum is None


def test_parse_actor_no_doomednum() -> None:
    text = "actor AbstractBase\n{\n}\n"
    actors = parse_decorate(text)
    assert actors[0].doomednum is None


def test_parse_multiple_actors() -> None:
    text = "actor A 100\n{\n    Health 10\n}\nactor B 200\n{\n    Health 20\n}\n"
    actors = parse_decorate(text)
    assert len(actors) == 2
    assert actors[0].name == "A"
    assert actors[1].name == "B"


def test_parse_flags_positive_negative() -> None:
    text = "actor Thing\n{\n    +SOLID\n    +SHOOTABLE\n    -FRIENDLY\n}\n"
    actors = parse_decorate(text)
    a = actors[0]
    assert "SOLID" in a.flags
    assert "SHOOTABLE" in a.flags
    assert "FRIENDLY" in a.antiflags


def test_parse_monster_keyword_sets_flag() -> None:
    text = "actor Zombie\n{\n    Monster\n}\n"
    actors = parse_decorate(text)
    assert actors[0].is_monster


def test_parse_is_item() -> None:
    text = "actor Clip 2007\n{\n    +COUNTITEM\n}\n"
    actors = parse_decorate(text)
    assert actors[0].is_item


def test_parse_comments_stripped() -> None:
    text = (
        "// This is a comment\n"
        "actor A 1\n"
        "{\n"
        "    Health 50 // inline comment\n"
        "    /* block\n"
        "       comment */\n"
        "    Speed 5\n"
        "}\n"
    )
    actors = parse_decorate(text)
    assert len(actors) == 1
    assert actors[0].health == 50


def test_parse_states_collected() -> None:
    text = (
        "actor Demon\n"
        "{\n"
        "    States\n"
        "    {\n"
        "        Spawn:\n"
        "            TROO A 10\n"
        "        See:\n"
        "            TROO B 4\n"
        "    }\n"
        "}\n"
    )
    actors = parse_decorate(text)
    assert "Spawn" in actors[0].states
    assert "See" in actors[0].states


def test_editor_numbers_dict() -> None:
    text = (
        "actor A 100\n{\n    Health 10\n}\n"
        "actor B\n{\n}\n"  # no doomednum — excluded
        "actor C 200\n{\n    Health 20\n}\n"
    )
    a = parse_decorate(text)
    ednums = {ac.doomednum: ac for ac in a if ac.doomednum is not None}
    assert 100 in ednums
    assert 200 in ednums
    assert None not in ednums


# ---------------------------------------------------------------------------
# DecorateLump via synthetic WAD
# ---------------------------------------------------------------------------


def _make_decorate_wad(decorate_text: str) -> str:
    """Build a minimal PWAD with a DECORATE lump and return its path."""
    data = decorate_text.encode("utf-8")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"DECORATE")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def test_wad_decorate_not_none() -> None:
    path = _make_decorate_wad("actor MyActor 9000\n{\n    Health 100\n}\n")
    with WadFile(path) as wad:
        assert wad.decorate is not None


def test_wad_decorate_is_decorate_lump() -> None:
    path = _make_decorate_wad("actor MyActor 9000\n{\n    Health 100\n}\n")
    with WadFile(path) as wad:
        assert isinstance(wad.decorate, DecorateLump)


def test_wad_decorate_actors_parsed() -> None:
    path = _make_decorate_wad("actor MyActor 9000\n{\n    Health 100\n}\n")
    with WadFile(path) as wad:
        assert wad.decorate is not None
        assert len(wad.decorate.actors) == 1
        assert wad.decorate.actors[0].name == "MyActor"


def test_wad_decorate_editor_numbers() -> None:
    path = _make_decorate_wad("actor MyActor 9000\n{\n    Health 100\n}\n")
    with WadFile(path) as wad:
        assert wad.decorate is not None
        assert 9000 in wad.decorate.editor_numbers
        assert wad.decorate.editor_numbers[9000].name == "MyActor"


def test_wad_decorate_none_when_absent(freedoom1_wad: WadFile) -> None:
    """A vanilla Doom WAD has no DECORATE lump."""
    assert freedoom1_wad.decorate is None


# ---------------------------------------------------------------------------
# DecorateActor properties
# ---------------------------------------------------------------------------


def test_actor_speed_property() -> None:
    text = "actor Runner\n{\n    Speed 10\n}\n"
    actors = parse_decorate(text)
    assert actors[0].speed == 10


def test_actor_radius_property() -> None:
    text = "actor Big 500\n{\n    Radius 32\n}\n"
    actors = parse_decorate(text)
    assert actors[0].radius == 32


def test_actor_height_property() -> None:
    text = "actor Tall 501\n{\n    Height 64\n}\n"
    actors = parse_decorate(text)
    assert actors[0].height == 64


def test_actor_is_monster_via_countkill() -> None:
    text = "actor Imp\n{\n    +COUNTKILL\n}\n"
    actors = parse_decorate(text)
    assert actors[0].is_monster
