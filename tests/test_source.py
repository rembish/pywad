"""Tests for LumpSource protocol and MemoryLumpSource implementation."""

from __future__ import annotations

from wadlib.lumps.base import BaseLump
from wadlib.source import LumpSource, MemoryLumpSource


class TestMemoryLumpSource:
    def test_name(self) -> None:
        src = MemoryLumpSource("PLAYPAL", b"\x00" * 16)
        assert src.name == "PLAYPAL"

    def test_size_reflects_data_length(self) -> None:
        data = b"\x01\x02\x03\x04"
        src = MemoryLumpSource("TEST", data)
        assert src.size == 4

    def test_read_bytes_returns_data(self) -> None:
        data = b"\xde\xad\xbe\xef"
        src = MemoryLumpSource("LUMP", data)
        assert src.read_bytes() == data

    def test_empty_source(self) -> None:
        src = MemoryLumpSource("EMPTY", b"")
        assert src.size == 0
        assert src.read_bytes() == b""

    def test_satisfies_lump_source_protocol(self) -> None:
        src = MemoryLumpSource("FOO", b"\x00")
        assert isinstance(src, LumpSource)


class TestBaseLumpWithMemorySource:
    """Verify BaseLump accepts a MemoryLumpSource directly."""

    def test_base_lump_reads_from_memory(self) -> None:
        data = b"\x01\x02\x03\x04\x05\x06"
        src = MemoryLumpSource("TESTLUMP", data)
        lump: BaseLump[object] = BaseLump(src)
        assert lump.name == "TESTLUMP"
        assert len(lump) == len(data)
        assert lump.raw() == data

    def test_base_lump_empty_source(self) -> None:
        src = MemoryLumpSource("EMPTY", b"")
        lump: BaseLump[object] = BaseLump(src)
        assert not lump
        assert lump.raw() == b""
