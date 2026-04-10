"""Coverage-targeted tests for under-covered library modules.

Covers:
  - language.py
  - sndseq.py
  - zmapinfo.py
  - dehacked.py
  - wad.py (None-path accessors, font accessors)
  - renderer.py (floor rendering paths)
  - compositor.py (None path, multi-patch composition)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

_WADS_DIR = Path(__file__).parent.parent / "wads"
_BLASPHEMER = _WADS_DIR / "blasphem.wad"
_FREEDOOM1 = _WADS_DIR / "freedoom1.wad"
_FREEDOOM2 = _WADS_DIR / "freedoom2.wad"

needs_blasphem = pytest.mark.skipif(
    not _BLASPHEMER.exists(), reason="blasphem.wad not found in wads/"
)
needs_f1 = pytest.mark.skipif(not _FREEDOOM1.exists(), reason="freedoom1.wad not found in wads/")
needs_f2 = pytest.mark.skipif(not _FREEDOOM2.exists(), reason="freedoom2.wad not found in wads/")


# ---------------------------------------------------------------------------
# Helpers — copied from conftest since helpers aren't importable fixtures
# ---------------------------------------------------------------------------


def _build_wad(wad_type: str, lumps: list[tuple[str, bytes]]) -> bytes:
    """Build a minimal IWAD/PWAD in memory from a list of (name, data) pairs."""
    import struct

    num_lumps = len(lumps)
    data_start = 12
    lump_data = b"".join(d for _, d in lumps)
    dir_offset = data_start + len(lump_data)

    header = struct.pack("<4sII", wad_type.encode(), num_lumps, dir_offset)

    directory = b""
    offset = data_start
    for name, data in lumps:
        padded_name = name.encode().ljust(8, b"\x00")
        directory += struct.pack("<II8s", offset, len(data), padded_name)
        offset += len(data)

    return header + lump_data + directory


def _wad_from_bytes(data: bytes):  # type: ignore[return]
    """Open a WadFile from raw bytes via a temp file."""
    from wadlib.wad import WadFile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wad") as f:
        f.write(data)
        name = f.name
    return WadFile(name)


# ---------------------------------------------------------------------------
# language.py
# ---------------------------------------------------------------------------


@needs_blasphem
def test_language_not_none() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None


@needs_blasphem
def test_language_strings_non_empty() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None
        strings = w.language.strings
        assert isinstance(strings, dict)
        assert len(strings) > 0


@needs_blasphem
def test_language_lookup_valid_key() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None
        strings = w.language.strings
        # TXT_WPNMACE is the first key we confirmed exists
        key = next(iter(strings))
        val = w.language.lookup(key)
        assert val == strings[key]


@needs_blasphem
def test_language_lookup_case_insensitive() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None
        strings = w.language.strings
        key = next(iter(strings))
        assert w.language.lookup(key.lower()) == strings[key]


@needs_blasphem
def test_language_lookup_missing_returns_default() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None
        result = w.language.lookup("NONEXISTENT_KEY_XYZ", "fallback_value")
        assert result == "fallback_value"


@needs_blasphem
def test_language_lookup_missing_empty_default() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_BLASPHEMER)) as w:
        assert w.language is not None
        result = w.language.lookup("NONEXISTENT_KEY_XYZ")
        assert result == ""


# ---------------------------------------------------------------------------
# sndseq.py — build a minimal in-memory SNDSEQ lump
# ---------------------------------------------------------------------------


def test_sndseq_sequences_parsed() -> None:
    sndseq_bytes = (
        b":DoorOpen\nplayuntildone DSDOROPN\nend\n"
        b":DoorClose\nplaytime DSDORCLS 35\nend\n"
        b":AmbientBuzz\nplayrepeat DSAMBUZZ\nstopsound\nend\n"
    )
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        sndseq = w.sndseq
        assert sndseq is not None
        seqs = sndseq.sequences
        assert len(seqs) >= 2


def test_sndseq_sequence_names() -> None:
    sndseq_bytes = (
        b":DoorOpen\nplayuntildone DSDOROPN\nend\n:DoorClose\nplaytime DSDORCLS 35\nend\n"
    )
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        seqs = w.sndseq.sequences
        names = [s.name for s in seqs]
        assert "DoorOpen" in names
        assert "DoorClose" in names


def test_sndseq_first_sequence_has_commands() -> None:
    sndseq_bytes = b":DoorOpen\nplayuntildone DSDOROPN\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        seq = w.sndseq.sequences[0]
        assert seq.name == "DoorOpen"
        assert len(seq.commands) >= 1
        assert seq.commands[0].command == "playuntildone"
        assert seq.commands[0].sound == "DSDOROPN"


def test_sndseq_command_with_tics() -> None:
    sndseq_bytes = b":DoorClose\nplaytime DSDORCLS 35\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        seq = w.sndseq.sequences[0]
        assert seq.commands[0].tics == 35


def test_sndseq_get_by_name() -> None:
    sndseq_bytes = b":DoorOpen\nplayuntildone DSDOROPN\nend\n:DoorClose\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        seq = w.sndseq.get("DoorOpen")
        assert seq is not None
        assert seq.name == "DoorOpen"
        missing = w.sndseq.get("Nonexistent")
        assert missing is None


def test_sndseq_get_case_insensitive() -> None:
    sndseq_bytes = b":DoorOpen\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        assert w.sndseq.get("dooropen") is not None


def test_sndseq_comment_lines_ignored() -> None:
    sndseq_bytes = b"; this is a comment\n:DoorOpen\n; another comment\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        assert len(w.sndseq.sequences) == 1


def test_sndseq_stopsound_no_tics() -> None:
    sndseq_bytes = b":Seq\nstopsound\nend\n"
    wad_bytes = _build_wad("IWAD", [("SNDSEQ", sndseq_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.sndseq is not None
        seq = w.sndseq.sequences[0]
        cmd = seq.commands[0]
        assert cmd.command == "stopsound"
        assert cmd.sound is None


# ---------------------------------------------------------------------------
# zmapinfo.py — build a minimal in-memory ZMAPINFO lump
# ---------------------------------------------------------------------------


def test_zmapinfo_maps_parsed() -> None:
    # Parser requires opening brace on a separate line for correct parsing
    zmapinfo_bytes = b'map MAP01 "First Map"\n{\nmusic = D_E1M1\nlevelnum = 1\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        zmi = w.zmapinfo
        assert zmi is not None
        maps = zmi.maps
        assert len(maps) >= 1


def test_zmapinfo_map_name() -> None:
    zmapinfo_bytes = b'map MAP01 "First Map"\n{\nlevelnum = 1\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.maps[0]
        assert entry.map_name == "MAP01"


def test_zmapinfo_title_parsed() -> None:
    zmapinfo_bytes = b'map MAP01 "First Map"\n{\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.maps[0]
        assert entry.title == "First Map"


def test_zmapinfo_levelnum() -> None:
    zmapinfo_bytes = b'map MAP01 "Map"\n{\nlevelnum = 5\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        assert w.zmapinfo.maps[0].levelnum == 5


def test_zmapinfo_music_field() -> None:
    zmapinfo_bytes = b'map MAP01 "Map"\n{\nmusic = D_RUNNIN\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        assert w.zmapinfo.maps[0].music == "D_RUNNIN"


def test_zmapinfo_get_by_name() -> None:
    zmapinfo_bytes = b'map MAP01 "Map"\n{\n}\nmap MAP02 "Map 2"\n{\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.get("MAP01")
        assert entry is not None
        assert entry.map_name == "MAP01"
        assert w.zmapinfo.get("MAP99") is None


def test_zmapinfo_multiple_maps() -> None:
    zmapinfo_bytes = (
        b'map MAP01 "Map 1"\n{\nlevelnum = 1\n}\n'
        b'map MAP02 "Map 2"\n{\nlevelnum = 2\nnext = MAP03\n}\n'
    )
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        maps = w.zmapinfo.maps
        assert len(maps) == 2
        assert maps[1].next == "MAP03"


def test_zmapinfo_next_field() -> None:
    zmapinfo_bytes = b'map MAP01 "Map"\n{\nnext = MAP02\nsecreetnext = MAP31\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.maps[0]
        assert entry.next == "MAP02"


def test_zmapinfo_sky1_cluster_par() -> None:
    zmapinfo_bytes = b'map MAP01 "Map"\n{\nsky1 = SKY1\ncluster = 1\npar = 90\n}\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.maps[0]
        assert entry.sky1 == "SKY1"
        assert entry.cluster == 1
        assert entry.par == 90


def test_zmapinfo_resolved_title_with_language() -> None:
    zmapinfo_bytes = b'map MAP01 lookup "HUSTR_1" { }\n'
    wad_bytes = _build_wad("IWAD", [("ZMAPINFO", zmapinfo_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        assert w.zmapinfo is not None
        entry = w.zmapinfo.maps[0]
        # Without language dict — returns empty title
        assert entry.resolved_title() == ""
        # With language dict
        fake_lang = {"HUSTR_1": "Entryway"}
        assert entry.resolved_title(fake_lang) == "Entryway"


def test_zmapinfo_strip_comments() -> None:
    from wadlib.lumps.zmapinfo import _strip_comments

    text = '// line comment\nmap MAP01 /* block */ "Map" { }\n'
    stripped = _strip_comments(text)
    assert "line comment" not in stripped
    assert "block" not in stripped


# ---------------------------------------------------------------------------
# dehacked.py
# ---------------------------------------------------------------------------


@needs_f1
def test_dehacked_not_none() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert w.dehacked is not None


@needs_f1
def test_dehacked_doom_version() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert w.dehacked is not None
        assert w.dehacked.doom_version is not None
        assert isinstance(w.dehacked.doom_version, int)


@needs_f1
def test_dehacked_par_times() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert w.dehacked is not None
        par_times = w.dehacked.par_times
        assert isinstance(par_times, dict)
        assert len(par_times) > 0


@needs_f1
def test_dehacked_patch_format() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert w.dehacked is not None
        # patch_format may be None if not present, but should not error
        pf = w.dehacked.patch_format
        assert pf is None or isinstance(pf, int)


@needs_f1
def test_dehacked_raw_bytes() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert w.dehacked is not None
        raw = w.dehacked.raw()
        assert len(raw) > 100


# ---------------------------------------------------------------------------
# wad.py — None-path and font accessors
# ---------------------------------------------------------------------------


@needs_f2
def test_wad_language_none() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert w.language is None


@needs_f2
def test_wad_sndseq_none() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert w.sndseq is None


@needs_f2
def test_wad_zmapinfo_none() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert w.zmapinfo is None


@needs_f2
def test_wad_stcfn_returns_dict() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        glyphs = w.stcfn
        assert isinstance(glyphs, dict)
        assert len(glyphs) > 0


@needs_f2
def test_wad_fonta_empty_on_doom() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert isinstance(w.fonta, dict)
        # freedoom2 has no FONTA_S/FONTA_E markers
        assert len(w.fonta) == 0


@needs_f2
def test_wad_fontb_empty_on_doom() -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert isinstance(w.fontb, dict)
        assert len(w.fontb) == 0


# ---------------------------------------------------------------------------
# renderer.py — floor rendering paths (BSP clipping)
# ---------------------------------------------------------------------------


@needs_f1
def test_floor_rendering_executes() -> None:
    """Run show_floors=True on a tiny scale to exercise BSP clipping code."""
    from wadlib.renderer import MapRenderer, RenderOptions
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        assert len(w.maps) > 0
        m = w.maps[0]
        # Very small scale keeps it fast; enough to exercise the BSP walk.
        opts = RenderOptions(show_floors=True, scale=0.02)
        renderer = MapRenderer(m, wad=w, options=opts)
        img = renderer.render()
        assert img is not None
        assert img.size[0] > 0 and img.size[1] > 0


@needs_f2
def test_floor_rendering_freedoom2() -> None:
    """Floor rendering on freedoom2 MAP01 at tiny scale."""
    from wadlib.renderer import MapRenderer, RenderOptions
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        target = next((m for m in w.maps if str(m) == "MAP01"), None)
        if target is None:
            pytest.skip("MAP01 not found")
        opts = RenderOptions(show_floors=True, scale=0.02)
        renderer = MapRenderer(target, wad=w, options=opts)
        img = renderer.render()
        assert img is not None


@needs_f1
def test_floor_rendering_alpha_mode() -> None:
    """Floor rendering with alpha=True."""
    from wadlib.renderer import MapRenderer, RenderOptions
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM1)) as w:
        m = w.maps[0]
        opts = RenderOptions(show_floors=True, scale=0.02, alpha=True)
        renderer = MapRenderer(m, wad=w, options=opts)
        img = renderer.render()
        assert img.mode == "RGBA"


@needs_f1
def test_clip_poly_direct() -> None:
    """Test the Sutherland-Hodgman clip polygon function directly."""
    from wadlib.renderer import _clip_poly

    # A simple square polygon
    poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    # Clip keeping right side of x=5 partition (nx=5, ny=0, ndx=0, ndy=1)
    result = _clip_poly(poly, 5.0, 0.0, 0.0, 1.0, keep_right=True)
    # Right side: x >= 5
    assert len(result) >= 3
    for pt in result:
        assert pt[0] >= 4.9


@needs_f1
def test_clip_poly_degenerate() -> None:
    """Degenerate polygon with fewer than 2 points returns empty."""
    from wadlib.renderer import _clip_poly

    result = _clip_poly([(0.0, 0.0)], 5.0, 0.0, 0.0, 1.0, keep_right=True)
    assert result == []


# ---------------------------------------------------------------------------
# compositor.py — None path and multi-patch
# ---------------------------------------------------------------------------


@needs_f2
def test_compositor_nonexistent_returns_none() -> None:
    from wadlib.compositor import TextureCompositor
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        comp = TextureCompositor(w)
        result = comp.compose("NOTEXTURE_XYZ_NONEXISTENT")
        assert result is None


@needs_f2
def test_compositor_known_texture() -> None:
    from wadlib.compositor import TextureCompositor
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert w.texture1 is not None
        first_tex = w.texture1.textures[0].name
        comp = TextureCompositor(w)
        img = comp.compose(first_tex)
        assert img is not None
        assert img.size[0] > 0 and img.size[1] > 0


@needs_f2
def test_compositor_multi_patch_texture() -> None:
    """Find a multi-patch texture and compose it."""
    from wadlib.compositor import TextureCompositor
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        assert w.texture1 is not None
        # Find a texture with more than one patch
        multi = next(
            (t for t in w.texture1.textures if len(t.patches) > 1),
            None,
        )
        if multi is None:
            pytest.skip("No multi-patch texture found in TEXTURE1")
        comp = TextureCompositor(w)
        img = comp.compose(multi.name)
        assert img is not None
        assert img.size == (multi.width, multi.height)


@pytest.mark.slow
@needs_f2
def test_compositor_compose_all() -> None:
    """compose_all returns a non-empty dict."""
    from wadlib.compositor import TextureCompositor
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        comp = TextureCompositor(w)
        all_textures = comp.compose_all()
        assert isinstance(all_textures, dict)
        assert len(all_textures) > 0


# ---------------------------------------------------------------------------
# ogg.py — MidiLump.save() (OggLump/Mp3Lump have no test WAD, MidiLump does)
# ---------------------------------------------------------------------------


@needs_f2
def test_midi_lump_save(tmp_path: Path) -> None:
    from wadlib.wad import WadFile

    with WadFile(str(_FREEDOOM2)) as w:
        music = w.music
        midi_lump = next((v for v in music.values() if type(v).__name__ == "MidiLump"), None)
        if midi_lump is None:
            pytest.skip("No MidiLump found in freedoom2")
        out = str(tmp_path / "track.mid")
        midi_lump.save(out)
        assert Path(out).exists() and Path(out).stat().st_size > 0


def test_ogg_lump_save(tmp_path: Path) -> None:
    from wadlib.lumps.ogg import OggLump
    from wadlib.wad import WadFile

    # Build a minimal WAD with a fake OGG lump (just needs OggS magic).
    ogg_bytes = b"OggS" + b"\x00" * 60
    wad_bytes = _build_wad("IWAD", [("D_FAKE", ogg_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        entry = next(e for e in w.directory if e.name == "D_FAKE")
        lump = OggLump(entry)
        out = str(tmp_path / "fake.ogg")
        lump.save(out)
        assert Path(out).read_bytes()[:4] == b"OggS"


def test_mp3_lump_save(tmp_path: Path) -> None:
    from wadlib.lumps.ogg import Mp3Lump
    from wadlib.wad import WadFile

    mp3_bytes = b"ID3" + b"\x00" * 60
    wad_bytes = _build_wad("IWAD", [("D_FAKE", mp3_bytes)])
    with _wad_from_bytes(wad_bytes) as w:
        entry = next(e for e in w.directory if e.name == "D_FAKE")
        lump = Mp3Lump(entry)
        out = str(tmp_path / "fake.mp3")
        lump.save(out)
        assert Path(out).read_bytes()[:3] == b"ID3"


# ---------------------------------------------------------------------------
# renderer.py — _clip_poly intersection path + show()
# ---------------------------------------------------------------------------


def test_clip_poly_intersection() -> None:
    """_clip_poly must compute an intersection when prev is in, curr is out."""
    from wadlib.renderer import _clip_poly

    # Square: two points above (in) and two below (out) the partition y=0 line.
    # Partition line: point (0,0), direction (1,0) → keeps points with cross>=0.
    # cross = (px-0)*0 - (py-0)*1 = -py  → keep where -py >= 0 → py <= 0
    # So keep points with y <= 0.
    poly = [(0.0, -1.0), (1.0, -1.0), (1.0, 1.0), (0.0, 1.0)]
    clipped = _clip_poly(poly, 0.0, 0.0, 1.0, 0.0, keep_right=True)
    # Should have 4 points: two original below and two intersections at y=0
    assert len(clipped) == 4
    assert all(y <= 0.0 + 1e-9 for _, y in clipped)


def test_clip_poly_empty_polygon() -> None:
    from wadlib.renderer import _clip_poly

    result = _clip_poly([], 0.0, 0.0, 1.0, 0.0, keep_right=True)
    assert result == []


# ---------------------------------------------------------------------------
# list_animations.py — synthetic ANIMDEFS WAD to cover all branches
# ---------------------------------------------------------------------------


def test_list_animations_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """list animations --json with a synthetic ANIMDEFS lump."""
    import argparse

    from wadlib.cli.commands import list_animations

    animdefs_text = (
        b"; Doom-format ANIMDEFS\n"
        b"flat NUKAGE1\n"
        b"  pic 1 tics 8\n"
        b"  pic 2 tics 8\n"
        b"  pic 3 tics 8\n"
        b"texture BLODGR1\n"
        b"  pic 1 rand 6 10\n"
        b"  pic 2 rand 6 10\n"
    )
    wad_bytes = _build_wad("IWAD", [("ANIMDEFS", animdefs_text)])
    with _wad_from_bytes(wad_bytes) as w:
        with _wad_from_bytes(wad_bytes) as w2:
            import json

            ns = argparse.Namespace(wad=None, pwads=[], deh=None, json=True)
            # Monkey-patch open_wad context to use our WadFile
            from unittest.mock import patch as mpatch

            with mpatch("wadlib.cli.commands.list_animations.open_wad") as mock_ow:
                mock_ow.return_value.__enter__ = lambda s: w
                mock_ow.return_value.__exit__ = lambda s, *a: False
                list_animations.run(ns)
            out = capsys.readouterr().out
            data = json.loads(out)
            assert isinstance(data, list)
            assert len(data) >= 1
            assert "name" in data[0]


def test_list_animations_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """list animations text mode with a synthetic ANIMDEFS lump."""
    import argparse

    from wadlib.cli.commands import list_animations

    animdefs_text = (
        b"flat NUKAGE1\n"
        b"  pic 1 tics 8\n"
        b"  pic 2 rand 4 12\n"
    )
    wad_bytes = _build_wad("IWAD", [("ANIMDEFS", animdefs_text)])
    with _wad_from_bytes(wad_bytes) as w:
        ns = argparse.Namespace(wad=None, pwads=[], deh=None, json=False)
        from unittest.mock import patch as mpatch

        with mpatch("wadlib.cli.commands.list_animations.open_wad") as mock_ow:
            mock_ow.return_value.__enter__ = lambda s: w
            mock_ow.return_value.__exit__ = lambda s, *a: False
            list_animations.run(ns)
        out = capsys.readouterr().out
        assert "NUKAGE1" in out


def test_list_animations_no_animdefs(capsys: pytest.CaptureFixture[str]) -> None:
    """list animations exits 1 when no ANIMDEFS lump present."""
    import argparse
    import sys

    from wadlib.cli.commands import list_animations

    wad_bytes = _build_wad("IWAD", [("DUMMY", b"\x00")])
    with _wad_from_bytes(wad_bytes) as w:
        ns = argparse.Namespace(wad=None, pwads=[], deh=None, json=False)
        from unittest.mock import patch as mpatch

        with mpatch("wadlib.cli.commands.list_animations.open_wad") as mock_ow:
            mock_ow.return_value.__enter__ = lambda s: w
            mock_ow.return_value.__exit__ = lambda s, *a: False
            with pytest.raises(SystemExit) as exc:
                list_animations.run(ns)
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# compositor.py — compose_all with minimal synthetic WAD (fast, covers 72-80)
# ---------------------------------------------------------------------------


def test_compositor_compose_all_minimal(tmp_path: Path) -> None:
    """compose_all with a 1-texture WAD: covers lines 72-80 including texture2=None branch."""
    import struct

    from wadlib.compositor import TextureCompositor

    # Build PNAMES: 1 patch named "FAKEPAT1"
    pnames_data = struct.pack("<I", 1) + b"FAKEPAT1"

    # Build TEXTURE1: 1 texture "MYTEX" (64×64) using patch_index=0
    # Also include a patch with out-of-range index=99 to cover line 60
    TEX_HDR_FMT = "<8sIHHIH"
    PATCH_FMT = "<hhHhh"
    tex_hdr = struct.pack(TEX_HDR_FMT, b"MYTEX\x00\x00\x00", 0, 64, 64, 0, 2)
    patch1 = struct.pack(PATCH_FMT, 0, 0, 0, 0, 0)   # valid index 0
    patch2 = struct.pack(PATCH_FMT, 0, 0, 99, 0, 0)  # out-of-range index 99 → covers line 60
    tex_def = tex_hdr + patch1 + patch2
    # TEXTURE1 layout: count(4) + offset(4) + tex_def
    tex1_data = struct.pack("<I", 1) + struct.pack("<I", 8) + tex_def

    # Minimal PLAYPAL: 1 palette = 256 × 3 bytes of zeros
    playpal_data = b"\x00" * (256 * 3)

    # No picture lump named FAKEPAT1 → wad.get_picture() returns None → covers line 64
    wad_bytes = _build_wad(
        "IWAD",
        [
            ("PLAYPAL", playpal_data),
            ("PNAMES", pnames_data),
            ("TEXTURE1", tex1_data),
        ],
    )
    with _wad_from_bytes(wad_bytes) as w:
        comp = TextureCompositor(w)
        all_textures = comp.compose_all()
        # MYTEX composed (all patches skipped but canvas returned)
        assert isinstance(all_textures, dict)
        # texture2 is None → compose_all hits the continue at line 75


def test_renderer_show(tmp_path: Path) -> None:
    """show() should call im.show() without crashing (mock PIL show)."""
    from unittest.mock import patch
    from wadlib.lumps.map import Doom2MapEntry
    from wadlib.renderer import MapRenderer

    # Re-use the minimal IWAD helper to get a map entry
    import struct

    vertex_data = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)
    linedef_data = struct.pack("<HHHHHhh", 0, 1, 1, 0, 0, 0, -1)
    thing_data = struct.pack("<hhHHH", 0, 0, 0, 1, 7)
    lumps: list[tuple[str, bytes]] = [
        ("MAP01", b""),
        ("THINGS", thing_data),
        ("VERTEXES", vertex_data),
        ("LINEDEFS", linedef_data),
    ]
    wad_bytes = _build_wad("IWAD", lumps)
    wad_path = tmp_path / "t.wad"
    wad_path.write_bytes(wad_bytes)
    from wadlib.wad import WadFile

    with WadFile(str(wad_path)) as w:
        r = MapRenderer(w.maps[0])
        r.render()
        with patch.object(r.im, "show") as mock_show:
            r.show()
            mock_show.assert_called_once()
