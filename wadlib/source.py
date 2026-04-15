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
    def name(self) -> str: ...

    @property
    def size(self) -> int: ...

    def read_bytes(self) -> bytes: ...


class MemoryLumpSource:
    """In-memory ``LumpSource`` — for pk3 entries and unit tests."""

    def __init__(self, name: str, data: bytes) -> None:
        self._name = name
        self._data = data

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> int:
        return len(self._data)

    def read_bytes(self) -> bytes:
        return self._data
