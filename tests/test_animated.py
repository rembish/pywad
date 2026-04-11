"""Tests for ANIMATED and SWITCHES binary lumps."""

from __future__ import annotations

import struct

from wadlib.lumps.animated import (
    AnimatedEntry,
    AnimatedLump,
    SwitchEntry,
    SwitchesLump,
    animated_to_bytes,
    switches_to_bytes,
)


def _build_animated_raw(entries: list[tuple[int, str, str, int]]) -> bytes:
    """Build raw ANIMATED data from (type, last, first, speed) tuples."""
    data = b""
    for type_byte, last, first, speed in entries:
        data += struct.pack(
            "<B9s9sI",
            type_byte,
            last.encode("ascii").ljust(9, b"\x00"),
            first.encode("ascii").ljust(9, b"\x00"),
            speed,
        )
    # Terminator
    data += struct.pack("<B9s9sI", 0xFF, b"\x00" * 9, b"\x00" * 9, 0)
    return data


def _build_switches_raw(entries: list[tuple[str, str, int]]) -> bytes:
    """Build raw SWITCHES data from (off, on, episode) tuples."""
    data = b""
    for off_name, on_name, episode in entries:
        data += struct.pack(
            "<9s9sH",
            off_name.encode("ascii").ljust(9, b"\x00"),
            on_name.encode("ascii").ljust(9, b"\x00"),
            episode,
        )
    # Terminator
    data += struct.pack("<9s9sH", b"\x00" * 9, b"\x00" * 9, 0)
    return data


class TestAnimatedEntry:
    def test_to_bytes(self) -> None:
        e = AnimatedEntry(kind="flat", first="NUKAGE1", last="NUKAGE3", speed=8)
        raw = e.to_bytes()
        assert len(raw) == 23
        assert raw[0] == 0  # flat

    def test_texture_type(self) -> None:
        e = AnimatedEntry(kind="texture", first="BLODGR1", last="BLODGR4", speed=8)
        raw = e.to_bytes()
        assert raw[0] == 1  # texture


class TestAnimatedLump:
    def test_parse_flats(self) -> None:
        raw = _build_animated_raw([
            (0, "NUKAGE3", "NUKAGE1", 8),
            (0, "FWATER4", "FWATER1", 8),
        ])
        from wadlib.directory import DirectoryEntry
        from io import BytesIO

        class _FW:
            def __init__(self, d: bytes) -> None:
                self.fd = BytesIO(d)

        entry = DirectoryEntry(_FW(raw), 0, len(raw), "ANIMATED")  # type: ignore[arg-type]
        lump = AnimatedLump(entry)
        assert len(lump.entries) == 2
        assert lump.entries[0].kind == "flat"
        assert lump.entries[0].first == "NUKAGE1"
        assert lump.entries[0].last == "NUKAGE3"
        assert lump.entries[0].speed == 8
        assert len(lump.flats) == 2
        assert len(lump.textures) == 0

    def test_parse_mixed(self) -> None:
        raw = _build_animated_raw([
            (0, "NUKAGE3", "NUKAGE1", 8),
            (1, "BLODGR4", "BLODGR1", 8),
        ])
        from wadlib.directory import DirectoryEntry
        from io import BytesIO

        class _FW:
            def __init__(self, d: bytes) -> None:
                self.fd = BytesIO(d)

        entry = DirectoryEntry(_FW(raw), 0, len(raw), "ANIMATED")  # type: ignore[arg-type]
        lump = AnimatedLump(entry)
        assert len(lump.flats) == 1
        assert len(lump.textures) == 1


class TestSwitchEntry:
    def test_to_bytes(self) -> None:
        e = SwitchEntry(off_name="SW1BRCOM", on_name="SW2BRCOM", episode=1)
        raw = e.to_bytes()
        assert len(raw) == 20


class TestSwitchesLump:
    def test_parse(self) -> None:
        raw = _build_switches_raw([
            ("SW1BRCOM", "SW2BRCOM", 1),
            ("SW1GARG", "SW2GARG", 2),
        ])
        from wadlib.directory import DirectoryEntry
        from io import BytesIO

        class _FW:
            def __init__(self, d: bytes) -> None:
                self.fd = BytesIO(d)

        entry = DirectoryEntry(_FW(raw), 0, len(raw), "SWITCHES")  # type: ignore[arg-type]
        lump = SwitchesLump(entry)
        assert len(lump.entries) == 2
        assert lump.entries[0].off_name == "SW1BRCOM"
        assert lump.entries[0].on_name == "SW2BRCOM"
        assert lump.entries[0].episode == 1


class TestRoundTrip:
    def test_animated_round_trip(self) -> None:
        entries = [
            AnimatedEntry("flat", "NUKAGE1", "NUKAGE3", 8),
            AnimatedEntry("texture", "BLODGR1", "BLODGR4", 8),
        ]
        raw = animated_to_bytes(entries)
        # Parse back
        from wadlib.directory import DirectoryEntry
        from io import BytesIO

        class _FW:
            def __init__(self, d: bytes) -> None:
                self.fd = BytesIO(d)

        entry = DirectoryEntry(_FW(raw), 0, len(raw), "ANIMATED")  # type: ignore[arg-type]
        lump = AnimatedLump(entry)
        assert len(lump.entries) == 2
        assert lump.entries[0].first == "NUKAGE1"
        assert lump.entries[1].kind == "texture"

    def test_switches_round_trip(self) -> None:
        entries = [
            SwitchEntry("SW1BRCOM", "SW2BRCOM", 1),
            SwitchEntry("SW1GARG", "SW2GARG", 3),
        ]
        raw = switches_to_bytes(entries)
        from wadlib.directory import DirectoryEntry
        from io import BytesIO

        class _FW:
            def __init__(self, d: bytes) -> None:
                self.fd = BytesIO(d)

        entry = DirectoryEntry(_FW(raw), 0, len(raw), "SWITCHES")  # type: ignore[arg-type]
        lump = SwitchesLump(entry)
        assert len(lump.entries) == 2
        assert lump.entries[1].episode == 3
