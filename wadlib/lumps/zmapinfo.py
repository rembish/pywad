"""ZMAPINFO lump parser (ZDoom format) — brace-delimited map metadata."""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from .base import BaseLump

_MAP_RE = re.compile(r"^map\s+(\S+)\s*(.*)", re.IGNORECASE)
_EPISODE_RE = re.compile(r"^episode\s+(\S+)\s*(.*)", re.IGNORECASE)
_CLUSTER_RE = re.compile(r"^cluster\s+(\d+)", re.IGNORECASE)
_DEFAULTMAP_RE = re.compile(r"^defaultmap\b", re.IGNORECASE)
_LOOKUP_RE = re.compile(r'^lookup\s+"([^"]+)"', re.IGNORECASE)


def _strip_comments(text: str) -> str:
    """Remove // line comments and /* */ block comments."""
    # Block comments first
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Line comments
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _unquote(s: str) -> str:
    return s.strip().strip('"').strip("'")


def _consume_block(lines: list[str], start: int) -> tuple[int, list[str]]:
    """Scan forward from *start* to find an opening brace, then collect body
    lines until the matching closing brace.

    Returns ``(next_index, body_lines)`` where *next_index* is the line index
    immediately after the closing brace.  If no opening brace is found,
    returns ``(start + 1, [])``.
    """
    i = start
    while i < len(lines):
        if "{" in lines[i]:
            break
        i += 1
    if i >= len(lines):
        return start + 1, []

    brace_pos = lines[i].index("{")
    rest = lines[i][brace_pos + 1 :]
    depth = 1 + rest.count("{") - rest.count("}")
    i += 1

    body: list[str] = []
    while i < len(lines) and depth > 0:
        depth += lines[i].count("{") - lines[i].count("}")
        if depth > 0:
            body.append(lines[i])
        else:
            close_idx = lines[i].rfind("}")
            if close_idx > 0:
                body.append(lines[i][:close_idx])
        i += 1

    return i, body


def _parse_block_kv(body_lines: list[str]) -> dict[str, str]:
    """Extract ``key = value`` pairs from block body lines into a raw dict."""
    kv: dict[str, str] = {}
    for raw in body_lines:
        prop = raw.strip()
        if not prop:
            continue
        parts = prop.split("=", 1)
        key = parts[0].strip().lower()
        if not key:
            continue
        if len(parts) == 2:
            # Strip comma-separated extras (e.g. sky1 = "SKY1", 200.0)
            kv[key] = _unquote(parts[1].split(",")[0])
        else:
            kv[key] = ""  # bare flag keyword (e.g. noskillmenu)
    return kv


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ZMapInfoEpisode:
    """An episode block from ZMAPINFO."""

    map: str  # first map of the episode (e.g. "E1M1")
    name: str = ""  # display name (direct string)
    name_lookup: str | None = None  # LANGUAGE key when name uses lookup "KEY"
    pic_name: str = ""  # graphic lump shown on the episode-select screen
    key: str = ""  # keyboard shortcut character
    no_skill_menu: bool = False  # skip skill-selection screen


@dataclass
class ZMapInfoCluster:
    """A cluster block from ZMAPINFO."""

    cluster_num: int
    exittext: str = ""
    entertext: str = ""
    exittextislump: bool = False  # exittext is a lump name rather than inline text
    entertextislump: bool = False  # entertext is a lump name rather than inline text
    music: str = ""
    flat: str = ""  # intermission background flat


@dataclass
class ZMapInfoEntry:
    """A single map block from ZMAPINFO."""

    map_name: str = ""  # e.g. "E5M1", "MAP01"
    title: str = ""  # display title (may be empty if resolved via lookup)
    title_lookup: str | None = None  # LANGUAGE key when title uses lookup "KEY"
    levelnum: int | None = None
    next: str | None = None
    secretnext: str | None = None
    sky1: str | None = None
    music: str | None = None
    titlepatch: str | None = None
    cluster: int | None = None
    par: int | None = None  # par time in seconds
    props: dict[str, str] = field(default_factory=dict)  # unrecognized block keys

    def resolved_title(self, language: dict[str, str] | None = None) -> str:
        """Return the display title, resolving lookup keys via *language* if provided."""
        if self.title_lookup and language:
            return language.get(self.title_lookup.upper(), self.title)
        return self.title


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def _build_map_entry(
    map_name: str,
    title: str,
    title_lookup: str | None,
    kv: dict[str, str],
) -> ZMapInfoEntry:
    """Build a :class:`ZMapInfoEntry` from parsed key-value pairs."""
    entry = ZMapInfoEntry(map_name=map_name, title=title, title_lookup=title_lookup)
    for key, val in kv.items():
        if key == "levelnum":
            with contextlib.suppress(ValueError):
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
            with contextlib.suppress(ValueError):
                entry.cluster = int(val)
        elif key == "par":
            with contextlib.suppress(ValueError):
                entry.par = int(val)
        else:
            entry.props[key] = val
    return entry


def _build_episode(ep_map: str, header_rest: str, kv: dict[str, str]) -> ZMapInfoEpisode:
    """Build a :class:`ZMapInfoEpisode` from parsed data."""
    lookup_m = _LOOKUP_RE.match(header_rest.strip())
    if lookup_m:
        name = ""
        name_lookup: str | None = lookup_m.group(1)
    else:
        name = _unquote(header_rest)
        name_lookup = None
    ep = ZMapInfoEpisode(map=ep_map, name=name, name_lookup=name_lookup)
    for key, val in kv.items():
        if key == "picname":
            ep.pic_name = val.strip()
        elif key == "key":
            ep.key = val.strip()
        elif key == "noskillmenu":
            ep.no_skill_menu = True
    return ep


def _build_cluster(cluster_num: int, kv: dict[str, str]) -> ZMapInfoCluster:
    """Build a :class:`ZMapInfoCluster` from parsed data."""
    cl = ZMapInfoCluster(cluster_num=cluster_num)
    for key, val in kv.items():
        if key == "exittext":
            cl.exittext = val.strip()
        elif key == "entertext":
            cl.entertext = val.strip()
        elif key == "exittextislump":
            cl.exittextislump = True
        elif key == "entertextislump":
            cl.entertextislump = True
        elif key == "music":
            cl.music = val.strip()
        elif key == "flat":
            cl.flat = val.strip()
    return cl


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def serialize_zmapinfo(entries: list[ZMapInfoEntry]) -> str:
    """Serialize a list of :class:`ZMapInfoEntry` to ZMAPINFO text (ZDoom format)."""
    parts: list[str] = []
    for e in entries:
        if e.title_lookup:
            parts.append(f'map {e.map_name} lookup "{e.title_lookup}"')
        else:
            parts.append(f'map {e.map_name} "{e.title}"')
        parts.append("{")
        if e.levelnum is not None:
            parts.append(f"    levelnum = {e.levelnum}")
        if e.next:
            parts.append(f'    next = "{e.next}"')
        if e.secretnext:
            parts.append(f'    secretnext = "{e.secretnext}"')
        if e.sky1:
            parts.append(f'    sky1 = "{e.sky1}"')
        if e.music:
            parts.append(f'    music = "{e.music}"')
        if e.titlepatch:
            parts.append(f'    titlepatch = "{e.titlepatch}"')
        if e.cluster is not None:
            parts.append(f"    cluster = {e.cluster}")
        if e.par is not None:
            parts.append(f"    par = {e.par}")
        for key, val in e.props.items():
            parts.append(f'    {key} = "{val}"' if val else f"    {key}")
        parts.append("}")
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Lump class
# ---------------------------------------------------------------------------


class ZMapInfoLump(BaseLump[Any]):
    """ZMAPINFO lump: ZDoom-format map metadata with brace-delimited blocks."""

    @cached_property
    def _parsed(  # pylint: disable=too-many-branches,too-many-statements
        self,
    ) -> tuple[
        list[ZMapInfoEntry],
        list[ZMapInfoEpisode],
        list[ZMapInfoCluster],
        ZMapInfoEntry | None,
    ]:
        """Parse all ZMAPINFO blocks in a single pass."""
        text = _strip_comments(self.raw().decode("latin-1"))
        lines = text.splitlines()

        map_entries: list[ZMapInfoEntry] = []
        episodes: list[ZMapInfoEpisode] = []
        clusters: list[ZMapInfoCluster] = []
        defaultmap_kv: dict[str, str] = {}
        defaultmap_entry: ZMapInfoEntry | None = None

        i = 0
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue

            # Map block
            m = _MAP_RE.match(stripped)
            if m:
                map_name = m.group(1).upper()
                raw_after = m.group(2).strip()
                lookup_m = _LOOKUP_RE.match(raw_after)
                if lookup_m:
                    title_lookup: str | None = lookup_m.group(1)
                    raw_title = ""
                else:
                    title_lookup = None
                    raw_title = raw_after.strip('"').strip("'")
                i, body = _consume_block(lines, i)
                merged = {**defaultmap_kv, **_parse_block_kv(body)}
                map_entries.append(_build_map_entry(map_name, raw_title, title_lookup, merged))
                continue

            # Episode block
            ep_m = _EPISODE_RE.match(stripped)
            if ep_m:
                ep_map = ep_m.group(1).upper()
                ep_rest = ep_m.group(2).strip()
                i, body = _consume_block(lines, i)
                episodes.append(_build_episode(ep_map, ep_rest, _parse_block_kv(body)))
                continue

            # Cluster block
            cl_m = _CLUSTER_RE.match(stripped)
            if cl_m:
                cluster_num = int(cl_m.group(1))
                i, body = _consume_block(lines, i)
                clusters.append(_build_cluster(cluster_num, _parse_block_kv(body)))
                continue

            # Defaultmap block
            if _DEFAULTMAP_RE.match(stripped):
                i, body = _consume_block(lines, i)
                defaultmap_kv = _parse_block_kv(body)
                defaultmap_entry = _build_map_entry("", "", None, defaultmap_kv)
                continue

            # Unrecognized block or directive — only consume a brace block if one
            # starts on this line or the very next, to avoid swallowing map blocks.
            if "{" in stripped or (i + 1 < len(lines) and "{" in lines[i + 1]):
                i, _ = _consume_block(lines, i)
            else:
                i += 1

        return map_entries, episodes, clusters, defaultmap_entry

    @property
    def maps(self) -> list[ZMapInfoEntry]:
        """Return all map entries."""
        return self._parsed[0]

    @property
    def episodes(self) -> list[ZMapInfoEpisode]:
        """Return all episode blocks."""
        return self._parsed[1]

    @property
    def clusters(self) -> list[ZMapInfoCluster]:
        """Return all cluster blocks."""
        return self._parsed[2]

    @property
    def defaultmap(self) -> ZMapInfoEntry | None:
        """Return the defaultmap baseline entry, or *None* if not present."""
        return self._parsed[3]

    def get_map(self, map_name: str) -> ZMapInfoEntry | None:
        """Return the entry for the given map name (case-insensitive), or None."""
        return next(
            (e for e in self.maps if e.map_name == map_name.upper()),
            None,
        )
