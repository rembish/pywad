"""Tests for ENDOOM lump decoder."""

from wadlib.lumps.endoom import Endoom
from wadlib.wad import WadFile


def test_endoom_not_none(doom1_wad: WadFile) -> None:
    assert doom1_wad.endoom is not None


def test_endoom_is_endoom_instance(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.endoom, Endoom)


def test_to_text_returns_str(doom1_wad: WadFile) -> None:
    endoom = doom1_wad.endoom
    assert endoom is not None
    result = endoom.to_text()
    assert isinstance(result, str)


def test_to_text_has_newlines(doom1_wad: WadFile) -> None:
    endoom = doom1_wad.endoom
    assert endoom is not None
    result = endoom.to_text()
    assert "\n" in result


def test_to_text_25_lines(doom1_wad: WadFile) -> None:
    endoom = doom1_wad.endoom
    assert endoom is not None
    lines = endoom.to_text().split("\n")
    assert len(lines) == 25


def test_to_ansi_returns_str(doom1_wad: WadFile) -> None:
    endoom = doom1_wad.endoom
    assert endoom is not None
    result = endoom.to_ansi()
    assert isinstance(result, str)


def test_to_ansi_contains_escape_codes(doom1_wad: WadFile) -> None:
    endoom = doom1_wad.endoom
    assert endoom is not None
    result = endoom.to_ansi()
    assert "\x1b[" in result
