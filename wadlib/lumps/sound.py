"""DMX digitized sound lump decoder."""

from __future__ import annotations

import struct
from typing import ClassVar

from .base import BaseLump

_DMX_FORMAT: int = 3
_HEADER_FMT: str = "<HHI"
_HEADER_SIZE: int = struct.calcsize(_HEADER_FMT)  # 8 bytes
_PADDING: int = 16


class DmxSound(BaseLump):
    """A Doom digitized sound effect stored in DMX format.

    DMX layout: fmt(2) + rate(2) + num_samples(4) + padding(16) + PCM bytes.
    num_samples includes the 16-byte padding, so actual PCM length is
    num_samples - _PADDING.
    """

    _HEADER_FMT: ClassVar[str] = _HEADER_FMT

    @property
    def rate(self) -> int:
        """Sample rate in Hz."""
        return int.from_bytes(self.raw()[2:4], "little")

    @property
    def sample_count(self) -> int:
        """Number of PCM samples (num_samples field minus the 16-byte padding)."""
        ns = int.from_bytes(self.raw()[4:8], "little")
        return max(0, ns - _PADDING)

    def to_wav(self) -> bytes:
        """Convert this DMX sound to a WAV file byte string."""
        data = self.raw()
        fmt, rate, num_samples = struct.unpack_from(_HEADER_FMT, data)
        if fmt != _DMX_FORMAT:
            raise ValueError(f"Unsupported DMX format: {fmt}")
        pcm_len = max(0, num_samples - _PADDING)
        samples = data[_HEADER_SIZE + _PADDING : _HEADER_SIZE + _PADDING + pcm_len]

        riff = struct.pack("<4sI4s", b"RIFF", 36 + len(samples), b"WAVE")
        fmt_chunk = struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, rate, rate, 1, 8)
        data_chunk = struct.pack("<4sI", b"data", len(samples)) + samples
        return riff + fmt_chunk + data_chunk
