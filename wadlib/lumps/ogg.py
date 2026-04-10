"""OGG, MP3, and MIDI music lump wrappers."""

from __future__ import annotations

from .base import BaseLump

# Magic bytes for content-based detection
OGG_MAGIC = b"OggS"
MP3_ID3_MAGIC = b"ID3"
MP3_SYNC_MAGIC = b"\xff\xfb"
MP3_SYNC_MAGIC2 = b"\xff\xf3"
MP3_SYNC_MAGIC3 = b"\xff\xf2"
MIDI_MAGIC = b"MThd"


class OggLump(BaseLump):
    """A WAD lump containing OGG Vorbis audio."""

    def save(self, path: str) -> None:
        """Write the raw OGG data to *path*."""
        with open(path, "wb") as f:
            f.write(self.raw())


class Mp3Lump(BaseLump):
    """A WAD lump containing MP3 audio."""

    def save(self, path: str) -> None:
        """Write the raw MP3 data to *path*."""
        with open(path, "wb") as f:
            f.write(self.raw())


class MidiLump(BaseLump):
    """A WAD lump containing a raw MIDI file (Standard MIDI Format)."""

    def save(self, path: str) -> None:
        """Write the raw MIDI data to *path*."""
        with open(path, "wb") as f:
            f.write(self.raw())
