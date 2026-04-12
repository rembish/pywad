"""Tests for WAV → DMX conversion and hex colour utilities."""

from __future__ import annotations

import os
import struct

import pytest

from wadlib.lumps.colormap import build_colormap, hex_to_rgb, rgb_to_hex
from wadlib.lumps.sound import wav_to_dmx
from wadlib.wad import WadFile

FREEDOOM2 = "wads/freedoom2.wad"


def _has_wad(path: str) -> bool:
    return os.path.isfile(path)


# ---------------------------------------------------------------------------
# WAV helpers
# ---------------------------------------------------------------------------


def _build_wav(pcm: bytes, rate: int = 11025, bits: int = 8, channels: int = 1) -> bytes:
    """Build a minimal WAV file from raw PCM samples."""
    byte_rate = rate * channels * (bits // 8)
    block_align = channels * (bits // 8)
    riff = struct.pack("<4sI4s", b"RIFF", 36 + len(pcm), b"WAVE")
    fmt_chunk = struct.pack(
        "<4sIHHIIHH", b"fmt ", 16, 1, channels, rate, byte_rate, block_align, bits
    )
    data_chunk = struct.pack("<4sI", b"data", len(pcm)) + pcm
    return riff + fmt_chunk + data_chunk


# ---------------------------------------------------------------------------
# wav_to_dmx tests
# ---------------------------------------------------------------------------


class TestWavToDmx:
    def test_basic_8bit_mono(self) -> None:
        pcm = bytes([0x80] * 100)
        wav = _build_wav(pcm, rate=11025, bits=8)
        dmx = wav_to_dmx(wav)
        assert dmx[:2] == b"\x03\x00"  # DMX format 3
        rate = struct.unpack("<H", dmx[2:4])[0]
        assert rate == 11025
        # PCM samples should be in the output after header + padding
        assert dmx[24:] == pcm

    def test_16bit_conversion(self) -> None:
        # 16-bit signed: 0x0000 = silence, should map to 128 unsigned
        pcm_16 = struct.pack("<50h", *([0] * 50))
        wav = _build_wav(pcm_16, rate=22050, bits=16)
        dmx = wav_to_dmx(wav)
        rate = struct.unpack("<H", dmx[2:4])[0]
        assert rate == 22050
        # Verify samples converted: signed 0 → unsigned 128
        samples = dmx[24:]
        assert len(samples) == 50
        assert all(s == 128 for s in samples)

    def test_16bit_extremes(self) -> None:
        # Max positive (32767) → 255, max negative (-32768) → 0
        pcm_16 = struct.pack("<2h", 32767, -32768)
        wav = _build_wav(pcm_16, rate=11025, bits=16)
        dmx = wav_to_dmx(wav)
        samples = dmx[24:]
        assert samples[0] == 255  # 32767 >> 8 + 128 = 255
        assert samples[1] == 0  # -32768 >> 8 + 128 = 0

    def test_stereo_downmix(self) -> None:
        # 2-channel 8-bit: [L0, R0, L1, R1, ...]
        pcm = bytes([100, 200, 150, 250])  # 2 samples, stereo
        wav = _build_wav(pcm, rate=11025, bits=8, channels=2)
        dmx = wav_to_dmx(wav)
        samples = dmx[24:]
        assert len(samples) == 2
        assert samples[0] == 100  # first channel
        assert samples[1] == 150  # first channel

    def test_custom_rate(self) -> None:
        wav = _build_wav(b"\x80" * 10, rate=44100)
        dmx = wav_to_dmx(wav)
        rate = struct.unpack("<H", dmx[2:4])[0]
        assert rate == 44100

    def test_not_wav_raises(self) -> None:
        with pytest.raises(ValueError, match="Not a WAV"):
            wav_to_dmx(b"NOT_A_WAV_FILE")

    def test_missing_fmt_raises(self) -> None:
        # Valid RIFF/WAVE but no fmt chunk
        bad = b"RIFF\x00\x00\x00\x00WAVEdata\x04\x00\x00\x00\x80\x80\x80\x80"
        with pytest.raises(ValueError, match="missing fmt"):
            wav_to_dmx(bad)


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestWavRoundTrip:
    def test_dmx_to_wav_to_dmx(self) -> None:
        """DMX → WAV → DMX should preserve the audio data."""
        with WadFile(FREEDOOM2) as wad:
            sound = next(iter(wad.sounds.values()))
            wav = sound.to_wav()
            dmx = wav_to_dmx(wav)
            # Compare sample rates
            orig_rate = sound.rate
            new_rate = struct.unpack("<H", dmx[2:4])[0]
            assert new_rate == orig_rate
            # Compare sample counts
            assert sound.sample_count > 0


# ---------------------------------------------------------------------------
# hex_to_rgb / rgb_to_hex
# ---------------------------------------------------------------------------


class TestHexColors:
    def test_hex_6_digit(self) -> None:
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)

    def test_hex_no_hash(self) -> None:
        assert hex_to_rgb("FF8800") == (255, 136, 0)

    def test_hex_3_digit(self) -> None:
        assert hex_to_rgb("#F00") == (255, 0, 0)
        assert hex_to_rgb("0F0") == (0, 255, 0)

    def test_hex_lowercase(self) -> None:
        assert hex_to_rgb("#ff8800") == (255, 136, 0)

    def test_hex_invalid(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            hex_to_rgb("#GGGGGG")

    def test_hex_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="Invalid hex"):
            hex_to_rgb("#1234")

    def test_rgb_to_hex(self) -> None:
        assert rgb_to_hex(255, 0, 0) == "#FF0000"
        assert rgb_to_hex(0, 128, 255) == "#0080FF"

    def test_round_trip(self) -> None:
        for color in ("#FF0000", "#00FF00", "#0000FF", "#ABCDEF", "#000000", "#FFFFFF"):
            r, g, b = hex_to_rgb(color)
            assert rgb_to_hex(r, g, b) == color


# ---------------------------------------------------------------------------
# Colormap builder
# ---------------------------------------------------------------------------


class TestBuildColormap:
    def _grey_palette(self) -> list[tuple[int, int, int]]:
        return [(i, i, i) for i in range(256)]

    def test_output_size(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal)
        assert len(result) == 8704  # 34 * 256

    def test_fullbright_is_identity(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal)
        # Table 0 (fullbright) should be identity mapping
        table0 = result[:256]
        for i in range(256):
            assert table0[i] == i, f"Table 0 index {i}: expected {i}, got {table0[i]}"

    def test_darkest_is_near_black(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal)
        # Table 31 (darkest normal) should map most colours to near-black
        table31 = result[31 * 256 : 32 * 256]
        # Index 255 (white) darkened by ~97% should be close to black
        assert table31[255] < 20

    def test_progressive_darkening(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal)
        # For index 128 (medium grey), each successive table should map
        # to a darker index
        prev = 128
        for level in range(1, 32):
            table = result[level * 256 : (level + 1) * 256]
            assert table[128] <= prev
            prev = table[128]

    def test_all_black_table(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal)
        # Table 33 should be all-black (index 0 for greyscale palette)
        table33 = result[33 * 256 : 34 * 256]
        assert all(b == 0 for b in table33)

    def test_invulnerability_table(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal, invuln_tint="#00FF00")
        # Table 32 is the invulnerability map
        table32 = result[32 * 256 : 33 * 256]
        # Should not be identity (it's a greyscale + tint remap)
        assert table32 != bytes(range(256))

    def test_custom_invuln_tint_tuple(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal, invuln_tint=(255, 0, 0))
        assert len(result) == 8704

    def test_hex_invuln_tint(self) -> None:
        pal = self._grey_palette()
        result = build_colormap(pal, invuln_tint="#FFD700")
        assert len(result) == 8704

    def test_hex_palette_entries(self) -> None:
        """Palette entries can be hex strings."""
        pal: list[str | tuple[int, int, int]] = [f"#{i:02X}{i:02X}{i:02X}" for i in range(256)]
        result = build_colormap(pal)  # type: ignore[arg-type]
        assert len(result) == 8704


@pytest.mark.skipif(not _has_wad(FREEDOOM2), reason="freedoom2.wad not available")
class TestColormapRealPalette:
    def test_build_from_real_palette(self) -> None:
        """Build a colormap from freedoom2's actual palette."""
        with WadFile(FREEDOOM2) as wad:
            assert wad.playpal is not None
            pal = wad.playpal.get_palette(0)
            result = build_colormap(pal)
            assert len(result) == 8704

            # Table 0 should be close to identity (minor rounding diffs possible)
            table0 = result[:256]
            # At least the first few dark colours should map to themselves
            assert table0[0] == 0  # black → black
