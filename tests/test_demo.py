"""Tests for Doom demo (.lmp) parser."""

from __future__ import annotations

import struct

from wadlib.lumps.demo import Demo, DemoHeader, DemoTic, parse_demo


def _build_demo(
    version: int = 109,
    skill: int = 2,
    episode: int = 1,
    map_num: int = 1,
    tics: list[tuple[int, int, int, int]] | None = None,
) -> bytes:
    """Build a minimal demo from header values and (fwd, side, turn, buttons) tics."""
    header = bytes([
        version, skill, episode, map_num,
        0,  # singleplayer
        0,  # no respawn
        0,  # no fast
        0,  # no nomonsters
        0,  # player 0 POV
        1, 0, 0, 0,  # player 1 present, others absent
    ])
    body = b""
    if tics:
        for fwd, side, turn, buttons in tics:
            body += struct.pack("bbbB", fwd, side, turn, buttons)
    body += b"\x80"  # end marker
    return header + body


class TestDemoHeader:
    def test_parse_header(self) -> None:
        data = _build_demo(version=109, skill=3, episode=2, map_num=5)
        demo = parse_demo(data)
        assert demo.header.version == 109
        assert demo.header.skill == 3
        assert demo.header.episode == 2
        assert demo.header.map == 5
        assert demo.header.num_players == 1

    def test_skill_name(self) -> None:
        data = _build_demo(skill=0)
        demo = parse_demo(data)
        assert "Too Young" in demo.header.skill_name

        data = _build_demo(skill=4)
        demo = parse_demo(data)
        assert demo.header.skill_name == "Nightmare"

    def test_multiplayer(self) -> None:
        header = bytes([109, 2, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0])  # 2 players coop
        header += struct.pack("bbbB", 0, 0, 0, 0) * 2  # one frame, 2 players
        header += b"\x80"
        demo = parse_demo(header)
        assert demo.header.num_players == 2
        assert demo.header.multiplayer_mode == 1


class TestDemoTics:
    def test_single_tic(self) -> None:
        data = _build_demo(tics=[(50, 0, 0, 0)])  # forward 50
        demo = parse_demo(data)
        assert demo.duration_tics == 1
        assert demo.tics[0][0].forwardmove == 50

    def test_movement(self) -> None:
        data = _build_demo(tics=[
            (50, 0, 0, 0),     # forward
            (-25, 0, 0, 0),    # backward
            (0, 40, 0, 0),     # strafe right
            (0, -40, 0, 0),    # strafe left
        ])
        demo = parse_demo(data)
        assert demo.duration_tics == 4
        assert demo.tics[0][0].forwardmove == 50
        assert demo.tics[1][0].forwardmove == -25
        assert demo.tics[2][0].sidemove == 40
        assert demo.tics[3][0].sidemove == -40

    def test_buttons(self) -> None:
        data = _build_demo(tics=[
            (0, 0, 0, 1),   # fire
            (0, 0, 0, 2),   # use
            (0, 0, 0, 3),   # fire + use
            (0, 0, 0, 12),  # weapon 3 (bits 2-3 = 3)
        ])
        demo = parse_demo(data)
        assert demo.tics[0][0].fire
        assert not demo.tics[0][0].use
        assert demo.tics[1][0].use
        assert not demo.tics[1][0].fire
        assert demo.tics[2][0].fire and demo.tics[2][0].use
        assert demo.tics[3][0].weapon == 3

    def test_turning(self) -> None:
        data = _build_demo(tics=[
            (0, 0, 10, 0),   # turn left
            (0, 0, -10, 0),  # turn right
        ])
        demo = parse_demo(data)
        assert demo.tics[0][0].angleturn == 10
        assert demo.tics[1][0].angleturn == -10

    def test_duration_seconds(self) -> None:
        data = _build_demo(tics=[(0, 0, 0, 0)] * 70)
        demo = parse_demo(data)
        assert demo.duration_seconds == 2.0  # 70 tics / 35 Hz


class TestPlayerPath:
    def test_stationary(self) -> None:
        data = _build_demo(tics=[(0, 0, 0, 0)] * 5)
        demo = parse_demo(data)
        path = demo.player_path(0)
        assert len(path) == 6  # initial + 5 tics
        assert all(abs(x) < 0.001 and abs(y) < 0.001 for x, y in path)

    def test_forward_movement(self) -> None:
        data = _build_demo(tics=[(50, 0, 0, 0)] * 10)
        demo = parse_demo(data)
        path = demo.player_path(0)
        # Should move in initial direction (angle=0)
        assert path[-1][0] > path[0][0]


class TestEmptyDemo:
    def test_no_tics(self) -> None:
        data = _build_demo(tics=[])
        demo = parse_demo(data)
        assert demo.duration_tics == 0
        assert demo.duration_seconds == 0.0

    def test_too_short_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="too short"):
            parse_demo(b"\x00" * 5)


class TestLongtics:
    def test_longtics_format(self) -> None:
        """Version >= 111 uses 5-byte tics with 16-bit angleturn."""
        header = bytes([111, 2, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0])
        # One longtic: fwd=50, side=0, turn=1000 (16-bit LE), buttons=0
        body = struct.pack("<bbhB", 50, 0, 1000, 0)
        body += b"\x80"
        demo = parse_demo(header + body)
        assert demo.header.version == 111
        assert demo.duration_tics == 1
        assert demo.tics[0][0].forwardmove == 50
        assert demo.tics[0][0].angleturn == 1000
