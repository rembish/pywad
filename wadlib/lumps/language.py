"""LANGUAGE lump parser — ZDoom localisation string table."""

from __future__ import annotations

import re
from functools import cached_property

from .base import BaseLump

# KEY = "value";   (inside a language block)
_ENTRY_RE = re.compile(r"^\s*(\w+)\s*=\s*\"((?:[^\"\\]|\\.)*)\"\s*;?\s*$")
# [section] or [enu default] block headers
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]")


class LanguageLump(BaseLump):
    """LANGUAGE lump: ZDoom localisation strings.

    Parses all ``[enu default]`` / ``[enu]`` / ``[default]`` sections and
    exposes them as a flat ``dict[str, str]`` keyed by the uppercase string ID.
    Other language sections (``[fra]``, ``[deu]``, …) are skipped — English
    strings are sufficient for map title resolution.

    Usage::

        strings = wad.language
        title = strings.get("HUSTR_1", "")
    """

    _ENGLISH_SECTIONS = frozenset({"enu", "default", "enu default", "default enu"})

    @cached_property
    def strings(self) -> dict[str, str]:
        """Return all English localisation strings, keyed by uppercase ID."""
        text = self.raw().decode("latin-1")
        result: dict[str, str] = {}
        in_english = False

        for line in text.splitlines():
            # Strip // line comments
            line = re.sub(r"//[^\n]*", "", line).strip()
            if not line:
                continue

            sec = _SECTION_RE.match(line)
            if sec:
                section_key = sec.group(1).strip().lower()
                in_english = section_key in self._ENGLISH_SECTIONS
                continue

            if not in_english:
                continue

            m = _ENTRY_RE.match(line)
            if m:
                key = m.group(1).upper()
                value = m.group(2).replace('\\"', '"').replace("\\n", "\n")
                result[key] = value

        return result

    def lookup(self, key: str, default: str = "") -> str:
        """Return the string for *key* (case-insensitive), or *default*."""
        return self.strings.get(key.upper(), default)
