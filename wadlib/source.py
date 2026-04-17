"""LumpSource — abstract read-only handle for lump bytes.

``LumpSource`` is the structural protocol consumed by ``BaseLump.__init__``.
Any object that exposes a ``name`` string, a ``size`` integer, and a
``read_bytes()`` method satisfies it.

``DirectoryEntry`` (WAD file-backed) and ``MemoryLumpSource`` (in-memory,
used for pk3 and tests) are the two built-in implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LumpSource(Protocol):
    """Structural protocol consumed by ``BaseLump.__init__``."""

    @property
    def name(self) -> str:
        """The lump name (uppercase, at most 8 characters)."""

    @property
    def size(self) -> int:
        """Byte size of the lump data."""

    def read_bytes(self) -> bytes:
        """Return the full raw bytes of this lump."""


class MemoryLumpSource:
    """In-memory ``LumpSource`` — for pk3 entries and unit tests."""

    def __init__(self, name: str, data: bytes) -> None:
        self._name = name
        self._data = data

    @property
    def name(self) -> str:
        """The lump name supplied at construction."""
        return self._name

    @property
    def size(self) -> int:
        """Byte size of the in-memory data buffer."""
        return len(self._data)

    def read_bytes(self) -> bytes:
        """Return the full in-memory data buffer."""
        return self._data
