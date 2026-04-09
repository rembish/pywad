"""Tests for DMX sound lump decoder."""

from wadlib.lumps.sound import DmxSound
from wadlib.wad import WadFile


def test_sounds_not_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.sounds) > 0


def test_sounds_keys_start_with_ds_or_dp(doom1_wad: WadFile) -> None:
    for name in doom1_wad.sounds:
        assert name.startswith("DS") or name.startswith("DP"), name


def test_get_sound_returns_dmxsound(doom1_wad: WadFile) -> None:
    snd = doom1_wad.get_sound("DSPISTOL")
    assert isinstance(snd, DmxSound)


def test_get_sound_case_insensitive(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_sound("dspistol") is not None


def test_get_sound_missing_returns_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.get_sound("DSNOEXIST") is None


def test_to_wav_starts_with_riff(doom1_wad: WadFile) -> None:
    snd = doom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    wav = snd.to_wav()
    assert wav[:4] == b"RIFF"


def test_to_wav_has_wave_marker(doom1_wad: WadFile) -> None:
    snd = doom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    wav = snd.to_wav()
    assert wav[8:12] == b"WAVE"


def test_to_wav_returns_bytes(doom1_wad: WadFile) -> None:
    snd = doom1_wad.get_sound("DSPISTOL")
    assert snd is not None
    assert isinstance(snd.to_wav(), bytes)
