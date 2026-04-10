"""Tests for wadcli check command logic."""

import struct
from pathlib import Path

from wadlib.cli.commands.check import Issue, _check_map, _flat_names, _texture_names
from wadlib.wad import WadFile


def test_freedoom1_no_issues(freedoom1_wad: WadFile) -> None:
    """A well-formed IWAD should report no authoring issues."""
    textures = _texture_names(freedoom1_wad)
    flats = _flat_names(freedoom1_wad)
    issues: list[Issue] = []
    for m in freedoom1_wad.maps:
        _check_map(m, textures, flats, issues)
    assert issues == []


def test_texture_names_non_empty(freedoom1_wad: WadFile) -> None:
    textures = _texture_names(freedoom1_wad)
    assert len(textures) > 0


def test_flat_names_non_empty(freedoom1_wad: WadFile) -> None:
    flats = _flat_names(freedoom1_wad)
    assert len(flats) > 0


def test_no_texture_sentinel_is_always_valid(freedoom1_wad: WadFile) -> None:
    """'-' must never appear as a missing-texture issue."""
    textures = _texture_names(freedoom1_wad)
    flats = _flat_names(freedoom1_wad)
    issues: list[Issue] = []
    for m in freedoom1_wad.maps:
        _check_map(m, textures, flats, issues)
    assert not any("'-'" in i.message for i in issues)


def test_missing_texture_detected(tmp_path: Path) -> None:
    """Inject a sidedef referencing a non-existent texture — expect a report."""
    # Build a minimal IWAD with one map, one sector, one sidedef, one linedef.
    # The sidedef uses a middle_texture that does not exist.
    sector_data = struct.pack(
        "<hh8s8sHHH", 0, 128, b"FLAT1\x00\x00\x00", b"FLAT1\x00\x00\x00", 160, 0, 0
    )
    sidedef_data = struct.pack(
        "<hh8s8s8sH",
        0,
        0,
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"XTEXTURE\x00"[:8],
        0,
    )
    vertex_data = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)
    linedef_data = struct.pack("<HHHHHhh", 0, 1, 1, 0, 0, 0, -1)

    lumps: list[tuple[str, bytes]] = [
        ("E1M1", b""),
        ("THINGS", struct.pack("<hhHHH", 32, 32, 0, 1, 7)),
        ("VERTEXES", vertex_data),
        ("LINEDEFS", linedef_data),
        ("SIDEDEFS", sidedef_data),
        ("SECTORS", sector_data),
    ]
    num_lumps = len(lumps)
    lump_bytes = b"".join(d for _, d in lumps)
    dir_offset = 12 + len(lump_bytes)
    header = struct.pack("<4sII", b"IWAD", num_lumps, dir_offset)
    directory = b""
    offset = 12
    for name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), name.encode().ljust(8, b"\x00"))
        offset += len(data)

    wad_path = tmp_path / "bad.wad"
    wad_path.write_bytes(header + lump_bytes + directory)

    with WadFile(str(wad_path)) as wad:
        issues: list[Issue] = []
        for m in wad.maps:
            _check_map(m, frozenset(), frozenset({"FLAT1"}), issues)

    missing = [i for i in issues if i.kind == "missing_texture"]
    assert len(missing) >= 1
    assert any("XTEXTURE" in i.message.upper() for i in missing)
