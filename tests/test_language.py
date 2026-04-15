"""Tests for the LANGUAGE lump parser — English and multi-locale support."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.language import serialize_language
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# serialize_language — unit tests
# ---------------------------------------------------------------------------


def test_serialize_language_basic() -> None:
    text = serialize_language({"HUSTR_1": "Level 1: Entryway"})
    assert "[enu default]" in text
    assert 'HUSTR_1 = "Level 1: Entryway";' in text
    assert text.endswith("\n")


def test_serialize_language_custom_section() -> None:
    text = serialize_language({"FOO": "bar"}, section="fra")
    assert "[fra]" in text
    assert 'FOO = "bar";' in text


def test_serialize_language_escapes_quotes() -> None:
    text = serialize_language({"A": 'say "hello"'})
    assert '\\"hello\\"' in text


# ---------------------------------------------------------------------------
# Helpers — build synthetic WADs
# ---------------------------------------------------------------------------


def _make_language_wad(lang_text: str) -> str:
    data = lang_text.encode("latin-1")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"LANGUAGE")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


# ---------------------------------------------------------------------------
# LanguageLump.strings — backward-compat English-only interface
# ---------------------------------------------------------------------------


def test_strings_enu_section() -> None:
    path = _make_language_wad('[enu]\nHUSTR_1 = "Level 1";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings["HUSTR_1"] == "Level 1"


def test_strings_default_section() -> None:
    path = _make_language_wad('[default]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings["FOO"] == "bar"


def test_strings_combined_enu_default() -> None:
    path = _make_language_wad('[enu default]\nHUSTR_1 = "Level 1";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings["HUSTR_1"] == "Level 1"


def test_strings_keys_uppercased() -> None:
    path = _make_language_wad('[enu]\nhustr_1 = "Level 1";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert "HUSTR_1" in wad.language.strings


def test_strings_comments_stripped() -> None:
    path = _make_language_wad('[enu]\n// comment\nFOO = "bar"; // inline\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings["FOO"] == "bar"


def test_lookup_english() -> None:
    path = _make_language_wad('[enu]\nHUSTR_1 = "Level 1";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.lookup("HUSTR_1") == "Level 1"


def test_lookup_default_value() -> None:
    path = _make_language_wad("[enu]\n")
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.lookup("MISSING", "fallback") == "fallback"


# ---------------------------------------------------------------------------
# LanguageLump.all_locales — multi-locale dict
# ---------------------------------------------------------------------------


def test_all_locales_contains_enu() -> None:
    path = _make_language_wad('[enu]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert "enu" in wad.language.all_locales


def test_all_locales_contains_fra() -> None:
    path = _make_language_wad('[fra]\nFOO = "truc";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert "fra" in wad.language.all_locales


def test_all_locales_multiple_sections() -> None:
    text = '[enu]\nFOO = "bar";\n[fra]\nFOO = "truc";\n[deu]\nFOO = "ding";\n'
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        locales = wad.language.all_locales
        assert set(locales.keys()) >= {"enu", "fra", "deu"}


def test_all_locales_combined_header_expands() -> None:
    """[enu default] must populate both 'enu' and 'default' locale keys."""
    path = _make_language_wad('[enu default]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        locales = wad.language.all_locales
        assert "enu" in locales
        assert "default" in locales
        assert locales["enu"]["FOO"] == "bar"
        assert locales["default"]["FOO"] == "bar"


def test_all_locales_values_correct() -> None:
    text = '[enu]\nHUSTR_1 = "Level 1";\n[fra]\nHUSTR_1 = "Niveau 1";\n'
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        locales = wad.language.all_locales
        assert locales["enu"]["HUSTR_1"] == "Level 1"
        assert locales["fra"]["HUSTR_1"] == "Niveau 1"


# ---------------------------------------------------------------------------
# LanguageLump.strings_for — locale-specific lookup
# ---------------------------------------------------------------------------


def test_strings_for_enu() -> None:
    path = _make_language_wad('[enu]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        d = wad.language.strings_for("enu")
        assert d["FOO"] == "bar"


def test_strings_for_fra() -> None:
    text = '[enu]\nFOO = "bar";\n[fra]\nFOO = "truc";\n'
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings_for("fra")["FOO"] == "truc"


def test_strings_for_case_insensitive() -> None:
    path = _make_language_wad('[enu]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings_for("ENU") == wad.language.strings_for("enu")


def test_strings_for_missing_locale_empty_dict() -> None:
    path = _make_language_wad('[enu]\nFOO = "bar";\n')
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.strings_for("xyz") == {}


# ---------------------------------------------------------------------------
# LanguageLump.lookup — locale parameter
# ---------------------------------------------------------------------------


def test_lookup_with_locale() -> None:
    text = '[enu]\nHUSTR_1 = "Level 1";\n[fra]\nHUSTR_1 = "Niveau 1";\n'
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.lookup("HUSTR_1", locale="fra") == "Niveau 1"


def test_lookup_with_locale_missing_key_returns_default() -> None:
    text = "[fra]\n"
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.lookup("HUSTR_1", default="?", locale="fra") == "?"


def test_lookup_locale_none_uses_english() -> None:
    text = '[enu]\nFOO = "bar";\n'
    path = _make_language_wad(text)
    with WadFile(path) as wad:
        assert wad.language is not None
        assert wad.language.lookup("FOO", locale=None) == "bar"


# ---------------------------------------------------------------------------
# WadFile.language absent
# ---------------------------------------------------------------------------


def test_language_none_when_absent(freedoom1_wad: WadFile) -> None:
    """Vanilla Doom WADs have no LANGUAGE lump."""
    assert freedoom1_wad.language is None
