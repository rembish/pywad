"""ZMAPINFO lump parser (ZDoom format) — brace-delimited map metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

from .base import BaseLump

_MAP_RE = re.compile(r"^map\s+(\S+)\s*(.*)", re.IGNORECASE)
# lookup "KEY" title syntax
_LOOKUP_RE = re.compile(r'^lookup\s+"([^"]+)"', re.IGNORECASE)
_BLOCK_START_RE = re.compile(r"^(gameinfo|episode|defaultmap|cluster|map)\b", re.IGNORECASE)


def _strip_comments(text: str) -> str:
    """Remove // line comments and /* */ block comments."""
    # Block comments first
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _unquote(s: str) -> str:
    s = s.strip().strip('"').strip("'")
    # $STRREF placeholders — return the ref name without $
    return s


@dataclass
class ZMapInfoEntry:
    """A single map block from ZMAPINFO."""

    map_name: str           # e.g. "E5M1", "MAP01"
    title: str              # display title (may be empty if resolved via lookup)
    title_lookup: str | None = None  # LANGUAGE key when title uses lookup "KEY"
    levelnum: int | None = None
    next: str | None = None
    secretnext: str | None = None
    sky1: str | None = None
    music: str | None = None
    titlepatch: str | None = None
    cluster: int | None = None
    par: int | None = None  # par time in seconds

    def resolved_title(self, language: dict[str, str] | None = None) -> str:
        """Return the display title, resolving lookup keys via *language* if provided."""
        if self.title_lookup and language:
            return language.get(self.title_lookup.upper(), self.title)
        return self.title


class ZMapInfoLump(BaseLump):
    """ZMAPINFO lump: ZDoom-format map metadata with brace-delimited blocks."""

    @cached_property
    def maps(self) -> list[ZMapInfoEntry]:
        """Return all map entries."""
        text = _strip_comments(self.raw().decode("latin-1"))
        entries: list[ZMapInfoEntry] = []

        lines = iter(text.splitlines())
        for line in lines:
            stripped = line.strip()
            m = _MAP_RE.match(stripped)
            if not m:
                continue

            map_name = m.group(1).upper()
            raw_after = m.group(2).strip()

            # Detect  lookup "KEY"  vs  "Direct title"  vs  bare title
            lookup_m = _LOOKUP_RE.match(raw_after)
            if lookup_m:
                title_lookup: str | None = lookup_m.group(1)
                raw_title = ""
            else:
                title_lookup = None
                raw_title = raw_after.strip('"').strip("'")

            entry = ZMapInfoEntry(
                map_name=map_name,
                title=raw_title,
                title_lookup=title_lookup,
            )

            # Consume the { ... } block (opening brace may follow on same line or next)
            block_text = raw_after
            if "{" not in block_text:
                for inner in lines:
                    block_text = inner
                    if "{" in inner:
                        break

            depth = block_text.count("{") - block_text.count("}")
            block_lines = []
            if depth > 0:
                for inner in lines:
                    block_lines.append(inner)
                    depth += inner.count("{") - inner.count("}")
                    if depth <= 0:
                        break

            for prop_line in block_lines:
                prop = prop_line.strip()
                if not prop:
                    continue
                kv = prop.split("=", 1)
                key = kv[0].strip().lower()
                val = _unquote(kv[1].split(",")[0]) if len(kv) == 2 else ""

                if key == "levelnum":
                    with __import__("contextlib").suppress(ValueError):
                        entry.levelnum = int(val)
                elif key == "next":
                    entry.next = val.strip().upper()
                elif key == "secretnext":
                    entry.secretnext = val.strip().upper()
                elif key == "sky1":
                    entry.sky1 = val.strip()
                elif key == "music":
                    entry.music = val.strip()
                elif key == "titlepatch":
                    entry.titlepatch = val.strip()
                elif key == "cluster":
                    with __import__("contextlib").suppress(ValueError):
                        entry.cluster = int(val)
                elif key == "par":
                    with __import__("contextlib").suppress(ValueError):
                        entry.par = int(val)

            entries.append(entry)

        return entries

    def get(self, map_name: str) -> ZMapInfoEntry | None:  # type: ignore[override]
        """Return the entry for the given map name (case-insensitive), or None."""
        return next(
            (e for e in self.maps if e.map_name == map_name.upper()),
            None,
        )
