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

_PC_SPEAKER_FORMAT: int = 0
_PC_TICKS_PER_SEC: int = 140  # Doom timer rate for PC speaker notes
_PC_TIMER_FREQ: int = 1193180  # 8253 PIT base frequency (Hz)
_PC_SAMPLE_RATE: int = 11025  # synthesis output sample rate

# 128-entry timer-value table from Chocolate Doom's pcsound driver.
# Index 0 means silence; index 1-127 -> frequency = _PC_TIMER_FREQ / timer_val.
_PC_TONES: tuple[int, ...] = (
    0,
    6818,
    6628,
    6449,
    6279,
    6087,
    5906,
    5736,
    5575,
    5423,
    5279,
    5120,
    4971,
    4843,
    4706,
    4579,
    4450,
    4327,
    4210,
    4096,
    3979,
    3871,
    3763,
    3660,
    3551,
    3454,
    3351,
    3255,
    3167,
    3072,
    2984,
    2901,
    2809,
    2726,
    2651,
    2575,
    2500,
    2433,
    2362,
    2293,
    2230,
    2166,
    2105,
    2048,
    1991,
    1934,
    1881,
    1828,
    1774,
    1725,
    1676,
    1626,
    1579,
    1534,
    1491,
    1442,
    1398,
    1358,
    1316,
    1277,
    1237,
    1199,
    1163,
    1130,
    1097,
    1064,
    1032,
    1001,
    970,
    939,
    911,
    885,
    861,
    834,
    810,
    786,
    762,
    740,
    718,
    697,
    677,
    657,
    638,
    619,
    600,
    582,
    565,
    547,
    532,
    516,
    501,
    486,
    472,
    458,
    445,
    431,
    419,
    407,
    395,
    383,
    372,
    362,
    351,
    341,
    331,
    321,
    312,
    303,
    294,
    286,
    278,
    270,
    262,
    254,
    247,
    240,
    233,
    226,
    220,
    214,
    208,
    202,
    196,
    190,
    185,
    180,
    175,
    170,
)


def _pc_speaker_to_pcm(notes: bytes, num_samples: int) -> bytes:
    """Synthesize a PC speaker note sequence into 8-bit unsigned mono PCM.

    Each note is one Doom timer tick (1/140 s). Note byte 0 = silence;
    values 1-127 index into ``_PC_TONES``; values >= 128 are treated as silence.
    A square wave is generated at the computed frequency.
    """
    pcm = bytearray()
    phase = 0.0
    prev_end = 0
    for i, note in enumerate(notes[:num_samples]):
        tick_end = round(_PC_SAMPLE_RATE * (i + 1) / _PC_TICKS_PER_SEC)
        n = tick_end - prev_end
        prev_end = tick_end

        timer_val = _PC_TONES[note] if note < len(_PC_TONES) else 0
        if timer_val == 0:
            pcm.extend(b"\x80" * n)
            phase = 0.0
        else:
            freq = _PC_TIMER_FREQ / timer_val
            half_period = _PC_SAMPLE_RATE / (2.0 * freq)
            for _ in range(n):
                pcm.append(0xC0 if int(phase / half_period) % 2 == 0 else 0x40)
                phase += 1.0
    return bytes(pcm)


class DmxSound(BaseLump[Any]):
    """A Doom sound effect stored in DMX format.

    Supports two sub-formats:
    - **Format 3** (digitized PCM): ``fmt(2) + rate(2) + num_samples(4) + padding(16) + PCM``.
    - **Format 0** (PC speaker): ``fmt(2) + num_notes(2) + note_bytes``.  Each
      note byte is a timer index (0 = silence, 1-127 = tone).
    """

    _HEADER_FMT: ClassVar[str] = _HEADER_FMT

    @property
    def format(self) -> int:
        """DMX format identifier: 3 for digitized PCM, 0 for PC speaker sequence."""
        data = self.raw()
        if len(data) < 2:
            return -1
        return int(struct.unpack_from("<H", data, 0)[0])

    @property
    def rate(self) -> int:
        """Sample rate in Hz. For PC speaker lumps (format 0), returns the synthesis rate."""
        if self.format == _PC_SPEAKER_FORMAT:
            return _PC_SAMPLE_RATE
        return int.from_bytes(self.raw()[2:4], "little")

    @property
    def sample_count(self) -> int:
        """Number of PCM samples (format 3) or note ticks (format 0)."""
        if self.format == _PC_SPEAKER_FORMAT:
            return int.from_bytes(self.raw()[2:4], "little")
        ns = int.from_bytes(self.raw()[4:8], "little")
        return max(0, ns - _PADDING)

    def to_wav(self) -> bytes:
        """Convert this DMX sound to a WAV file byte string.

        Both format 3 (digitized PCM) and format 0 (PC speaker) are supported.
        PC speaker lumps are synthesized as square waves at the nominal
        frequencies defined by the Doom PC-speaker timer table.
        """
        data = self.raw()
        if len(data) < 2:
            raise CorruptLumpError(f"{self.name!r}: DMX sound lump too short ({len(data)} bytes)")
        fmt = struct.unpack_from("<H", data, 0)[0]

        if fmt == _PC_SPEAKER_FORMAT:
            if len(data) < 4:
                raise CorruptLumpError(
                    f"{self.name!r}: PC speaker lump too short ({len(data)} bytes)"
                )
            num_notes = struct.unpack_from("<H", data, 2)[0]
            pcm = _pc_speaker_to_pcm(data[4:], num_notes)
            riff = struct.pack("<4sI4s", b"RIFF", 36 + len(pcm), b"WAVE")
            fmt_chunk = struct.pack(
                "<4sIHHIIHH", b"fmt ", 16, 1, 1, _PC_SAMPLE_RATE, _PC_SAMPLE_RATE, 1, 8
            )
            return riff + fmt_chunk + struct.pack("<4sI", b"data", len(pcm)) + pcm

        if len(data) < _HEADER_SIZE:
            raise CorruptLumpError(f"{self.name!r}: DMX sound lump too short ({len(data)} bytes)")
        try:
            _, rate, num_samples = struct.unpack_from(_HEADER_FMT, data)
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
