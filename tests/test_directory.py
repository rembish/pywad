"""Tests for WAD directory / lump listing."""

from wadlib.directory import DirectoryEntry
from wadlib.wad import WadFile


def test_directory_returns_list(freedoom1_wad: WadFile) -> None:
    assert isinstance(freedoom1_wad.directory, list)


def test_directory_entry_count_matches_header(freedoom1_wad: WadFile) -> None:
    assert len(freedoom1_wad.directory) == freedoom1_wad.directory_size


def test_directory_entries_are_directory_entries(freedoom1_wad: WadFile) -> None:
    for entry in freedoom1_wad.directory:
        assert isinstance(entry, DirectoryEntry)


def test_directory_entry_name_is_string(freedoom1_wad: WadFile) -> None:
    for entry in freedoom1_wad.directory:
        assert isinstance(entry.name, str)


def test_directory_entry_offset_non_negative(freedoom1_wad: WadFile) -> None:
    for entry in freedoom1_wad.directory:
        assert entry.offset >= 0


def test_directory_entry_size_non_negative(freedoom1_wad: WadFile) -> None:
    for entry in freedoom1_wad.directory:
        assert entry.size >= 0


def test_minimal_wad_directory(minimal_iwad: WadFile) -> None:
    # E1M1 marker + THINGS + VERTEXES + LINEDEFS = 4 entries
    assert len(minimal_iwad.directory) == 4


def test_directory_entry_repr(freedoom1_wad: WadFile) -> None:
    entry = freedoom1_wad.directory[0]
    assert repr(entry).startswith("<DirectoryEntry")


def test_doom2_directory_has_map_markers(freedoom2_wad: WadFile) -> None:
    names = {e.name for e in freedoom2_wad.directory}
    assert "MAP01" in names
