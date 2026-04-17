"""Doom demo (.lmp) parser — decode recorded game input.

A Doom demo records player inputs frame-by-frame (one "tic" per frame at
35 Hz).  The format is simple:

Header (vanilla Doom):
  [1]  version    (109 = Doom 1.9, 110 = Doom 1.10, etc.)
  [1]  skill      (0-4: I'm Too Young To Die .. Nightmare)
  [1]  episode    (1-based, or 1 for Doom 2)
  [1]  map        (1-based map number)
  [1]  multiplayer_mode  (0=single, 1=coop, 2=DM)
  [1]  respawn    (0 or 1)
  [1]  fast       (0 or 1)
  [1]  nomonsters (0 or 1)
  [1]  player_pov (0-3: which player's view)
  [1]  player1    (1=present, 0=absent)
  [1]  player2
  [1]  player3
  [1]  player4

Body: sequence of 4-byte tics per active player:
  [1]  forwardmove  (signed: positive=forward, negative=backward)
  [1]  sidemove     (signed: positive=right, negative=left)
  [1]  angleturn    (signed: angle delta, positive=left)
  [1]  buttons      (bit 0=fire, bit 1=use, bits 2-7=weapon change)

End marker: 0x80

Longtics variant (Doom v1.91+, -longtics):
  Each tic is 5 bytes: forwardmove(1), sidemove(1), angleturn(2 LE), buttons(1)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class DemoHeader:
    """Parsed demo header."""

    version: int
    skill: int
    episode: int
    map: int
    multiplayer_mode: int
    respawn: bool
    fast: bool
    nomonsters: bool
    player_pov: int
    players: list[bool]

    @property
    def num_players(self) -> int:
        """Number of active players in this demo (count of ``True`` entries in :attr:`players`)."""
        return sum(self.players)

    @property
    def skill_name(self) -> str:
        """Human-readable skill level name (e.g. ``"Hurt Me Plenty"`` for skill 2)."""
        names = [
            "I'm Too Young To Die",
            "Hey, Not Too Rough",
            "Hurt Me Plenty",
            "Ultra-Violence",
            "Nightmare",
        ]
        if 0 <= self.skill < len(names):
            return names[self.skill]
        return f"Unknown ({self.skill})"


@dataclass
class DemoTic:
    """A single input frame for one player."""

    forwardmove: int
    sidemove: int
    angleturn: int
    buttons: int

    @property
    def fire(self) -> bool:
        """``True`` if the fire button (bit 0 of :attr:`buttons`) was held this tic."""
        return bool(self.buttons & 0x01)

    @property
    def use(self) -> bool:
        """``True`` if the use/activate button (bit 1 of :attr:`buttons`) was held this tic."""
        return bool(self.buttons & 0x02)

    @property
    def weapon(self) -> int:
        """Weapon change slot (0 = no change)."""
        return (self.buttons >> 2) & 0x3F

    def to_bytes(self, longtics: bool = False) -> bytes:
        """Serialize this tic to bytes."""
        if longtics:
            return struct.pack(
                "<bbhB", self.forwardmove, self.sidemove, self.angleturn, self.buttons
            )
        return struct.pack("bbbB", self.forwardmove, self.sidemove, self.angleturn, self.buttons)


@dataclass
class Demo:
    """A parsed Doom demo recording."""

    header: DemoHeader
    tics: list[list[DemoTic]]  # outer: frames, inner: per-player

    @property
    def duration_tics(self) -> int:
        """Total length of the demo in tics (35 tics = 1 second)."""
        return len(self.tics)

    @property
    def duration_seconds(self) -> float:
        """Duration in seconds (35 tics per second)."""
        return len(self.tics) / 35.0

    def to_bytes(self) -> bytes:
        """Serialize this demo to raw bytes (playable by Doom engine)."""
        longtics = self.header.version >= 111
        header_bytes = bytes(
            [
                self.header.version,
                self.header.skill,
                self.header.episode,
                self.header.map,
                self.header.multiplayer_mode,
                int(self.header.respawn),
                int(self.header.fast),
                int(self.header.nomonsters),
                self.header.player_pov,
                *[int(p) for p in self.header.players],
            ]
        )
        body = bytearray()
        for frame in self.tics:
            for tic in frame:
                body.extend(tic.to_bytes(longtics))
        body.append(0x80)  # end marker
        return header_bytes + bytes(body)

    def player_path(self, player: int = 0) -> list[tuple[float, float]]:
        """Reconstruct approximate player positions from movement inputs.

        Returns a list of (x, y) coordinates. Note: these are relative
        movements from an unknown start position, and don't account for
        collision or actual map geometry.
        """
        import math

        x, y = 0.0, 0.0
        angle = 0.0  # radians
        path = [(x, y)]

        for frame in self.tics:
            if player >= len(frame):
                continue
            tic = frame[player]
            # angleturn is in byteangle units: 256 = full circle, but
            # in the demo it's signed char (8-bit), scaled by 256 internally
            angle += tic.angleturn * (math.pi / 128.0)
            fwd = tic.forwardmove
            side = tic.sidemove
            x += fwd * math.cos(angle) + side * math.cos(angle - math.pi / 2)
            y += fwd * math.sin(angle) + side * math.sin(angle - math.pi / 2)
            path.append((x, y))

        return path


def parse_demo(data: bytes) -> Demo:
    """Parse a Doom demo from raw bytes.

    Supports vanilla Doom (4-byte tics) and longtics (5-byte tics) formats.
    """
    if len(data) < 13:
        raise ValueError(f"Demo too short ({len(data)} bytes)")

    version = data[0]
    skill = data[1]
    episode = data[2]
    map_num = data[3]
    mp_mode = data[4]
    respawn = bool(data[5])
    fast = bool(data[6])
    nomonsters = bool(data[7])
    pov = data[8]
    players = [bool(data[9]), bool(data[10]), bool(data[11]), bool(data[12])]

    header = DemoHeader(
        version=version,
        skill=skill,
        episode=episode,
        map=map_num,
        multiplayer_mode=mp_mode,
        respawn=respawn,
        fast=fast,
        nomonsters=nomonsters,
        player_pov=pov,
        players=players,
    )

    num_players = header.num_players
    pos = 13

    # Detect longtics: version >= 111 uses 5-byte tics
    longtics = version >= 111
    tic_size = 5 if longtics else 4
    frame_size = tic_size * num_players

    tics: list[list[DemoTic]] = []

    while pos + frame_size <= len(data):
        # Check for end marker
        if data[pos] == 0x80:
            break

        frame: list[DemoTic] = []
        for _ in range(num_players):
            if longtics:
                fwd = struct.unpack_from("b", data, pos)[0]
                side = struct.unpack_from("b", data, pos + 1)[0]
                turn = struct.unpack_from("<h", data, pos + 2)[0]
                buttons = data[pos + 4]
                pos += 5
            else:
                fwd = struct.unpack_from("b", data, pos)[0]
                side = struct.unpack_from("b", data, pos + 1)[0]
                turn = struct.unpack_from("b", data, pos + 2)[0]
                buttons = data[pos + 3]
                pos += 4
            frame.append(DemoTic(fwd, side, turn, buttons))

        tics.append(frame)

    return Demo(header=header, tics=tics)
