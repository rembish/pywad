"""Tests for demo serialization, DECORATE, ACS BEHAVIOR, and GL nodes."""

from __future__ import annotations

import struct

import pytest

# ---------------------------------------------------------------------------
# Demo serialization
# ---------------------------------------------------------------------------

from wadlib.lumps.demo import Demo, DemoHeader, DemoTic, parse_demo


class TestDemoSerialization:
    def _make_demo(self, tics: list[tuple[int, int, int, int]]) -> bytes:
        header = bytes([109, 2, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0])
        body = b""
        for fwd, side, turn, buttons in tics:
            body += struct.pack("bbbB", fwd, side, turn, buttons)
        body += b"\x80"
        return header + body

    def test_round_trip(self) -> None:
        orig = self._make_demo([(50, 10, -5, 1), (0, 0, 0, 2)])
        demo = parse_demo(orig)
        rebuilt = demo.to_bytes()
        demo2 = parse_demo(rebuilt)
        assert demo2.duration_tics == demo.duration_tics
        assert demo2.tics[0][0].forwardmove == 50
        assert demo2.tics[0][0].sidemove == 10
        assert demo2.tics[1][0].buttons == 2

    def test_empty_demo_round_trip(self) -> None:
        orig = self._make_demo([])
        demo = parse_demo(orig)
        rebuilt = demo.to_bytes()
        assert rebuilt[-1] == 0x80  # end marker

    def test_header_preserved(self) -> None:
        orig = self._make_demo([(0, 0, 0, 0)])
        demo = parse_demo(orig)
        rebuilt = demo.to_bytes()
        demo2 = parse_demo(rebuilt)
        assert demo2.header.version == 109
        assert demo2.header.skill == 2
        assert demo2.header.episode == 1
        assert demo2.header.map == 1

    def test_longtics_round_trip(self) -> None:
        header = bytes([111, 2, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0])
        body = struct.pack("<bbhB", 50, 0, 1000, 0)
        body += b"\x80"
        demo = parse_demo(header + body)
        rebuilt = demo.to_bytes()
        demo2 = parse_demo(rebuilt)
        assert demo2.tics[0][0].angleturn == 1000

    def test_tic_to_bytes(self) -> None:
        tic = DemoTic(50, -10, 5, 3)
        raw = tic.to_bytes()
        assert len(raw) == 4
        raw_long = tic.to_bytes(longtics=True)
        assert len(raw_long) == 5


# ---------------------------------------------------------------------------
# DECORATE parser
# ---------------------------------------------------------------------------

from wadlib.lumps.decorate import DecorateActor, parse_decorate


class TestDecorate:
    def test_simple_actor(self) -> None:
        text = '''
actor MyMonster 20000
{
    Health 100
    Speed 8
    Radius 20
    Height 56
    +SOLID
    +SHOOTABLE
    +COUNTKILL
    States
    {
    Spawn:
        TROO A 10 A_Look
        Loop
    See:
        TROO AABBCCDD 4 A_Chase
        Loop
    }
}
'''
        actors = parse_decorate(text)
        assert len(actors) == 1
        a = actors[0]
        assert a.name == "MyMonster"
        assert a.doomednum == 20000
        assert a.health == 100
        assert a.speed == 8
        assert a.is_monster
        assert "SOLID" in a.flags
        assert "Spawn" in a.states
        assert "See" in a.states

    def test_actor_with_parent(self) -> None:
        text = 'actor BigImp : DoomImp 20001 { Health 200 }'
        actors = parse_decorate(text)
        assert actors[0].parent == "DoomImp"
        assert actors[0].doomednum == 20001

    def test_actor_replaces(self) -> None:
        text = 'actor SuperShotgun : Shotgun replaces Shotgun { }'
        actors = parse_decorate(text)
        assert actors[0].replaces == "Shotgun"

    def test_multiple_actors(self) -> None:
        text = '''
actor Monster1 10001 { Health 50 }
actor Monster2 10002 { Health 100 }
actor Item1 10003 { +COUNTITEM }
'''
        actors = parse_decorate(text)
        assert len(actors) == 3
        assert actors[2].is_item

    def test_comments_stripped(self) -> None:
        text = '''
// This is a comment
actor Test 99999
{
    /* block comment */
    Health 50
}
'''
        actors = parse_decorate(text)
        assert len(actors) == 1
        assert actors[0].health == 50

    def test_no_ednum(self) -> None:
        text = 'actor InternalActor { Health 10 }'
        actors = parse_decorate(text)
        assert actors[0].doomednum is None

    def test_antiflags(self) -> None:
        text = 'actor Test 1 { -SOLID +NOGRAVITY }'
        actors = parse_decorate(text)
        assert "SOLID" in actors[0].antiflags
        assert "NOGRAVITY" in actors[0].flags

    def test_monster_property(self) -> None:
        text = 'actor Test 1 { Monster }'
        actors = parse_decorate(text)
        assert actors[0].is_monster


# ---------------------------------------------------------------------------
# ACS BEHAVIOR parser
# ---------------------------------------------------------------------------

from wadlib.lumps.behavior import AcsScript, BehaviorInfo, parse_behavior


class TestBehavior:
    def test_acs0_minimal(self) -> None:
        # Minimal ACS0: magic + dir_offset pointing to script count = 0
        data = b"ACS\x00" + struct.pack("<I", 8) + struct.pack("<I", 0)
        info = parse_behavior(data)
        assert info.format == "ACS0"
        assert len(info.scripts) == 0

    def test_acs0_with_script(self) -> None:
        # Build a minimal ACS0 with one closed script
        bytecode = b"\x00" * 16  # fake bytecode
        dir_offset = 4 + 4 + len(bytecode)  # magic + dir_offset + bytecode

        # Script directory: count(4) + entry(12)
        script_count = struct.pack("<I", 1)
        script_entry = struct.pack("<IIi", 1, 8, 0)  # script 1, offset 8, 0 args

        # String count = 0
        string_count = struct.pack("<I", 0)

        data = b"ACS\x00" + struct.pack("<I", dir_offset) + bytecode
        data += script_count + script_entry + string_count

        info = parse_behavior(data)
        assert len(info.scripts) == 1
        assert info.scripts[0].number == 1
        assert info.scripts[0].arg_count == 0

    def test_acs0_open_script(self) -> None:
        # Open scripts have number >= 1000
        dir_offset = 8
        data = b"ACS\x00" + struct.pack("<I", dir_offset)
        data += struct.pack("<I", 1)  # count
        data += struct.pack("<IIi", 1001, 0, 0)  # script 1001 = open script 1
        data += struct.pack("<I", 0)  # no strings

        info = parse_behavior(data)
        assert info.scripts[0].number == 1
        assert info.scripts[0].script_type == 1  # open

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            parse_behavior(b"\x00\x00")

    def test_bad_magic_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown"):
            parse_behavior(b"XXXX\x00\x00\x00\x00")

    def test_script_type_name(self) -> None:
        s = AcsScript(1, 0, 0, 0)
        assert s.type_name == "closed"
        s2 = AcsScript(1, 1, 0, 0)
        assert s2.type_name == "open"


# ---------------------------------------------------------------------------
# GL nodes
# ---------------------------------------------------------------------------

from wadlib.lumps.glnodes import (
    GlNode,
    GlSeg,
    GlSubSector,
    GlVertex,
    parse_gl_nodes,
    parse_gl_segs,
    parse_gl_ssectors,
    parse_gl_verts,
)


class TestGlNodes:
    def test_gl_verts_v1(self) -> None:
        data = struct.pack("<hh", 100, -200) + struct.pack("<hh", 300, 400)
        verts = parse_gl_verts(data)
        assert len(verts) == 2
        assert verts[0].x == 100.0
        assert verts[0].y == -200.0

    def test_gl_verts_v2(self) -> None:
        data = b"gNd2"
        data += struct.pack("<ii", 100 * 65536, -200 * 65536)
        verts = parse_gl_verts(data)
        assert len(verts) == 1
        assert verts[0].x == 100.0
        assert verts[0].y == -200.0

    def test_gl_segs(self) -> None:
        data = struct.pack("<HHHHH", 0, 1, 5, 0, 0xFFFF)
        segs = parse_gl_segs(data)
        assert len(segs) == 1
        assert segs[0].start_vertex == 0
        assert segs[0].linedef == 5
        assert not segs[0].is_miniseg

    def test_gl_segs_miniseg(self) -> None:
        data = struct.pack("<HHHHH", 0, 1, 0xFFFF, 0, 0xFFFF)
        segs = parse_gl_segs(data)
        assert segs[0].is_miniseg

    def test_gl_ssectors(self) -> None:
        data = struct.pack("<HH", 4, 0) + struct.pack("<HH", 3, 4)
        ssectors = parse_gl_ssectors(data)
        assert len(ssectors) == 2
        assert ssectors[0].seg_count == 4
        assert ssectors[1].first_seg == 4

    def test_gl_nodes(self) -> None:
        data = struct.pack("<hhhhhhhhhhhhHH",
            0, 0, 64, 0,  # partition
            64, 0, 0, 64,  # right bbox
            0, -64, 0, 64,  # left bbox
            0, 0x8001,  # children
        )
        nodes = parse_gl_nodes(data)
        assert len(nodes) == 1
        assert nodes[0].dx == 64
        assert nodes[0].left_child == 0x8001

    def test_empty_data(self) -> None:
        assert parse_gl_verts(b"") == []
        assert parse_gl_segs(b"") == []
        assert parse_gl_ssectors(b"") == []
        assert parse_gl_nodes(b"") == []
