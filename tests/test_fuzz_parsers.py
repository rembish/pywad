"""Property-based fuzz tests for binary lump parsers.

These tests verify that hardened parsers never raise unexpected low-level
exceptions (AssertionError, IndexError, struct.error, AttributeError, etc.)
when fed arbitrary byte inputs.  The only acceptable outcomes are:

- A successful parse (returns a value)
- CorruptLumpError  (corrupt / truncated data)
- ValueError        (explicitly invalid caller input, e.g. wrong DMX format)

Everything else is a bug in the hardening layer.
"""

from __future__ import annotations

import struct
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from wadlib.exceptions import CorruptLumpError
from wadlib.lumps.behavior import parse_behavior
from wadlib.lumps.mus import Mus
from wadlib.lumps.sound import DmxSound
from wadlib.lumps.textures import PNames, TextureList

# ---------------------------------------------------------------------------
# Helpers — build minimal WAD bytes around a lump so we can open it
# ---------------------------------------------------------------------------

_MUS_MAGIC = b"MUS\x1a"


def _build_single_lump_wad(name: bytes, data: bytes) -> bytes:
    """Return raw WAD bytes containing exactly one lump."""
    padded_name = name.ljust(8, b"\x00")[:8]
    lump_data_offset = 12
    dir_offset = lump_data_offset + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", lump_data_offset, len(data), padded_name)
    return header + data + entry


def _make_lump(name: str, data: bytes, cls: type) -> Any:
    """Write a single-lump WAD to a fresh temp directory and return the lump object."""
    from wadlib.wad import WadFile

    raw = _build_single_lump_wad(name.encode().ljust(8, b"\x00")[:8], data)
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / f"{name}.wad"
        path.write_bytes(raw)
        with WadFile(str(path)) as wad:
            entry = wad.find_lump(name)
            assert entry is not None
            return cls(entry)


# ---------------------------------------------------------------------------
# Allowed exception types for each parser
# ---------------------------------------------------------------------------

_LUMP_OK = (CorruptLumpError, ValueError)


def _assert_no_crash(fn, *exc_types):
    """Call *fn()*, allowing listed exception types but re-raising anything else."""
    try:
        fn()
    except exc_types:
        pass


# ---------------------------------------------------------------------------
# parse_behavior — module-level function, no WAD needed
# ---------------------------------------------------------------------------


class TestFuzzParseBehavior:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_bytes_never_crash(self, data: bytes) -> None:
        """parse_behavior on arbitrary bytes never raises except CorruptLumpError."""
        _assert_no_crash(lambda: parse_behavior(data), CorruptLumpError)

    @given(
        data=st.binary(min_size=8, max_size=512),
        magic=st.sampled_from([b"ACS\x00", b"ACSE", b"ACSe"]),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_magic_prefix_never_crash(self, data: bytes, magic: bytes) -> None:
        """Known-magic prefixes should parse without unexpected crashes."""
        _assert_no_crash(lambda: parse_behavior(magic + data[4:]), CorruptLumpError)


# ---------------------------------------------------------------------------
# PNames — lump-based
# ---------------------------------------------------------------------------


class TestFuzzPNames:
    @given(data=st.binary(max_size=256))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_names_never_crash(self, data: bytes) -> None:
        """PNames.names on arbitrary lump data never raises except CorruptLumpError."""
        lump = _make_lump("PNAMES", data, PNames)
        _assert_no_crash(lambda: lump.names, CorruptLumpError)

    @given(data=st.binary(max_size=256))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_len_never_crash(self, data: bytes) -> None:
        """PNames.__len__ on arbitrary lump data never raises."""
        lump = _make_lump("PNAMES", data, PNames)
        _assert_no_crash(lambda: len(lump))


# ---------------------------------------------------------------------------
# TextureList — lump-based
# ---------------------------------------------------------------------------


class TestFuzzTextureList:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_textures_never_crash(self, data: bytes) -> None:
        """TextureList.textures on arbitrary bytes never raises except CorruptLumpError."""
        lump = _make_lump("TEXTURE1", data, TextureList)
        _assert_no_crash(lambda: lump.textures, CorruptLumpError)

    @given(data=st.binary(max_size=256))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_len_never_crash(self, data: bytes) -> None:
        lump = _make_lump("TEXTURE1", data, TextureList)
        _assert_no_crash(lambda: len(lump))


# ---------------------------------------------------------------------------
# Mus.to_midi — lump-based
# ---------------------------------------------------------------------------


class TestFuzzMus:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_to_midi_arbitrary_never_crash(self, data: bytes) -> None:
        """Mus.to_midi on arbitrary bytes never raises except CorruptLumpError/ValueError."""
        lump = _make_lump("D_E1M1", data, Mus)
        _assert_no_crash(lambda: lump.to_midi(), CorruptLumpError, ValueError)

    @given(tail=st.binary(max_size=256))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_to_midi_valid_magic_never_crash(self, tail: bytes) -> None:
        """MUS-magic-prefixed data with arbitrary event bytes never crashes unexpectedly."""
        score_start = struct.calcsize("<4sHHHHHH")  # 16
        score_len = len(tail)
        header = struct.pack("<4sHHHHHH", _MUS_MAGIC, score_len, score_start, 0, 0, 0, 0)
        lump = _make_lump("D_E1M1", header + tail, Mus)
        _assert_no_crash(lambda: lump.to_midi(), CorruptLumpError, ValueError)


# ---------------------------------------------------------------------------
# DmxSound.to_wav — lump-based
# ---------------------------------------------------------------------------


class TestFuzzDmxSound:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_to_wav_arbitrary_never_crash(self, data: bytes) -> None:
        """DmxSound.to_wav on arbitrary bytes never raises except CorruptLumpError/ValueError."""
        lump = _make_lump("DSPISTOL", data, DmxSound)
        _assert_no_crash(lambda: lump.to_wav(), CorruptLumpError, ValueError)
