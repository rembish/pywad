"""Tests for MUS lump and MUS→MIDI conversion."""

import struct

from wadlib.lumps.mus import _MUS_MAGIC, _TICKS_PER_QN, Mus
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# WadFile.music / get_music
# ---------------------------------------------------------------------------


def test_music_dict_not_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.music) > 0


def test_music_dict_keys_start_with_d(doom1_wad: WadFile) -> None:
    for name in doom1_wad.music:
        assert name.startswith("D_"), name


def test_get_music_returns_mus(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert isinstance(mus, Mus)


def test_get_music_case_insensitive(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_music("d_e1m1") is not None


def test_get_music_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_music("D_NOEXIST") is None


# ---------------------------------------------------------------------------
# Mus.raw()
# ---------------------------------------------------------------------------


def test_raw_starts_with_mus_magic(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    assert mus.raw()[:4] == _MUS_MAGIC


# ---------------------------------------------------------------------------
# Mus.to_midi()
# ---------------------------------------------------------------------------


def test_to_midi_returns_bytes(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    midi = mus.to_midi()
    assert isinstance(midi, bytes)


def test_to_midi_mthd_header(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    midi = mus.to_midi()
    assert midi[:4] == b"MThd"


def test_to_midi_format_and_ticks(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    midi = mus.to_midi()
    # MThd: length=6, format=0, tracks=1, ticks=_TICKS_PER_QN
    _, length, fmt, tracks, ticks = struct.unpack_from(">4sIHHH", midi)
    assert length == 6
    assert fmt == 0
    assert tracks == 1
    assert ticks == _TICKS_PER_QN


def test_to_midi_mtrk_present(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    midi = mus.to_midi()
    assert midi[14:18] == b"MTrk"


def test_to_midi_nontrivial_length(doom1_wad: WadFile) -> None:
    mus = doom1_wad.get_music("D_E1M1")
    assert mus is not None
    midi = mus.to_midi()
    assert len(midi) > 256


def test_to_midi_all_tracks(doom1_wad: WadFile) -> None:
    """All music lumps should convert without error."""
    for name, mus in doom1_wad.music.items():
        midi = mus.to_midi()
        assert midi[:4] == b"MThd", f"{name}: bad MIDI header"
