"""DMX digitized sound lump decoder/encoder."""

from __future__ import annotations

import struct
from typing import Any, ClassVar

from ..exceptions import CorruptLumpError
from .base import BaseLump

_DMX_FORMAT: int = 3
_HEADER_FMT: str = "<HHI"
_HEADER_SIZE: int = struct.calcsize(_HEADER_FMT)  # 8 bytes
_PADDING: int = 16


class DmxSound(BaseLump[Any]):
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
        if len(data) < _HEADER_SIZE:
            raise CorruptLumpError(f"{self.name!r}: DMX sound lump too short ({len(data)} bytes)")
        try:
            fmt, rate, num_samples = struct.unpack_from(_HEADER_FMT, data)
        except struct.error as exc:
            raise CorruptLumpError(f"{self.name!r}: corrupt DMX header") from exc
        if fmt != _DMX_FORMAT:
            raise ValueError(f"Unsupported DMX format: {fmt}")
        pcm_len = max(0, num_samples - _PADDING)
        samples = data[_HEADER_SIZE + _PADDING : _HEADER_SIZE + _PADDING + pcm_len]

        riff = struct.pack("<4sI4s", b"RIFF", 36 + len(samples), b"WAVE")
        fmt_chunk = struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, 1, rate, rate, 1, 8)
        data_chunk = struct.pack("<4sI", b"data", len(samples)) + samples
        return riff + fmt_chunk + data_chunk


def encode_dmx(pcm_samples: bytes, rate: int = 11025) -> bytes:
    """Encode raw 8-bit unsigned PCM samples into a DMX sound lump.

    *rate* is the sample rate in Hz (typically 11025 for Doom sounds).
    """
    num_samples = len(pcm_samples) + _PADDING
    header = struct.pack(_HEADER_FMT, _DMX_FORMAT, rate, num_samples)
    padding = b"\x80" * _PADDING  # silence (0x80 = zero crossing for unsigned 8-bit)
    return header + padding + pcm_samples


def wav_to_dmx(wav_data: bytes) -> bytes:
    """Parse a WAV file and convert it to a DMX sound lump.

    Supports 8-bit unsigned and 16-bit signed mono PCM WAV files.
    Multi-channel WAV files are downmixed to mono (first channel only).

    Raises ``ValueError`` if the WAV file is not a supported format.
    """
    if wav_data[:4] != b"RIFF" or wav_data[8:12] != b"WAVE":
        raise ValueError("Not a WAV file (missing RIFF/WAVE header)")

    # Parse chunks
    pos = 12
    fmt_parsed = False
    channels = 1
    rate = 11025
    bits_per_sample = 8
    pcm_data = b""

    while pos < len(wav_data) - 8:
        chunk_id = wav_data[pos : pos + 4]
        chunk_size = struct.unpack("<I", wav_data[pos + 4 : pos + 8])[0]
        chunk_body = wav_data[pos + 8 : pos + 8 + chunk_size]

        if chunk_id == b"fmt ":
            if len(chunk_body) < 16:
                raise ValueError("WAV fmt chunk too short")
            audio_fmt, channels, rate, _byte_rate, _block_align, bits_per_sample = struct.unpack(
                "<HHIIHH", chunk_body[:16]
            )
            if audio_fmt != 1:
                raise ValueError(f"Unsupported WAV format {audio_fmt} (only PCM=1 supported)")
            if bits_per_sample not in (8, 16):
                raise ValueError(
                    f"Unsupported bit depth {bits_per_sample} (only 8 or 16 supported)"
                )
            fmt_parsed = True

        elif chunk_id == b"data":
            pcm_data = chunk_body

        # Advance to next chunk (chunks are word-aligned)
        pos += 8 + chunk_size
        if chunk_size % 2:
            pos += 1

    if not fmt_parsed:
        raise ValueError("WAV file missing fmt chunk")
    if not pcm_data:
        raise ValueError("WAV file missing data chunk")

    # Convert to 8-bit unsigned mono
    if bits_per_sample == 16:
        # 16-bit signed LE → 8-bit unsigned
        sample_count = len(pcm_data) // (2 * channels)
        samples = bytearray(sample_count)
        for i in range(sample_count):
            offset = i * 2 * channels  # take first channel
            val = struct.unpack("<h", pcm_data[offset : offset + 2])[0]
            samples[i] = (val >> 8) + 128  # signed 16 → unsigned 8
        pcm_data = bytes(samples)
    elif channels > 1:
        # 8-bit multi-channel → mono (first channel)
        sample_count = len(pcm_data) // channels
        pcm_data = bytes(pcm_data[i * channels] for i in range(sample_count))

    return encode_dmx(pcm_data, rate)
