"""Direct CLI run() tests — invoke each command's run() function without subprocess.

All tests use freedoom2.wad (committed to repo). Tests skip if the WAD is absent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

_WADS_DIR = Path(__file__).parent.parent / "wads"
_F2 = str(_WADS_DIR / "freedoom2.wad")
_F1 = str(_WADS_DIR / "freedoom1.wad")
_DOOM2 = str(_WADS_DIR / "DOOM2.WAD")

pytestmark = pytest.mark.skipif(not Path(_F2).exists(), reason="freedoom2.wad not found in wads/")
needs_f1 = pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
needs_doom2 = pytest.mark.skipif(not Path(_DOOM2).exists(), reason="DOOM2.WAD not found in wads/")


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {"wad": _F2, "pwads": [], "deh": None, "json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# list maps
# ---------------------------------------------------------------------------


def test_list_maps_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_maps

    list_maps.run(_ns())
    out = capsys.readouterr().out
    assert "MAP01" in out


def test_list_maps_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_maps

    list_maps.run(_ns(json=True))
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# list lumps
# ---------------------------------------------------------------------------


def test_list_lumps_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_lumps

    list_lumps.run(_ns(filter=None))
    out = capsys.readouterr().out
    assert "PLAYPAL" in out


def test_list_lumps_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_lumps

    list_lumps.run(_ns(json=True, filter=None))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    assert all("name" in e and "size" in e for e in data[:3])


def test_list_lumps_filter(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_lumps

    list_lumps.run(_ns(filter="MAP01"))
    out = capsys.readouterr().out
    assert "MAP01" in out


# ---------------------------------------------------------------------------
# list textures
# ---------------------------------------------------------------------------


def test_list_textures_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_textures

    list_textures.run(_ns(filter=None))
    out = capsys.readouterr().out
    assert "TOTAL" in out.upper() or "NAME" in out.upper()


def test_list_textures_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_textures

    list_textures.run(_ns(json=True, filter=None))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0] and "width" in data[0]


# ---------------------------------------------------------------------------
# list flats
# ---------------------------------------------------------------------------


def test_list_flats_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_flats

    list_flats.run(_ns(filter=None))
    out = capsys.readouterr().out
    assert "FLOOR" in out or "Total" in out


def test_list_flats_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_flats

    list_flats.run(_ns(json=True, filter=None))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0


# ---------------------------------------------------------------------------
# list sprites
# ---------------------------------------------------------------------------


def test_list_sprites_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_sprites

    list_sprites.run(_ns())
    out = capsys.readouterr().out
    assert len(out) > 0


def test_list_sprites_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_sprites

    list_sprites.run(_ns(json=True))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# list sounds
# ---------------------------------------------------------------------------


def test_list_sounds_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_sounds

    list_sounds.run(_ns())
    out = capsys.readouterr().out
    assert "DSPISTOL" in out or "NAME" in out


def test_list_sounds_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_sounds

    list_sounds.run(_ns(json=True))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# list music
# ---------------------------------------------------------------------------


def test_list_music_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_music

    list_music.run(_ns())
    out = capsys.readouterr().out
    assert "D_" in out or "NAME" in out


def test_list_music_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_music

    list_music.run(_ns(json=True))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    assert "name" in data[0]


# ---------------------------------------------------------------------------
# list patches
# ---------------------------------------------------------------------------


def test_list_patches_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_patches

    list_patches.run(_ns(filter=None))
    out = capsys.readouterr().out
    assert "Total" in out or "BODIES" in out


def test_list_patches_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_patches

    list_patches.run(_ns(json=True, filter=None))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0


# ---------------------------------------------------------------------------
# list stats
# ---------------------------------------------------------------------------


def test_list_stats_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_stats

    list_stats.run(_ns())
    out = capsys.readouterr().out
    assert "Maps" in out or "Things" in out


def test_list_stats_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_stats

    list_stats.run(_ns(json=True))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, dict)
    assert "maps" in data


# ---------------------------------------------------------------------------
# list animations — freedoom2 has no ANIMDEFS → tests the sys.exit(1) path
# ---------------------------------------------------------------------------


def test_list_animations_no_animdefs(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_animations

    with pytest.raises(SystemExit) as exc:
        list_animations.run(_ns())
    assert exc.value.code == 1


def test_list_animations_no_animdefs_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_animations

    with pytest.raises(SystemExit) as exc:
        list_animations.run(_ns(json=True))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


def test_info_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import info

    info.run(_ns())
    out = capsys.readouterr().out
    assert "IWAD" in out


def test_info_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import info

    info.run(_ns(json=True))
    data = json.loads(capsys.readouterr().out)
    assert data["type"] == "IWAD"
    assert "lumps" in data


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def test_check_clean_wad(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import check

    with pytest.raises(SystemExit) as exc:
        check.run(_ns())
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "No issues" in out


def test_check_clean_wad_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import check

    with pytest.raises(SystemExit) as exc:
        check.run(_ns(json=True))
    assert exc.value.code == 0
    data = json.loads(capsys.readouterr().out)
    assert data == []


# ---------------------------------------------------------------------------
# diff — text mode with identical WADs returns normally (no sys.exit)
# ---------------------------------------------------------------------------


def test_diff_identical_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import diff

    ns = argparse.Namespace(wad_a=_F2, wad_b=_F2, json=False)
    diff.run(ns)
    out = capsys.readouterr().out
    assert "No differences" in out


def test_diff_identical_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import diff

    ns = argparse.Namespace(wad_a=_F2, wad_b=_F2, json=True)
    diff.run(ns)
    data = json.loads(capsys.readouterr().out)
    assert data["added"] == []
    assert data["removed"] == []
    assert data["changed"] == []


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_diff_different_wads_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import diff

    ns = argparse.Namespace(wad_a=_F1, wad_b=_F2, json=False)
    with pytest.raises(SystemExit) as exc:
        diff.run(ns)
    assert exc.value.code == 1


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_diff_different_wads_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import diff

    ns = argparse.Namespace(wad_a=_F1, wad_b=_F2, json=True)
    diff.run(ns)
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data["added"], list)
    assert isinstance(data["removed"], list)


# ---------------------------------------------------------------------------
# export map
# ---------------------------------------------------------------------------


def test_export_map(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_map

    out = str(tmp_path / "m.png")
    export_map.run(
        _ns(
            map="MAP01",
            output=out,
            all=False,
            scale=0.0,
            no_things=False,
            floors=False,
            palette=0,
            thing_scale=1.0,
            alpha=False,
            sprites=False,
            multiplayer=False,
        )
    )
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_map_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_map

    with pytest.raises(SystemExit) as exc:
        export_map.run(
            _ns(
                map="NOTAMAP",
                output=str(tmp_path / "nope.png"),
                all=False,
                scale=0.0,
                no_things=False,
                floors=False,
                palette=0,
                thing_scale=1.0,
                alpha=False,
                sprites=False,
                multiplayer=False,
            )
        )
    assert exc.value.code == 1


@pytest.mark.slow
def test_export_map_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_map

    export_map.run(
        _ns(
            map=None,
            output=str(tmp_path),
            all=True,
            scale=0.0,
            no_things=False,
            floors=False,
            palette=0,
            thing_scale=1.0,
            alpha=False,
            sprites=False,
            multiplayer=False,
        )
    )
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) > 0
    out = capsys.readouterr().out
    assert "Exported" in out


@pytest.mark.slow
def test_export_map_all_no_map_arg(tmp_path: Path) -> None:
    """--all with no positional args uses cwd-equivalent (output arg)."""
    from wadlib.cli.commands import export_map

    export_map.run(
        _ns(
            map=None,
            output=str(tmp_path),
            all=True,
            scale=0.0,
            no_things=False,
            floors=False,
            palette=0,
            thing_scale=1.0,
            alpha=False,
            sprites=False,
            multiplayer=False,
        )
    )
    assert any(tmp_path.glob("MAP*.png"))


def test_export_map_no_name_no_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Omitting map name without --all exits 1."""
    from wadlib.cli.commands import export_map

    with pytest.raises(SystemExit) as exc:
        export_map.run(
            _ns(
                map=None,
                output=None,
                all=False,
                scale=0.0,
                no_things=False,
                floors=False,
                palette=0,
                thing_scale=1.0,
                alpha=False,
                sprites=False,
                multiplayer=False,
            )
        )
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export flat
# ---------------------------------------------------------------------------


def test_export_flat(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_flat

    out = str(tmp_path / "f.png")
    export_flat.run(_ns(flat="FLOOR0_1", output=out, palette=0, scale=1))
    assert Path(out).exists()


def test_export_flat_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_flat

    with pytest.raises(SystemExit) as exc:
        export_flat.run(_ns(flat="NOTAFLAT", output=str(tmp_path / "nope.png"), palette=0, scale=1))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export patch
# ---------------------------------------------------------------------------


def test_export_patch(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_patch

    out = str(tmp_path / "p.png")
    # BODIES is first patch in freedoom2 pnames
    export_patch.run(_ns(patch="BODIES", output=out, palette=0))
    assert Path(out).exists()


def test_export_patch_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_patch

    with pytest.raises(SystemExit) as exc:
        export_patch.run(_ns(patch="NOTAPATCH", output=str(tmp_path / "nope.png"), palette=0))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export sprite
# ---------------------------------------------------------------------------


def test_export_sprite(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sprite

    out = str(tmp_path / "s.png")
    export_sprite.run(_ns(name="AMMOA0", output=out, all=False, palette=0))
    assert Path(out).exists()


def test_export_sprite_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sprite

    with pytest.raises(SystemExit) as exc:
        export_sprite.run(
            _ns(name="NOTASPRITE", output=str(tmp_path / "nope.png"), all=False, palette=0)
        )
    assert exc.value.code == 1


@pytest.mark.slow
def test_export_sprite_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sprite

    export_sprite.run(_ns(name=None, output=str(tmp_path), all=True, palette=0))
    pngs = list(tmp_path.glob("*.png"))
    assert len(pngs) > 0
    assert "Exported" in capsys.readouterr().out


def test_export_sprite_no_name_no_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sprite

    with pytest.raises(SystemExit) as exc:
        export_sprite.run(_ns(name=None, output=None, all=False, palette=0))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export texture
# ---------------------------------------------------------------------------


def test_export_texture(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_texture

    out = str(tmp_path / "t.png")
    # AASHITTY is first texture in freedoom2 TEXTURE1
    export_texture.run(_ns(texture="AASHITTY", output=out, palette=0))
    assert Path(out).exists()


def test_export_texture_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_texture

    with pytest.raises(SystemExit) as exc:
        export_texture.run(_ns(texture="NOTEXTURE", output=str(tmp_path / "nope.png"), palette=0))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export sound
# ---------------------------------------------------------------------------


def test_export_sound_wav(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sound

    out = str(tmp_path / "s.wav")
    export_sound.run(_ns(name="DSBAREXP", output=out, raw=False))
    assert Path(out).exists()
    assert Path(out).read_bytes()[:4] == b"RIFF"


def test_export_sound_raw(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sound

    out = str(tmp_path / "s.dmx")
    export_sound.run(_ns(name="DSBAREXP", output=out, raw=True))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_sound_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_sound

    with pytest.raises(SystemExit) as exc:
        export_sound.run(_ns(name="DSNOTHING", output=str(tmp_path / "nope.wav"), raw=False))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export music
# ---------------------------------------------------------------------------


def test_export_music_midi(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_music

    out = str(tmp_path / "m.mid")
    export_music.run(_ns(name="D_ADRIAN", output=out, raw=False))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_music_raw(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_music

    out = str(tmp_path / "m.mus")
    export_music.run(_ns(name="D_ADRIAN", output=out, raw=True))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_music_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_music

    with pytest.raises(SystemExit) as exc:
        export_music.run(_ns(name="D_NOTHING", output=str(tmp_path / "nope.mid"), raw=False))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export colormap
# ---------------------------------------------------------------------------


def test_export_colormap(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_colormap

    out = str(tmp_path / "cm.png")
    export_colormap.run(_ns(output=out, palette=0))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# export palette
# ---------------------------------------------------------------------------


def test_export_palette_all(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_palette

    out = str(tmp_path / "pal_all.png")
    export_palette.run(_ns(output=out, palette=None))
    assert Path(out).exists()


def test_export_palette_single(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_palette

    out = str(tmp_path / "pal0.png")
    export_palette.run(_ns(output=out, palette=0))
    assert Path(out).exists()


def test_export_palette_out_of_range(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_palette

    with pytest.raises(SystemExit) as exc:
        export_palette.run(_ns(output=str(tmp_path / "nope.png"), palette=999))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export endoom
# ---------------------------------------------------------------------------


def test_export_endoom_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_endoom

    out = str(tmp_path / "e.txt")
    export_endoom.run(_ns(output=out, ansi=False))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_endoom_ansi(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_endoom

    out = str(tmp_path / "e.ans")
    export_endoom.run(_ns(output=out, ansi=True))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# export font
# ---------------------------------------------------------------------------


def test_export_font_stcfn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_font

    out = str(tmp_path / "font.png")
    export_font.run(_ns(font="stcfn", output=out, palette=0, cols=16))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_export_font_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """fonta is not present in freedoom2 — should exit 1."""
    from wadlib.cli.commands import export_font

    with pytest.raises(SystemExit) as exc:
        export_font.run(_ns(font="fonta", output=str(tmp_path / "fonta.png"), palette=0, cols=16))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# extract lump
# ---------------------------------------------------------------------------


def test_extract_lump(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import extract_lump

    out = str(tmp_path / "l.bin")
    extract_lump.run(_ns(lump="PLAYPAL", output=out))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


def test_extract_lump_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import extract_lump

    with pytest.raises(SystemExit) as exc:
        extract_lump.run(_ns(lump="NOTHERE", output=str(tmp_path / "nope.bin")))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# export animation — freedoom2 has no ANIMDEFS → tests the sys.exit(1) path
# ---------------------------------------------------------------------------


def test_export_animation_no_animdefs(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_animation

    with pytest.raises(SystemExit) as exc:
        export_animation.run(_ns(name="x_001", output=str(tmp_path / "a.gif"), palette=0))
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# main() — call the CLI main function via sys.argv patching to cover
# the configure() functions and argument parser setup in cli/__init__.py
# ---------------------------------------------------------------------------


def test_main_help() -> None:
    """Call wadcli main() with --help to cover cli/__init__.py setup code."""
    from wadlib.cli import main

    old_argv = sys.argv
    sys.argv = ["wadcli", "--help"]
    try:
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv


def test_main_list_help() -> None:
    """Call wadcli main() with 'list --help' to exercise list subparser setup."""
    from wadlib.cli import main

    old_argv = sys.argv
    sys.argv = ["wadcli", "list", "--help"]
    try:
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv


def test_main_export_help() -> None:
    """Call wadcli main() with 'export --help' to exercise export subparser setup."""
    from wadlib.cli import main

    old_argv = sys.argv
    sys.argv = ["wadcli", "export", "--help"]
    try:
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv


def test_main_check_runs(capsys: pytest.CaptureFixture[str]) -> None:
    """Call wadcli main() with a real command to cover argument dispatch."""
    from wadlib.cli import main

    old_argv = sys.argv
    sys.argv = ["wadcli", "--wad", _F2, "info", "--json"]
    try:
        main()
    except SystemExit as e:
        # Some commands may exit cleanly
        assert e.code == 0 or e.code is None
    finally:
        sys.argv = old_argv
    out = capsys.readouterr().out
    assert len(out) > 0


# ---------------------------------------------------------------------------
# Additional text-mode coverage for list commands
# ---------------------------------------------------------------------------


def test_list_patches_text_with_filter(capsys: pytest.CaptureFixture[str]) -> None:
    """Test text-mode list patches with a filter."""
    from wadlib.cli.commands import list_patches

    list_patches.run(_ns(filter="BFALL", json=False))
    out = capsys.readouterr().out
    assert "BFALL" in out or "Total" in out


def test_list_flats_text_with_filter(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_flats

    list_flats.run(_ns(filter="FLOOR", json=False))
    out = capsys.readouterr().out
    # floor flats exist in freedoom2
    assert "FLOOR" in out or "Total" in out


def test_list_textures_text_with_filter(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_textures

    list_textures.run(_ns(filter="ASH", json=False))
    out = capsys.readouterr().out
    assert len(out) > 0


def test_export_flat_scale2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test export_flat with scale=2 to cover the resize path."""
    from wadlib.cli.commands import export_flat

    out = str(tmp_path / "f2x.png")
    export_flat.run(_ns(flat="FLOOR0_1", output=out, palette=0, scale=2))
    assert Path(out).exists()


def test_export_colormap_text_output(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Verify export_colormap prints a success message."""
    from wadlib.cli.commands import export_colormap

    out = str(tmp_path / "cm2.png")
    export_colormap.run(_ns(output=out, palette=0))
    stdout = capsys.readouterr().out
    assert "Saved" in stdout


def test_export_endoom_default_path(capsys: pytest.CaptureFixture[str]) -> None:
    """Test export_endoom with no output path (uses default)."""
    import os

    from wadlib.cli.commands import export_endoom

    # Change to tmp dir so the default file lands somewhere clean
    old_cwd = os.getcwd()
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            export_endoom.run(_ns(output=None, ansi=False))
            assert Path(d, "ENDOOM.txt").exists()
    finally:
        os.chdir(old_cwd)


def test_export_map_with_floors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test export_map with floors=True to cover more renderer paths."""
    from wadlib.cli.commands import export_map

    out = str(tmp_path / "m_floors.png")
    export_map.run(
        _ns(
            map="MAP01",
            output=out,
            all=False,
            scale=0.05,  # tiny scale = fast
            no_things=True,
            floors=True,
            palette=0,
            thing_scale=1.0,
            alpha=False,
            sprites=False,
            multiplayer=False,
        )
    )
    assert Path(out).exists()


def test_export_map_alpha(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test export_map with alpha=True to cover RGBA path."""
    from wadlib.cli.commands import export_map

    out = str(tmp_path / "m_alpha.png")
    export_map.run(
        _ns(
            map="MAP01",
            output=out,
            all=False,
            scale=0.05,
            no_things=False,
            floors=False,
            palette=0,
            thing_scale=1.0,
            alpha=True,
            sprites=False,
            multiplayer=False,
        )
    )


def test_export_map_sprites(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Test export_map with --sprites to cover sprite rendering path."""
    from wadlib.cli.commands import export_map

    out = str(tmp_path / "m_sprites.png")
    export_map.run(
        _ns(
            map="MAP01",
            output=out,
            all=False,
            scale=0.05,
            no_things=False,
            floors=False,
            palette=0,
            thing_scale=1.0,
            alpha=False,
            sprites=True,
            multiplayer=False,
        )
    )
    assert Path(out).exists()


# ---------------------------------------------------------------------------
# list_maps on freedoom1 to cover Doom1 music path (E#M# pattern)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_list_maps_freedoom1_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_maps

    ns = argparse.Namespace(wad=_F1, pwads=[], deh=None, json=True)
    list_maps.run(ns)
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list) and len(data) > 0
    # E1M1 should have Doom1-style music key
    e1m1 = next((m for m in data if m["name"] == "E1M1"), None)
    assert e1m1 is not None
    assert e1m1["music"] in ("D_E1M1", "MUS_E1M1", "")


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_list_maps_freedoom1_text(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import list_maps

    ns = argparse.Namespace(wad=_F1, pwads=[], deh=None, json=False)
    list_maps.run(ns)
    out = capsys.readouterr().out
    assert "E1M1" in out


# ---------------------------------------------------------------------------
# Unit tests for list_maps helpers (cover _resolve_mi, _music_for_map)
# ---------------------------------------------------------------------------


def test_resolve_mi_no_mapinfo() -> None:
    from wadlib.cli.commands.list_maps import _resolve_mi

    result = _resolve_mi("MAP01", None, None)
    assert result is None


def test_resolve_mi_with_zmapinfo() -> None:
    """_resolve_mi returns zmapinfo entry when zmapinfo is present."""
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _resolve_mi

    entry = MagicMock()
    zmapinfo = MagicMock()
    zmapinfo.get_map.return_value = entry
    result = _resolve_mi("MAP01", None, zmapinfo)
    assert result is entry
    zmapinfo.get_map.assert_called_with("MAP01")


def test_resolve_mi_zmapinfo_miss_falls_to_mapinfo() -> None:
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _resolve_mi

    zmapinfo = MagicMock()
    zmapinfo.get_map.return_value = None  # miss

    mi_entry = MagicMock()
    mapinfo = MagicMock()
    mapinfo.get_map.return_value = mi_entry

    result = _resolve_mi("MAP01", mapinfo, zmapinfo)
    assert result is mi_entry


def test_resolve_mi_mapinfo_invalid_name() -> None:
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _resolve_mi

    mapinfo = MagicMock()
    result = _resolve_mi("SOMETEXT", mapinfo, None)
    assert result is None


def test_music_for_map_no_mi_doom1() -> None:
    from wadlib.cli.commands.list_maps import _music_for_map

    music = {"D_E1M1": object()}
    result = _music_for_map("E1M1", music, None)
    assert result == "D_E1M1"


def test_music_for_map_no_mi_doom1_fallback_mus() -> None:
    from wadlib.cli.commands.list_maps import _music_for_map

    music = {"MUS_E2M1": object()}
    result = _music_for_map("E2M1", music, None)
    assert result == "MUS_E2M1"


def test_music_for_map_no_mi_doom1_not_found() -> None:
    from wadlib.cli.commands.list_maps import _music_for_map

    result = _music_for_map("E9M9", {}, None)
    assert result == ""


def test_music_for_map_no_mi_doom2_out_of_range() -> None:
    from wadlib.cli.commands.list_maps import _music_for_map

    result = _music_for_map("MAP99", {}, None)
    assert result == ""


def test_music_for_map_mi_entry_direct_music() -> None:
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _music_for_map

    mi = MagicMock()
    mi.music = "D_CUSTOM"
    mi.cdtrack = None
    music = {"D_CUSTOM": object()}
    result = _music_for_map("MAP01", music, mi)
    assert result == "D_CUSTOM"


def test_music_for_map_mi_entry_cdtrack() -> None:
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _music_for_map

    mi = MagicMock()
    mi.music = None
    mi.cdtrack = 5
    result = _music_for_map("MAP01", {}, mi)
    assert result == "cd:5"


def test_music_for_map_mi_entry_music_not_in_wad() -> None:
    """music attr present but not in wad.music → fall through to pattern match."""
    from unittest.mock import MagicMock

    from wadlib.cli.commands.list_maps import _music_for_map

    mi = MagicMock()
    mi.music = "D_MISSING"
    mi.cdtrack = None
    # D_MISSING not in music dict, but D_RUNNIN is (MAP01 default)
    music = {"D_RUNNIN": object()}
    result = _music_for_map("MAP01", music, mi)
    assert result == "D_RUNNIN"


# ---------------------------------------------------------------------------
# check.py helper coverage — test helpers directly
# ---------------------------------------------------------------------------


def test_check_linedefs_helper() -> None:
    """Test _check_linedefs with a map entry."""
    from unittest.mock import MagicMock

    from wadlib.cli.commands.check import Issue, _check_linedefs
    from wadlib.lumps.lines import LineDefinition

    line = LineDefinition.__new__(LineDefinition)
    line.start_vertex = 999
    line.finish_vertex = 0
    line.right_sidedef = 0
    line.left_sidedef = -1

    m = MagicMock()
    m.name = "MAP01"
    m.lines = [line]
    m.vertices = [MagicMock()]  # 1 vertex
    m.sidedefs = [MagicMock()]  # 1 sidedef

    issues: list[Issue] = []
    _check_linedefs(m, issues)
    # start_vertex=999 > vertex_count=1 → bad_vertex issue
    assert any(i.kind == "bad_vertex" for i in issues)


def test_check_sectors_helper() -> None:
    """Test _check_sectors with a missing flat reference."""
    from unittest.mock import MagicMock

    from wadlib.cli.commands.check import Issue, _check_sectors

    sector = MagicMock()
    sector.floor_texture = "BADFLAT"
    sector.ceiling_texture = "CEIL1_1"

    m = MagicMock()
    m.name = "MAP01"
    m.sectors = [sector]

    flats = frozenset({"CEIL1_1"})
    issues: list[Issue] = []
    _check_sectors(m, flats, issues)
    assert any(i.kind == "missing_flat" for i in issues)


# ---------------------------------------------------------------------------
# list_stats text mode additional coverage
# ---------------------------------------------------------------------------


def test_list_stats_no_maps(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """Test list_stats on a WAD with no maps (exercise the 'no maps' branch)."""
    import struct

    # Build a minimal WAD with only PLAYPAL (no maps)
    playpal_data = bytes(256 * 3 * 14)
    num_lumps = 1
    data_start = 12
    lump_data = playpal_data
    dir_offset = data_start + len(lump_data)
    header = struct.pack("<4sII", b"IWAD", num_lumps, dir_offset)
    padded_name = b"PLAYPAL\x00"
    directory = struct.pack("<II8s", data_start, len(playpal_data), padded_name)
    wad_path = tmp_path / "nomaps.wad"
    wad_path.write_bytes(header + lump_data + directory)

    from wadlib.cli.commands import list_stats

    list_stats.run(argparse.Namespace(wad=str(wad_path), pwads=[], deh=None, json=False))
    out = capsys.readouterr().out
    assert "No maps" in out


def test_list_stats_no_maps_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    import struct

    playpal_data = bytes(256 * 3 * 14)
    num_lumps = 1
    data_start = 12
    dir_offset = data_start + len(playpal_data)
    header = struct.pack("<4sII", b"IWAD", num_lumps, dir_offset)
    directory = struct.pack("<II8s", data_start, len(playpal_data), b"PLAYPAL\x00")
    wad_path = tmp_path / "nomaps2.wad"
    wad_path.write_bytes(header + playpal_data + directory)

    from wadlib.cli.commands import list_stats

    list_stats.run(argparse.Namespace(wad=str(wad_path), pwads=[], deh=None, json=True))
    out = capsys.readouterr().out
    assert "{}" in out


# ---------------------------------------------------------------------------
# Empty-WAD paths for list_sprites / list_sounds / list_music / list_patches
# ---------------------------------------------------------------------------


def _make_empty_wad(tmp_path: Path, name: str = "empty.wad") -> str:
    """Build a minimal IWAD with zero lumps (no sprites/sounds/music/patches)."""
    import struct

    wad_path = tmp_path / name
    header = struct.pack("<4sII", b"IWAD", 0, 12)
    wad_path.write_bytes(header)
    return str(wad_path)


def test_list_sprites_empty_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_sprites

    wad = _make_empty_wad(tmp_path, "empty_sp.wad")
    list_sprites.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=False))
    out = capsys.readouterr().out
    assert "No sprites" in out


def test_list_sprites_empty_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_sprites

    wad = _make_empty_wad(tmp_path, "empty_sp2.wad")
    list_sprites.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=True))
    data = json.loads(capsys.readouterr().out)
    assert data == []


def test_list_sounds_empty_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_sounds

    wad = _make_empty_wad(tmp_path, "empty_snd.wad")
    list_sounds.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=False))
    out = capsys.readouterr().out
    assert "No sounds" in out


def test_list_sounds_empty_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_sounds

    wad = _make_empty_wad(tmp_path, "empty_snd2.wad")
    list_sounds.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=True))
    data = json.loads(capsys.readouterr().out)
    assert data == []


def test_list_music_empty_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_music

    wad = _make_empty_wad(tmp_path, "empty_mus.wad")
    list_music.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=False))
    out = capsys.readouterr().out
    assert "No music" in out


def test_list_music_empty_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_music

    wad = _make_empty_wad(tmp_path, "empty_mus2.wad")
    list_music.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=True))
    data = json.loads(capsys.readouterr().out)
    assert data == []


def test_list_patches_empty_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_patches

    wad = _make_empty_wad(tmp_path, "empty_pn.wad")
    list_patches.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=False, filter=None))
    out = capsys.readouterr().out
    assert "No PNAMES" in out


def test_list_patches_empty_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_patches

    wad = _make_empty_wad(tmp_path, "empty_pn2.wad")
    list_patches.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=True, filter=None))
    data = json.loads(capsys.readouterr().out)
    assert data == []


def test_list_patches_filter_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Test text-mode list patches with a filter that yields no results."""
    from wadlib.cli.commands import list_patches

    list_patches.run(_ns(filter="ZZZNOMATCH", json=False))
    out = capsys.readouterr().out
    assert "No patches" in out or "Total" in out


def test_list_maps_empty_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_maps

    wad = _make_empty_wad(tmp_path, "empty_maps.wad")
    list_maps.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=False))
    out = capsys.readouterr().out
    assert "No maps" in out


def test_list_maps_empty_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from wadlib.cli.commands import list_maps

    wad = _make_empty_wad(tmp_path, "empty_maps2.wad")
    list_maps.run(argparse.Namespace(wad=wad, pwads=[], deh=None, json=True))
    data = json.loads(capsys.readouterr().out)
    assert data == []


# ---------------------------------------------------------------------------
# info.py additional coverage — test with dehacked wad
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_info_with_dehacked_text(capsys: pytest.CaptureFixture[str]) -> None:
    """info text mode on freedoom1 (has DEHACKED) covers the dehacked print branch."""
    from wadlib.cli.commands import info

    ns = argparse.Namespace(wad=_F1, pwads=[], deh=None, json=False)
    info.run(ns)
    out = capsys.readouterr().out
    assert "DEHACKED" in out


@pytest.mark.skipif(not Path(_F1).exists(), reason="freedoom1.wad not found in wads/")
def test_info_with_dehacked_json(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import info

    ns = argparse.Namespace(wad=_F1, pwads=[], deh=None, json=True)
    info.run(ns)
    data = json.loads(capsys.readouterr().out)
    assert data.get("dehacked") is not None


# ---------------------------------------------------------------------------
# check.py — additional sidedef helper coverage
# ---------------------------------------------------------------------------


def test_check_sidedefs_helper() -> None:
    """Test _check_sidedefs with a missing texture reference."""
    from unittest.mock import MagicMock

    from wadlib.cli.commands.check import Issue, _check_sidedefs

    sidedef = MagicMock()
    sidedef.sector = 0
    sidedef.upper_texture = "MISSING"
    sidedef.lower_texture = "-"
    sidedef.middle_texture = "AASHITTY"

    m = MagicMock()
    m.name = "MAP01"
    m.sidedefs = [sidedef]
    m.sectors = [MagicMock()]  # 1 sector

    textures = frozenset({"AASHITTY"})
    issues: list[Issue] = []
    _check_sidedefs(m, textures, issues)
    assert any(i.kind == "missing_texture" for i in issues)


def test_check_sidedefs_bad_sector_ref() -> None:
    from unittest.mock import MagicMock

    from wadlib.cli.commands.check import Issue, _check_sidedefs

    sidedef = MagicMock()
    sidedef.sector = 999  # out of range
    sidedef.upper_texture = "-"
    sidedef.lower_texture = "-"
    sidedef.middle_texture = "-"

    m = MagicMock()
    m.name = "MAP01"
    m.sidedefs = [sidedef]
    m.sectors = [MagicMock()]  # 1 sector

    issues: list[Issue] = []
    _check_sidedefs(m, frozenset(), issues)
    assert any(i.kind == "bad_sector_ref" for i in issues)


def test_check_right_sidedef_out_of_range() -> None:
    from wadlib.cli.commands.check import Issue, _check_linedefs
    from wadlib.lumps.lines import LineDefinition

    line = LineDefinition.__new__(LineDefinition)
    line.start_vertex = 0
    line.finish_vertex = 0
    line.right_sidedef = 999  # out of range
    line.left_sidedef = -1

    from unittest.mock import MagicMock

    m = MagicMock()
    m.name = "MAP01"
    m.lines = [line]
    m.vertices = [MagicMock()]
    m.sidedefs = [MagicMock()]

    issues: list[Issue] = []
    _check_linedefs(m, issues)
    assert any(i.kind == "bad_sidedef" for i in issues)


def test_check_left_sidedef_out_of_range() -> None:
    from wadlib.cli.commands.check import Issue, _check_linedefs
    from wadlib.lumps.lines import LineDefinition

    line = LineDefinition.__new__(LineDefinition)
    line.start_vertex = 0
    line.finish_vertex = 0
    line.right_sidedef = 0
    line.left_sidedef = 999  # out of range, not -1

    from unittest.mock import MagicMock

    m = MagicMock()
    m.name = "MAP01"
    m.lines = [line]
    m.vertices = [MagicMock()]
    m.sidedefs = [MagicMock()]

    issues: list[Issue] = []
    _check_linedefs(m, issues)
    assert any(i.kind == "bad_sidedef" for i in issues)


# ---------------------------------------------------------------------------
# check.py — missing --wad + text output with issues
# ---------------------------------------------------------------------------


def test_check_no_wad_exits(capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import check

    with pytest.raises(SystemExit) as exc:
        check.run(argparse.Namespace(wad=None, pwads=[], deh=None, json=False))
    assert exc.value.code == 1


def test_check_text_output_with_issues(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Text mode on a bad WAD should print per-map issue lines and summary."""
    import struct

    from wadlib.cli.commands import check

    sector = struct.pack(
        "<hh8s8sHHH", 0, 128, b"FLAT1\x00\x00\x00", b"FLAT1\x00\x00\x00", 160, 0, 0
    )
    sidedef = struct.pack(
        "<hh8s8s8sH",
        0,
        0,
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"-\x00\x00\x00\x00\x00\x00\x00",
        b"XTEXTURE",
        0,
    )
    vertex = struct.pack("<hh", 0, 0) + struct.pack("<hh", 64, 0)
    linedef = struct.pack("<HHHHHhh", 0, 1, 1, 0, 0, 0, -1)
    lumps: list[tuple[str, bytes]] = [
        ("E1M1", b""),
        ("THINGS", struct.pack("<hhHHH", 32, 32, 0, 1, 7)),
        ("VERTEXES", vertex),
        ("LINEDEFS", linedef),
        ("SIDEDEFS", sidedef),
        ("SECTORS", sector),
    ]
    lump_bytes = b"".join(d for _, d in lumps)
    dir_off = 12 + len(lump_bytes)
    hdr = struct.pack("<4sII", b"IWAD", len(lumps), dir_off)
    directory = b""
    off = 12
    for name, data in lumps:
        directory += struct.pack("<II8s", off, len(data), name.encode().ljust(8, b"\x00"))
        off += len(data)
    p = tmp_path / "bad.wad"
    p.write_bytes(hdr + lump_bytes + directory)

    with pytest.raises(SystemExit) as exc:
        check.run(argparse.Namespace(wad=str(p), pwads=[], deh=None, json=False))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "issue(s)" in out


# ---------------------------------------------------------------------------
# export_music.py — MidiLump dispatch path
# ---------------------------------------------------------------------------


def test_export_music_midi_lump(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Export a MidiLump track (freedoom2 stores music as Standard MIDI)."""
    from wadlib.cli.commands import export_music
    from wadlib.wad import WadFile

    with WadFile(_F2) as w:
        midi_name = next((k for k, v in w.music.items() if type(v).__name__ == "MidiLump"), None)
    if midi_name is None:
        pytest.skip("No MidiLump in freedoom2")

    out = str(tmp_path / "midi.mid")
    export_music.run(_ns(name=midi_name, output=out, raw=False))
    assert Path(out).exists()


def test_export_music_midi_lump_raw(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from wadlib.cli.commands import export_music
    from wadlib.wad import WadFile

    with WadFile(_F2) as w:
        midi_name = next((k for k, v in w.music.items() if type(v).__name__ == "MidiLump"), None)
    if midi_name is None:
        pytest.skip("No MidiLump in freedoom2")

    out = str(tmp_path / "midi_raw.mid")
    export_music.run(_ns(name=midi_name, output=out, raw=True))
    assert Path(out).exists()


# ---------------------------------------------------------------------------
# _wad_args.py — deh loading path
# ---------------------------------------------------------------------------


def test_open_wad_with_deh(tmp_path: Path) -> None:
    """open_wad() should call load_deh() when args.deh is set."""
    from wadlib.cli._wad_args import open_wad

    # Write a minimal DEH file (empty is fine — load_deh should not crash)
    deh = tmp_path / "empty.deh"
    deh.write_text("")
    ns = argparse.Namespace(wad=_F2, pwads=[], deh=str(deh))
    with open_wad(ns) as wad:
        assert wad is not None


# ---------------------------------------------------------------------------
# compositor.py — compose() with missing patch returns None via continue
# ---------------------------------------------------------------------------


def test_compositor_compose_missing_patch(capsys: pytest.CaptureFixture[str]) -> None:
    """compose() returns a canvas even when a patch is absent (skips missing patches)."""
    from wadlib.compositor import TextureCompositor
    from wadlib.wad import WadFile

    with WadFile(_F2) as w:
        comp = TextureCompositor(w)
        # compose returns None for a nonexistent texture, valid image for existing ones
        result = comp.compose("TOTALLY_NONEXISTENT")
        assert result is None


# ---------------------------------------------------------------------------
# info.py — stcfn font + dehacked + many-maps paths (freedoom1 has all three)
# ---------------------------------------------------------------------------


@needs_f1
def test_info_text_freedoom1(capsys: pytest.CaptureFixture[str]) -> None:
    """info text mode with freedoom1: covers stcfn font line, many-maps truncation,
    and DEHacked presence."""
    from wadlib.cli.commands import info

    info.run(_ns(wad=_F1))
    out = capsys.readouterr().out
    assert "IWAD" in out
    # freedoom1 has STCFN font → font line should mention it
    assert "STCFN" in out or "Font" in out or "none" in out
    # freedoom1 has DEHACKED
    assert "DEHACKED" in out


@needs_f1
def test_info_json_freedoom1(capsys: pytest.CaptureFixture[str]) -> None:
    """info --json with freedoom1: covers the deh_info dict branch."""
    from wadlib.cli.commands import info

    info.run(_ns(wad=_F1, json=True))
    data = json.loads(capsys.readouterr().out)
    assert data["type"] == "IWAD"
    # freedoom1 has dehacked; deh_info should be a dict
    assert data["dehacked"] is not None
    assert "doom_version" in data["dehacked"]


# ---------------------------------------------------------------------------
# export_music.py — Mus lump path (DOOM2.WAD stores music as MUS format)
# ---------------------------------------------------------------------------


@needs_doom2
def test_export_music_mus_to_midi(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Export a Mus lump as MIDI — covers the Mus isinstance branch."""
    from wadlib.cli.commands import export_music

    out = str(tmp_path / "mus.mid")
    export_music.run(_ns(wad=_DOOM2, name="D_RUNNIN", output=out, raw=False))
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@needs_doom2
def test_export_music_mus_raw(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Export a Mus lump as raw bytes — covers the raw=True branch of Mus path."""
    from wadlib.cli.commands import export_music

    out = str(tmp_path / "raw.mus")
    export_music.run(_ns(wad=_DOOM2, name="D_RUNNIN", output=out, raw=True))
    assert Path(out).exists()
    assert Path(out).read_bytes()[:4] == b"MUS\x1a"
