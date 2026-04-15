"""LANGUAGE lump parser — ZDoom localisation string table."""

from __future__ import annotations

import re
from functools import cached_property
from typing import Any

from .base import BaseLump

# KEY = "value";   (inside a language block)
_ENTRY_RE = re.compile(r"^\s*(\w+)\s*=\s*\"((?:[^\"\\]|\\.)*)\"\s*;?\s*$")
# [section] or [enu default] block headers
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]")


def serialize_language(strings: dict[str, str], section: str = "enu default") -> str:
    """Serialize a string table to LANGUAGE lump text.

    Example::

        text = serialize_language({"HUSTR_1": "Level 1: Entryway"})
    """
    parts: list[str] = [f"[{section}]"]
    for key, value in strings.items():
        escaped = value.replace('"', '\\"').replace("\n", "\\n")
        parts.append(f'{key} = "{escaped}";')
    return "\n".join(parts) + "\n"


def _normalize_locale(raw: str) -> list[str]:
    """Split a combined section header like ``"enu default"`` into individual tokens.

    ``[enu default]`` declares that both the ``enu`` and ``default`` locales share
    the same string block, so both token names should map to that block's strings.
    """
    return [tok.strip().lower() for tok in raw.strip().lower().split() if tok.strip()]


_ENGLISH_TOKENS = frozenset({"enu", "default"})


class LanguageLump(BaseLump[Any]):
    """LANGUAGE lump: ZDoom localisation strings.

    Parses every ``[locale]`` section in the lump and exposes them as a nested
    ``dict[str, dict[str, str]]`` via :attr:`all_locales`.  The existing
    :attr:`strings` shortcut still returns only the English sections (``enu``,
    ``default``).

    Usage::

        # English strings (backward-compatible)
        title = wad.language.lookup("HUSTR_1")

        # French strings
        fr = wad.language.strings_for("fra")
        title_fr = fr.get("HUSTR_1", title)

        # All locales
        locales = wad.language.all_locales
        # locales == {"enu": {...}, "fra": {...}, ...}
    """

    _ENGLISH_SECTIONS = frozenset({"enu", "default", "enu default", "default enu"})

    @cached_property
    def all_locales(self) -> dict[str, dict[str, str]]:
        """Return every locale's strings, keyed by locale token (lowercase).

        A section header like ``[enu default]`` contributes to *both* the
        ``"enu"`` and ``"default"`` locale dicts.
        """
        text = self.raw().decode("latin-1")
        result: dict[str, dict[str, str]] = {}
        active_locales: list[str] = []

        for line in text.splitlines():
            line = re.sub(r"//[^\n]*", "", line).strip()
            if not line:
                continue

            sec = _SECTION_RE.match(line)
            if sec:
                active_locales = _normalize_locale(sec.group(1))
                for loc in active_locales:
                    if loc not in result:
                        result[loc] = {}
                continue

            if not active_locales:
                continue

            m = _ENTRY_RE.match(line)
            if m:
                key = m.group(1).upper()
                value = m.group(2).replace('\\"', '"').replace("\\n", "\n")
                for loc in active_locales:
                    result[loc][key] = value

        return result

    @cached_property
    def strings(self) -> dict[str, str]:
        """Return all English localisation strings, keyed by uppercase ID."""
        merged: dict[str, str] = {}
        for token in ("enu", "default"):
            merged.update(self.all_locales.get(token, {}))
        return merged

    def strings_for(self, locale: str) -> dict[str, str]:
        """Return strings for *locale* (e.g. ``"fra"``, ``"deu"``).

        Returns an empty dict if the locale is not present in the lump.
        Locale names are matched case-insensitively.
        """
        return self.all_locales.get(locale.lower().strip(), {})

    def lookup(self, key: str, default: str = "", locale: str | None = None) -> str:
        """Return the string for *key* (case-insensitive), or *default*.

        If *locale* is given, search only that locale's strings; otherwise
        search the merged English strings (``enu`` + ``default``).
        """
        pool = self.strings_for(locale) if locale else self.strings
        return pool.get(key.upper(), default)
