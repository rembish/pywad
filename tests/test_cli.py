"""CLI integration tests — invoke wadcli as a real subprocess.

All tests use freedoom2.wad (committed to repo, always available in CI).
Tests that need a second WAD (diff, freedoom1-specific) are skipped if
freedoom1.wad is absent.
"""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# wadcli entry point lives next to the Python interpreter that runs the tests.
_WADCLI = str(Path(sys.executable).parent / "wadcli")
_WADS_DIR = Path(__file__).parent.parent / "wads"
_F2 = str(_WADS_DIR / "freedoom2.wad")
_F1 = str(_WADS_DIR / "freedoom1.wad")

_HAS_F1 = (_WADS_DIR / "freedoom1.wad").exists()
_HAS_F2 = (_WADS_DIR / "freedoom2.wad").exists()

needs_f2 = pytest.mark.skipif(not _HAS_F2, reason="freedoom2.wad not found in wads/")
needs_f1 = pytest.mark.skipif(not _HAS_F1, reason="freedoom1.wad not found in wads/")


def wadcli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run wadcli with *args*, capture stdout/stderr, return CompletedProcess."""
    return subprocess.run([_WADCLI, *args], capture_output=True, text=True)


def wadcli_f2(*args: str) -> subprocess.CompletedProcess[str]:
    """Run wadcli with freedoom2.wad as --wad."""
    return wadcli("--wad", _F2, *args)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def test_help_exits_zero() -> None:
    r = wadcli("--help")
    assert r.returncode == 0


def test_help_mentions_subcommands() -> None:
    r = wadcli("--help")
    assert "check" in r.stdout
    assert "list" in r.stdout
    assert "export" in r.stdout


def test_no_args_prints_help() -> None:
    r = wadcli()
    # argparse prints help and exits 0 when no subcommand given
    assert "wadcli" in r.stdout or "wadcli" in r.stderr


# ---------------------------------------------------------------------------
# wadcli check
# ---------------------------------------------------------------------------


@needs_f2
def test_check_clean_wad_exits_zero() -> None:
    r = wadcli_f2("check")
    assert r.returncode == 0


@needs_f2
def test_check_clean_wad_no_issues_message() -> None:
    r = wadcli_f2("check")
    assert "No issues found" in r.stdout


@needs_f2
def test_check_json_output_is_valid() -> None:
    r = wadcli_f2("check", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list)
    assert data == []  # freedoom2 should be clean


def _make_bad_wad(tmp_path: Path, name: str = "bad.wad") -> Path:
    """Build a minimal IWAD with a sidedef referencing a non-existent texture."""
    sector_data = struct.pack(
        "<hh8s8sHHH", 0, 128, b"FLAT1\x00\x00\x00", b"FLAT1\x00\x00\x00", 160, 0, 0
    )
    sidedef_data = struct.pack(
        "<hh8s8s8sH",
        0,
        0,
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"XTEXTURE",
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
    lump_bytes = b"".join(d for _, d in lumps)
    dir_offset = 12 + len(lump_bytes)
    header = struct.pack("<4sII", b"IWAD", len(lumps), dir_offset)
    directory = b""
    offset = 12
    for lump_name, data in lumps:
        directory += struct.pack("<II8s", offset, len(data), lump_name.encode().ljust(8, b"\x00"))
        offset += len(data)
    wad_path = tmp_path / name
    wad_path.write_bytes(header + lump_bytes + directory)
    return wad_path


def test_check_bad_wad_exits_one(tmp_path: Path) -> None:
    """A WAD with a sidedef referencing a missing texture → exit 1."""
    wad_path = _make_bad_wad(tmp_path)
    # --wad is a global flag; must appear before the subcommand.
    r = wadcli("--wad", str(wad_path), "check")
    assert r.returncode == 1
    assert "missing_texture" in r.stdout


def test_check_bad_wad_json_reports_issue(tmp_path: Path) -> None:
    """--json output on a bad WAD is a non-empty list of issue objects."""
    wad_path = _make_bad_wad(tmp_path)
    r = wadcli("--wad", str(wad_path), "check", "--json")
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert all("map" in item and "kind" in item and "message" in item for item in data)


# ---------------------------------------------------------------------------
# wadcli diff
# ---------------------------------------------------------------------------


@needs_f2
def test_diff_identical_wads_exits_zero() -> None:
    """Comparing a WAD to itself → no differences → exit 0."""
    r = wadcli("diff", _F2, _F2)
    assert r.returncode == 0


@needs_f1
@needs_f2
def test_diff_different_wads_exits_one() -> None:
    """freedoom1 vs freedoom2 have differences → exit 1 (like Unix diff)."""
    r = wadcli("diff", _F1, _F2)
    assert r.returncode == 1


@needs_f1
@needs_f2
def test_diff_json_is_valid() -> None:
    # --json returns early (before sys.exit) so always exits 0
    r = wadcli("diff", _F1, _F2, "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, dict)
    assert "added" in data and "removed" in data and "changed" in data


@needs_f1
@needs_f2
def test_diff_reports_differences() -> None:
    """Output contains lump-level change entries."""
    r = wadcli("diff", _F1, _F2)
    assert len(r.stdout.strip()) > 0


# ---------------------------------------------------------------------------
# wadcli info
# ---------------------------------------------------------------------------


@needs_f2
def test_info_exits_zero() -> None:
    r = wadcli_f2("info")
    assert r.returncode == 0


@needs_f2
def test_info_mentions_iwad() -> None:
    r = wadcli_f2("info")
    assert "IWAD" in r.stdout or "iwad" in r.stdout.lower()


@needs_f2
def test_info_json_is_valid() -> None:
    r = wadcli_f2("info", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, dict)
    assert "type" in data


# ---------------------------------------------------------------------------
# wadcli list maps
# ---------------------------------------------------------------------------


@needs_f2
def test_list_maps_exits_zero() -> None:
    r = wadcli_f2("list", "maps")
    assert r.returncode == 0


@needs_f2
def test_list_maps_contains_map01() -> None:
    r = wadcli_f2("list", "maps")
    assert "MAP01" in r.stdout


@needs_f2
def test_list_maps_json_structure() -> None:
    r = wadcli_f2("list", "maps", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# wadcli list lumps
# ---------------------------------------------------------------------------


@needs_f2
def test_list_lumps_exits_zero() -> None:
    r = wadcli_f2("list", "lumps")
    assert r.returncode == 0


@needs_f2
def test_list_lumps_json_structure() -> None:
    r = wadcli_f2("list", "lumps", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert all("name" in e and "size" in e for e in data[:5])


@needs_f2
def test_list_lumps_filter() -> None:
    r = wadcli_f2("list", "lumps", "--filter", "MAP01")
    assert r.returncode == 0
    assert "MAP01" in r.stdout


# ---------------------------------------------------------------------------
# wadcli list textures / flats / sprites / sounds / music / patches / stats
# ---------------------------------------------------------------------------


@needs_f2
def test_list_textures_json() -> None:
    r = wadcli_f2("list", "textures", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert all("name" in t and "width" in t and "height" in t for t in data[:3])


@needs_f2
def test_list_flats_json() -> None:
    r = wadcli_f2("list", "flats", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0


@needs_f2
def test_list_sprites_json() -> None:
    r = wadcli_f2("list", "sprites", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


@needs_f2
def test_list_sounds_json() -> None:
    r = wadcli_f2("list", "sounds", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


@needs_f2
def test_list_music_json() -> None:
    r = wadcli_f2("list", "music", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


@needs_f2
def test_list_patches_json() -> None:
    r = wadcli_f2("list", "patches", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list) and len(data) > 0


@needs_f2
def test_list_stats_json() -> None:
    r = wadcli_f2("list", "stats", "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, dict)
    assert "maps" in data


# ---------------------------------------------------------------------------
# wadcli export map
# ---------------------------------------------------------------------------


@needs_f2
def test_export_map_creates_png(tmp_path: Path) -> None:
    out = str(tmp_path / "map01.png")
    r = wadcli_f2("export", "map", "MAP01", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@needs_f2
def test_export_map_custom_scale(tmp_path: Path) -> None:
    out = str(tmp_path / "map01_small.png")
    r = wadcli_f2("export", "map", "MAP01", out, "--scale", "0.05")
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()


@needs_f2
def test_export_map_alpha(tmp_path: Path) -> None:
    out = str(tmp_path / "map01_alpha.png")
    r = wadcli_f2("export", "map", "MAP01", out, "--alpha")
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()


@needs_f2
def test_export_map_unknown_name_fails(tmp_path: Path) -> None:
    out = str(tmp_path / "nope.png")
    r = wadcli_f2("export", "map", "NOTAMAP", out)
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# wadcli export flat
# ---------------------------------------------------------------------------


@needs_f2
def test_export_flat_creates_png(tmp_path: Path) -> None:
    out = str(tmp_path / "floor.png")
    r = wadcli_f2("export", "flat", "FLOOR0_1", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# wadcli export sound
# ---------------------------------------------------------------------------


@needs_f2
def test_export_sound_creates_wav(tmp_path: Path) -> None:
    out = str(tmp_path / "sound.wav")
    r = wadcli_f2("export", "sound", "DSBAREXP", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
    # WAV files start with "RIFF"
    assert Path(out).read_bytes()[:4] == b"RIFF"


# ---------------------------------------------------------------------------
# wadcli export music
# ---------------------------------------------------------------------------


@needs_f2
def test_export_music_creates_file(tmp_path: Path) -> None:
    out = str(tmp_path / "music.mid")
    r = wadcli_f2("export", "music", "D_ADRIAN", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# wadcli export lump (raw bytes)
# ---------------------------------------------------------------------------


@needs_f2
def test_export_lump_creates_file(tmp_path: Path) -> None:
    out = str(tmp_path / "playpal.bin")
    r = wadcli_f2("export", "lump", "PLAYPAL", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# wadcli export texture
# ---------------------------------------------------------------------------


@needs_f2
def test_export_texture_creates_png(tmp_path: Path) -> None:
    # Get first texture name from the WAD
    list_r = wadcli_f2("list", "textures", "--json")
    first_tex = json.loads(list_r.stdout)[0]["name"]
    out = str(tmp_path / "tex.png")
    r = wadcli_f2("export", "texture", first_tex, out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()


# ---------------------------------------------------------------------------
# wadcli export sprite
# ---------------------------------------------------------------------------


@needs_f2
def test_export_sprite_creates_png(tmp_path: Path) -> None:
    out = str(tmp_path / "sprite.png")
    r = wadcli_f2("export", "sprite", "AMMOA0", out)
    assert r.returncode == 0, r.stderr
    assert Path(out).exists()
