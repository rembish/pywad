"""Tests for the DECORATE lump parser and WadFile.decorate property."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.decorate import DecorateLump, parse_decorate, resolve_inheritance
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


# ---------------------------------------------------------------------------
# resolve_inheritance
# ---------------------------------------------------------------------------


def test_resolve_no_parent() -> None:
    """Actors without a parent are returned unchanged."""
    actors = parse_decorate("actor Base\n{\n    health 100\n    +SOLID\n}\n")
    resolved = resolve_inheritance(actors)
    assert resolved[0].health == 100
    assert "SOLID" in resolved[0].flags


def test_resolve_inherits_property() -> None:
    """Child inherits a property not overridden in its own definition."""
    text = "actor Base\n{\n    health 200\n    speed 8\n}\nactor Child : Base\n{\n    speed 4\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert child.health == 200  # inherited
    assert child.speed == 4  # overridden


def test_resolve_child_overrides_property() -> None:
    """Child property wins over parent property."""
    text = "actor Base\n{\n    health 100\n}\nactor Child : Base\n{\n    health 50\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert child.health == 50


def test_resolve_inherits_flags() -> None:
    """Child inherits parent flags not explicitly set or cleared."""
    text = (
        "actor Base\n{\n    +SOLID\n    +SHOOTABLE\n}\nactor Child : Base\n{\n    +COUNTKILL\n}\n"
    )
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert "SOLID" in child.flags  # inherited
    assert "SHOOTABLE" in child.flags  # inherited
    assert "COUNTKILL" in child.flags  # own


def test_resolve_antiflag_clears_parent_flag() -> None:
    """A child -FLAG removes the parent's +FLAG."""
    text = "actor Base\n{\n    +SOLID\n}\nactor Child : Base\n{\n    -SOLID\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert "SOLID" not in child.flags


def test_resolve_inherits_doomednum() -> None:
    """Child inherits doomednum from parent when child has none."""
    text = "actor Base 3001\n{\n    health 60\n}\nactor Child : Base\n{\n    health 30\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert child.doomednum == 3001


def test_resolve_child_doomednum_wins() -> None:
    """Child doomednum takes precedence over parent."""
    text = "actor Base 3001\n{\n}\nactor Child : Base 9000\n{\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    child = next(a for a in resolved if a.name == "Child")
    assert child.doomednum == 9000


def test_resolve_unknown_parent_unchanged() -> None:
    """An actor whose parent is not in the list is returned as-is."""
    text = "actor Child : SomeEngineClass\n{\n    health 50\n}\n"
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    assert resolved[0].health == 50
    assert resolved[0].parent == "SomeEngineClass"


def test_resolve_deep_chain() -> None:
    """Properties propagate through a three-level chain correctly."""
    text = (
        "actor A\n{\n    health 100\n    speed 4\n}\n"
        "actor B : A\n{\n    speed 8\n    radius 20\n}\n"
        "actor C : B\n{\n    radius 30\n}\n"
    )
    actors = parse_decorate(text)
    resolved = resolve_inheritance(actors)
    c = next(a for a in resolved if a.name == "C")
    assert c.health == 100  # from A via B
    assert c.speed == 8  # from B
    assert c.radius == 30  # own


def test_resolve_does_not_mutate_originals() -> None:
    """resolve_inheritance must not modify the original actor objects."""
    text = "actor Base\n{\n    health 100\n}\nactor Child : Base\n{\n}\n"
    actors = parse_decorate(text)
    original_child_health = actors[1].health
    resolve_inheritance(actors)
    assert actors[1].health == original_child_health  # unchanged
