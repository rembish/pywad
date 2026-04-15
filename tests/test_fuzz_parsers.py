"""Property-based fuzz tests for binary and text lump parsers.

These tests verify that hardened parsers never raise unexpected low-level
exceptions (AssertionError, IndexError, struct.error, AttributeError, etc.)
when fed arbitrary byte or text inputs.  The only acceptable outcomes are:

- A successful parse (returns a value)
- CorruptLumpError  (corrupt / truncated binary data)
- ValueError        (explicitly invalid caller input, e.g. wrong DMX format)

Text parsers (UDMF, DECORATE, ZMAPINFO, MAPINFO) are lenient by design and
must never raise at all — arbitrary text simply produces empty/partial output.

Everything else is a bug in the hardening layer.
"""

from __future__ import annotations

import contextlib
import struct
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from wadlib.exceptions import CorruptLumpError
from wadlib.lumps.behavior import parse_behavior
from wadlib.lumps.decorate import parse_decorate
from wadlib.lumps.mapinfo import MapInfoLump
from wadlib.lumps.mus import Mus
from wadlib.lumps.picture import Picture
from wadlib.lumps.sound import DmxSound
from wadlib.lumps.textures import PNames, TextureList
from wadlib.lumps.udmf import parse_udmf
from wadlib.lumps.zmapinfo import ZMapInfoLump
from wadlib.wad import WadFile

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
    with contextlib.suppress(*exc_types):
        fn()


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


# ---------------------------------------------------------------------------
# Picture.decode — lump-based
# ---------------------------------------------------------------------------

_FAKE_PALETTE = [(0, 0, 0)] * 256


class TestFuzzPictureDecode:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_bytes_never_crash(self, data: bytes) -> None:
        """Picture.decode on arbitrary bytes never raises except CorruptLumpError."""
        lump = _make_lump("PATCH1", data, Picture)
        _assert_no_crash(lambda: lump.decode(_FAKE_PALETTE), CorruptLumpError)

    @given(
        width=st.integers(min_value=1, max_value=8),
        height=st.integers(min_value=1, max_value=8),
        tail=st.binary(max_size=256),
    )
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_header_arbitrary_tail_never_crash(
        self, width: int, height: int, tail: bytes
    ) -> None:
        """Valid picture header with arbitrary column/post data never crashes unexpectedly."""
        header = struct.pack("<HHhh", width, height, 0, 0)
        lump = _make_lump("PATCH1", header + tail, Picture)
        _assert_no_crash(lambda: lump.decode(_FAKE_PALETTE), CorruptLumpError)

    @given(
        width=st.integers(min_value=1, max_value=4),
        height=st.integers(min_value=1, max_value=4),
        topdelta=st.integers(min_value=0, max_value=10),
        post_len=st.integers(min_value=0, max_value=8),
        pixel=st.integers(min_value=0, max_value=255),
    )
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_single_post_never_crash(
        self, width: int, height: int, topdelta: int, post_len: int, pixel: int
    ) -> None:
        """Structurally valid picture with one post per column never crashes unexpectedly.

        Covers the out-of-bounds topdelta case (topdelta >= height) — must raise
        CorruptLumpError, not IndexError.
        """
        col_data_offset = 8 + width * 4  # after header + offset table
        header = struct.pack("<HHhh", width, height, 0, 0)
        col_offsets = struct.pack(f"<{width}I", *([col_data_offset] * width))
        # topdelta, post_len, pre-pad, pixels..., post-pad, end-of-column marker
        post = bytes([topdelta, post_len, 0]) + bytes([pixel] * post_len) + bytes([0, 0xFF])
        lump = _make_lump("PATCH1", header + col_offsets + post, Picture)
        _assert_no_crash(lambda: lump.decode(_FAKE_PALETTE), CorruptLumpError)

    @given(
        height=st.integers(min_value=1, max_value=4),
        topdelta=st.integers(min_value=0, max_value=8),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_out_of_bounds_topdelta_raises_corrupt_not_index_error(
        self, height: int, topdelta: int
    ) -> None:
        """When topdelta >= height the bounds check must fire; IndexError is never acceptable."""
        header = struct.pack("<HHhh", 1, height, 0, 0)
        col_data_offset = 8 + 4
        col_offset = struct.pack("<I", col_data_offset)
        # post_len=1 so we try to write exactly one pixel at row topdelta
        post = bytes([topdelta, 1, 0, 0, 0, 0xFF])
        lump = _make_lump("PATCH1", header + col_offset + post, Picture)
        _assert_no_crash(lambda: lump.decode(_FAKE_PALETTE), CorruptLumpError)


# ---------------------------------------------------------------------------
# parse_udmf — module-level function, takes a string
# ---------------------------------------------------------------------------


class TestFuzzParseUdmf:
    @given(text=st.text(max_size=512))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_text_never_crash(self, text: str) -> None:
        """parse_udmf on arbitrary text never raises any exception."""
        _assert_no_crash(lambda: parse_udmf(text))

    @given(text=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")), max_size=256))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_identifier_like_text_never_crash(self, text: str) -> None:
        """Identifier-like text (letters, digits, spaces) never crashes."""
        _assert_no_crash(lambda: parse_udmf(text))

    @given(
        ns=st.sampled_from(["doom", "heretic", "hexen", "zdoom", "eternity"]),
        body=st.text(max_size=256),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_namespace_header_never_crash(self, ns: str, body: str) -> None:
        """A valid namespace declaration followed by arbitrary body never crashes."""
        _assert_no_crash(lambda: parse_udmf(f'namespace = "{ns}";\n{body}'))


# ---------------------------------------------------------------------------
# parse_decorate — module-level function, takes a string
# ---------------------------------------------------------------------------


class TestFuzzParseDecorate:
    @given(text=st.text(max_size=512))
    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_text_never_crash(self, text: str) -> None:
        """parse_decorate on arbitrary text never raises any exception."""
        _assert_no_crash(lambda: parse_decorate(text))

    @given(
        name=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=12),
        body=st.text(max_size=128),
    )
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_actor_like_block_never_crash(self, name: str, body: str) -> None:
        """An actor block header followed by arbitrary body never crashes."""
        _assert_no_crash(lambda: parse_decorate(f"actor {name}\n{{\n{body}\n}}"))


# ---------------------------------------------------------------------------
# ZMapInfoLump.maps — lump-based
# ---------------------------------------------------------------------------


class TestFuzzZMapInfo:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_maps_arbitrary_bytes_never_crash(self, data: bytes) -> None:
        """ZMapInfoLump.maps on arbitrary bytes never raises any exception."""
        lump = _make_lump("ZMAPINFO", data, ZMapInfoLump)
        _assert_no_crash(lambda: lump.maps)

    @given(text=st.text(max_size=256))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_maps_arbitrary_text_bytes_never_crash(self, text: str) -> None:
        """ZMapInfoLump.maps on UTF-8-encoded arbitrary text never crashes."""
        data = text.encode("utf-8", errors="replace")
        lump = _make_lump("ZMAPINFO", data, ZMapInfoLump)
        _assert_no_crash(lambda: lump.maps)


# ---------------------------------------------------------------------------
# MapInfoLump.maps — lump-based
# ---------------------------------------------------------------------------


class TestFuzzMapInfo:
    @given(data=st.binary(max_size=512))
    @settings(max_examples=400, suppress_health_check=[HealthCheck.too_slow])
    def test_maps_arbitrary_bytes_never_crash(self, data: bytes) -> None:
        """MapInfoLump.maps on arbitrary bytes never raises any exception."""
        lump = _make_lump("MAPINFO", data, MapInfoLump)
        _assert_no_crash(lambda: lump.maps)

    @given(text=st.text(max_size=256))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_maps_arbitrary_text_bytes_never_crash(self, text: str) -> None:
        """MapInfoLump.maps on UTF-8-encoded arbitrary text never crashes."""
        data = text.encode("utf-8", errors="replace")
        lump = _make_lump("MAPINFO", data, MapInfoLump)
        _assert_no_crash(lambda: lump.maps)
