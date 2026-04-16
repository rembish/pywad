"""Tests for CLI commands that previously had low coverage.

Commands covered here:
  complevel, convert, export_animation, export_obj, list_actors,
  list_language, list_mapinfo, list_scripts, list_sndseq, scan_textures.

All tests that need a real licensed IWAD are individually marked
``@pytest.mark.slow`` and skip when that WAD is absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from wadlib.archive import WadArchive

_WADS = Path(__file__).parent.parent / "wads"
_F2 = str(_WADS / "freedoom2.wad")
_F1 = str(_WADS / "freedoom1.wad")
_HEXEN = str(_WADS / "HEXEN.WAD")

_has_f2 = pytest.mark.skipif(not (_WADS / "freedoom2.wad").exists(), reason="freedoom2.wad absent")
_has_f1 = pytest.mark.skipif(not (_WADS / "freedoom1.wad").exists(), reason="freedoom1.wad absent")
_has_hexen = pytest.mark.skipif(not (_WADS / "HEXEN.WAD").exists(), reason="HEXEN.WAD absent")


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "wad": _F2,
        "pwads": [],
        "deh": None,
        "json": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _make_minimal_wad(lumps: list[tuple[str, bytes]], *, tmp_path: Path) -> str:
    """Write a minimal PWAD from (name, data) pairs and return its path."""
    path = str(tmp_path / "test.wad")
    with WadArchive(path, "w") as wad:
        for name, data in lumps:
            wad.writestr(name, data, validate=False)
    return path


# ---------------------------------------------------------------------------
# complevel
# ---------------------------------------------------------------------------


@_has_f2
class TestComplevel:
    def test_text_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        complevel.run(_ns(check=None))
        out = capsys.readouterr().out
        assert "Compatibility level" in out or "vanilla" in out.lower()

    def test_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        complevel.run(_ns(json=True, check=None))
        data = json.loads(capsys.readouterr().out)
        assert "level" in data
        assert "features" in data
        assert isinstance(data["features"], list)

    def test_check_flag_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        complevel.run(_ns(check="boom"))
        out = capsys.readouterr().out
        assert "compatible" in out.lower() or "boom" in out.lower()

    def test_check_flag_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        complevel.run(_ns(json=True, check="boom"))
        data = json.loads(capsys.readouterr().out)
        assert "current" in data
        assert "target" in data
        assert "compatible" in data
        assert "issues" in data

    def test_invalid_level_exits(self) -> None:
        from wadlib.cli.commands import complevel

        with pytest.raises(SystemExit):
            complevel.run(_ns(check="notareal"))

    def test_check_vanilla_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        # Freedoom2 is not vanilla — either compatible or not, never crashes.
        complevel.run(_ns(check="vanilla"))
        out = capsys.readouterr().out
        assert out.strip()

    def test_check_udmf_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import complevel

        complevel.run(_ns(json=True, check="udmf"))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data["compatible"], bool)


# ---------------------------------------------------------------------------
# convert — pk3 / wad / complevel subcommands
# ---------------------------------------------------------------------------


@_has_f2
class TestConvert:
    def test_wad_to_pk3(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import convert

        out_pk3 = str(tmp_path / "out.pk3")
        convert.run_pk3(_ns(output=out_pk3))
        stdout = capsys.readouterr().out
        assert "→" in stdout
        assert Path(out_pk3).exists()

    def test_pk3_to_wad(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import convert
        from wadlib.pk3 import wad_to_pk3

        pk3_path = str(tmp_path / "tmp.pk3")
        wad_to_pk3(_F2, pk3_path)
        out_wad = str(tmp_path / "out.wad")
        convert.run_wad(_ns(pk3=pk3_path, output=out_wad))
        stdout = capsys.readouterr().out
        assert "→" in stdout
        assert Path(out_wad).exists()

    def test_wad_to_pk3_no_wad_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import convert

        with pytest.raises(SystemExit) as exc:
            convert.run_pk3(argparse.Namespace(wad=None, output=None))
        assert exc.value.code == 1

    def test_convert_complevel_no_wad_exits(self) -> None:
        from wadlib.cli.commands import convert

        with pytest.raises(SystemExit) as exc:
            convert.run_complevel(argparse.Namespace(wad=None, level="vanilla", output=None))
        assert exc.value.code == 1

    def test_convert_complevel_invalid_level_exits(self) -> None:
        from wadlib.cli.commands import convert

        with pytest.raises(SystemExit) as exc:
            convert.run_complevel(_ns(level="notareal", output=None))
        assert exc.value.code == 1

    def test_convert_complevel_to_boom(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from wadlib.cli.commands import convert

        out_wad = str(tmp_path / "out_boom.wad")
        convert.run_complevel(_ns(level="boom", output=out_wad))
        stdout = capsys.readouterr().out
        assert "→" in stdout
        assert Path(out_wad).exists()


# ---------------------------------------------------------------------------
# export_animation
# ---------------------------------------------------------------------------


@_has_f2
class TestExportAnimation:
    def test_no_animdefs_exits(self, tmp_path: Path) -> None:
        from wadlib.cli.commands import export_animation

        with pytest.raises(SystemExit) as exc:
            export_animation.run(_ns(name="x_001", output=str(tmp_path / "a.gif"), palette=0))
        assert exc.value.code == 1


@_has_hexen
@pytest.mark.slow
class TestExportAnimationHexen:
    def test_animation_name_not_found(self, tmp_path: Path) -> None:
        from wadlib.cli.commands import export_animation

        with pytest.raises(SystemExit) as exc:
            export_animation.run(
                _ns(wad=_HEXEN, name="NOTEXIST", output=str(tmp_path / "a.gif"), palette=0)
            )
        assert exc.value.code == 1

    def test_flat_animation_exported(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from wadlib.cli.commands import export_animation

        out = str(tmp_path / "anim.gif")
        export_animation.run(_ns(wad=_HEXEN, name="x_001", output=out, palette=0))
        stdout = capsys.readouterr().out
        assert "GIF" in stdout
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0


# ---------------------------------------------------------------------------
# export_obj
# ---------------------------------------------------------------------------


@_has_f2
class TestExportObj:
    def test_map_not_found_exits(self, tmp_path: Path) -> None:
        from wadlib.cli.commands import export_obj

        with pytest.raises(SystemExit) as exc:
            export_obj.run(
                _ns(map="NOTEXIST", output=str(tmp_path / "x.obj"), scale=0.01, materials=False)
            )
        assert exc.value.code == 1

    @pytest.mark.slow
    def test_basic_obj_export(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import export_obj

        out = str(tmp_path / "map01.obj")
        export_obj.run(_ns(map="MAP01", output=out, scale=0.01, materials=False))
        stdout = capsys.readouterr().out
        assert "MAP01" in stdout
        assert Path(out).exists()
        assert Path(out).stat().st_size > 0

    @pytest.mark.slow
    def test_obj_with_materials(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import export_obj

        out = str(tmp_path / "map01.obj")
        export_obj.run(_ns(map="MAP01", output=out, scale=0.01, materials=True))
        stdout = capsys.readouterr().out
        assert "MAP01" in stdout
        mtl = str(tmp_path / "map01.mtl")
        assert Path(mtl).exists()


# ---------------------------------------------------------------------------
# list_actors
# ---------------------------------------------------------------------------


class TestListActors:
    def test_no_decorate_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_actors

        list_actors.run(_ns())
        out = capsys.readouterr().out
        assert "No DECORATE" in out

    def test_no_decorate_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_actors

        list_actors.run(_ns(json=True))
        data = json.loads(capsys.readouterr().out)
        assert data == []

    def test_with_decorate_text(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_actors

        decorate = b"Actor MyMonster : Actor 1234\n{\n  Health 100\n  Monster\n  States { Spawn: TROO A -1 loop }\n}\n"
        wad_path = _make_minimal_wad([("DECORATE", decorate)], tmp_path=tmp_path)
        list_actors.run(_ns(wad=wad_path))
        out = capsys.readouterr().out
        assert "MyMonster" in out

    def test_with_decorate_json(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_actors

        decorate = b"Actor MyItem : Actor 2000\n{\n  Item\n  States { Pickup: TNT1 A 1 loop }\n}\n"
        wad_path = _make_minimal_wad([("DECORATE", decorate)], tmp_path=tmp_path)
        list_actors.run(_ns(wad=wad_path, json=True))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(a["name"] == "MyItem" for a in data)


# ---------------------------------------------------------------------------
# list_language
# ---------------------------------------------------------------------------


class TestListLanguage:
    def test_no_language_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_language

        list_language.run(_ns(locale=None, locales=False))
        assert "No LANGUAGE" in capsys.readouterr().out

    def test_no_language_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_language

        list_language.run(_ns(json=True, locale=None, locales=False))
        assert capsys.readouterr().out.strip() == "{}"

    def test_no_language_locales_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_language

        list_language.run(_ns(json=True, locale=None, locales=True))
        assert capsys.readouterr().out.strip() == "[]"

    def test_with_language_text(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_language

        lang = b'[enu]\nTITLE = "My WAD"\nCREDITS = "Test Author"\n'
        wad_path = _make_minimal_wad([("LANGUAGE", lang)], tmp_path=tmp_path)
        list_language.run(_ns(wad=wad_path, locale=None, locales=False))
        out = capsys.readouterr().out
        assert "TITLE" in out or "title" in out.lower() or "My WAD" in out

    def test_with_language_locales_text(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from wadlib.cli.commands import list_language

        lang = b'[enu]\nTITLE = "My WAD"\n[fra]\nTITLE = "Mon WAD"\n'
        wad_path = _make_minimal_wad([("LANGUAGE", lang)], tmp_path=tmp_path)
        list_language.run(_ns(wad=wad_path, locale=None, locales=True))
        out = capsys.readouterr().out
        assert out.strip()

    def test_with_language_locales_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from wadlib.cli.commands import list_language

        lang = b'[enu]\nTITLE = "My WAD"\n'
        wad_path = _make_minimal_wad([("LANGUAGE", lang)], tmp_path=tmp_path)
        list_language.run(_ns(wad=wad_path, json=True, locale=None, locales=True))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)

    def test_with_language_specific_locale(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from wadlib.cli.commands import list_language

        lang = b'[enu]\nTITLE = "My WAD"\n[fra]\nTITLE = "Mon WAD"\n'
        wad_path = _make_minimal_wad([("LANGUAGE", lang)], tmp_path=tmp_path)
        list_language.run(_ns(wad=wad_path, locale="fra", locales=False))
        out = capsys.readouterr().out
        # Either found French strings or reported none for locale
        assert out.strip()


# ---------------------------------------------------------------------------
# list_mapinfo
# ---------------------------------------------------------------------------


class TestListMapinfo:
    def test_no_mapinfo_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_mapinfo

        list_mapinfo.run(_ns())
        assert "No MAPINFO" in capsys.readouterr().out

    def test_no_mapinfo_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_mapinfo

        list_mapinfo.run(_ns(json=True))
        assert capsys.readouterr().out.strip() == "[]"


@_has_hexen
@pytest.mark.slow
class TestListMapinfoHexen:
    def test_mapinfo_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_mapinfo

        list_mapinfo.run(_ns(wad=_HEXEN))
        out = capsys.readouterr().out
        assert "MAPINFO" in out or "map" in out.lower()

    def test_mapinfo_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_mapinfo

        list_mapinfo.run(_ns(wad=_HEXEN, json=True))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "title" in data[0] or "map_name" in data[0] or "map_num" in data[0]


# ---------------------------------------------------------------------------
# list_scripts
# ---------------------------------------------------------------------------


class TestListScripts:
    def test_no_scripts_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_scripts

        list_scripts.run(_ns())
        assert "No ACS" in capsys.readouterr().out

    def test_no_scripts_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_scripts

        list_scripts.run(_ns(json=True))
        data = json.loads(capsys.readouterr().out)
        assert data == []


@_has_hexen
@pytest.mark.slow
class TestListScriptsHexen:
    def test_scripts_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_scripts

        list_scripts.run(_ns(wad=_HEXEN))
        out = capsys.readouterr().out
        assert "MAP" in out
        assert "script" in out.lower() or "#" in out

    def test_scripts_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_scripts

        list_scripts.run(_ns(wad=_HEXEN, json=True))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0
        first = data[0]
        assert "map" in first and "number" in first and "type" in first and "args" in first


# ---------------------------------------------------------------------------
# list_sndseq
# ---------------------------------------------------------------------------


class TestListSndseq:
    def test_no_sndseq_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_sndseq

        list_sndseq.run(_ns(detail=False))
        assert "No SNDSEQ" in capsys.readouterr().out

    def test_no_sndseq_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_sndseq

        list_sndseq.run(_ns(json=True, detail=False))
        assert capsys.readouterr().out.strip() == "[]"


@_has_hexen
@pytest.mark.slow
class TestListSndseqHexen:
    def test_sndseq_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_sndseq

        list_sndseq.run(_ns(wad=_HEXEN, detail=False))
        out = capsys.readouterr().out
        assert "sequence" in out.lower() or "Name" in out

    def test_sndseq_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_sndseq

        list_sndseq.run(_ns(wad=_HEXEN, json=True, detail=False))
        data = json.loads(capsys.readouterr().out)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0] and "commands" in data[0]

    def test_sndseq_detail(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import list_sndseq

        list_sndseq.run(_ns(wad=_HEXEN, detail=True))
        out = capsys.readouterr().out
        assert "end" in out.lower()


# ---------------------------------------------------------------------------
# scan_textures
# ---------------------------------------------------------------------------


@_has_f2
class TestScanTextures:
    def test_text_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import scan_textures

        scan_textures.run(_ns(unused=False))
        out = capsys.readouterr().out
        assert "Textures" in out or "textures" in out.lower()

    def test_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import scan_textures

        scan_textures.run(_ns(json=True, unused=False))
        data = json.loads(capsys.readouterr().out)
        assert "total_textures" in data
        assert "maps" in data
        assert isinstance(data["maps"], dict)

    def test_unused_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import scan_textures

        scan_textures.run(_ns(unused=True))
        out = capsys.readouterr().out
        assert "unused" in out.lower() or "No unused" in out

    def test_unused_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from wadlib.cli.commands import scan_textures

        scan_textures.run(_ns(json=True, unused=True))
        data = json.loads(capsys.readouterr().out)
        assert "unused_textures" in data
        assert "unused_flats" in data
        assert isinstance(data["unused_textures"], list)
