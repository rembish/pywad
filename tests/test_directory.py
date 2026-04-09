"""Tests for WAD directory / lump listing."""

from pywad.directory import DirectoryEntry
from pywad.wad import WadFile


def test_directory_returns_list(doom1_wad: WadFile) -> None:
    assert isinstance(doom1_wad.directory, list)


def test_directory_entry_count_matches_header(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.directory) == doom1_wad.directory_size


def test_directory_entries_are_directory_entries(doom1_wad: WadFile) -> None:
    for entry in doom1_wad.directory:
        assert isinstance(entry, DirectoryEntry)


def test_directory_entry_name_is_string(doom1_wad: WadFile) -> None:
    for entry in doom1_wad.directory:
        assert isinstance(entry.name, str)


def test_directory_entry_offset_non_negative(doom1_wad: WadFile) -> None:
    for entry in doom1_wad.directory:
        assert entry.offset >= 0


def test_directory_entry_size_non_negative(doom1_wad: WadFile) -> None:
    for entry in doom1_wad.directory:
        assert entry.size >= 0


def test_minimal_wad_directory(minimal_iwad: WadFile) -> None:
    # E1M1 marker + THINGS + VERTEXES + LINEDEFS = 4 entries
    assert len(minimal_iwad.directory) == 4


def test_directory_entry_repr(doom1_wad: WadFile) -> None:
    entry = doom1_wad.directory[0]
    assert repr(entry).startswith("<DirectoryEntry")


def test_doom2_directory_has_map_markers(doom2_wad: WadFile) -> None:
    names = {e.name for e in doom2_wad.directory}
    assert "MAP01" in names
