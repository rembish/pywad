"""DECORATE lump parser — extract actor definitions from GZDoom mods.

DECORATE is a text-based actor definition language used by ZDoom/GZDoom.
Each actor block defines a new thing type with properties, flags, and
state sequences.

This parser extracts the key metadata needed for map analysis:
- Actor name and parent class
- DoomEdNum (editor number for placing in maps)
- Properties: health, speed, radius, height, mass, damage, etc.
- Flags: SOLID, SHOOTABLE, COUNTKILL, COUNTITEM, etc.
- State labels (Spawn, See, Melee, Missile, Death, etc.)

It does NOT fully evaluate ZScript expressions or resolve inheritance
chains — that would require a full scripting engine.

Reference: https://zdoom.org/wiki/DECORATE

Usage::

    from wadlib.lumps.decorate import parse_decorate

    with open("DECORATE.txt") as f:
        actors = parse_decorate(f.read())
    for actor in actors:
        print(f"{actor.name} (ednum={actor.doomednum})")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from functools import cached_property
from typing import Any

from .base import BaseLump

_ACTOR_RE = re.compile(
    r"^\s*actor\s+(\w+)"  # actor name
    r"(?:\s*:\s*(\w+))?"  # optional parent class
    r"(?:\s+(\d+))?"  # optional doomednum
    r"(?:\s+replaces\s+(\w+))?",  # optional replaces
    re.IGNORECASE,
)

_PROPERTY_RE = re.compile(r"^\s+(\w+(?:\.\w+)?)(?:\s+(.*))?$", re.IGNORECASE)
_FLAG_RE = re.compile(r"(?:^|\s)([+-])(\w+(?:\.\w+)?)", re.IGNORECASE)
_STATE_LABEL_RE = re.compile(r"^\s+(\w+):\s*$")
_INCLUDE_RE = re.compile(r'^\s*#include\s+"([^"]+)"', re.IGNORECASE)


@dataclass
class DecorateActor:
    """A parsed DECORATE actor definition."""

    name: str
    parent: str = ""
    doomednum: int | None = None
    replaces: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    antiflags: set[str] = field(default_factory=set)
    states: list[str] = field(default_factory=list)

    @property
    def health(self) -> int | None:
        v = self.properties.get("health")
        return int(v) if v and v.isdigit() else None

    @property
    def speed(self) -> int | None:
        v = self.properties.get("speed")
        return int(v) if v and v.isdigit() else None

    @property
    def radius(self) -> int | None:
        v = self.properties.get("radius")
        return int(v) if v and v.isdigit() else None

    @property
    def height(self) -> int | None:
        v = self.properties.get("height")
        return int(v) if v and v.isdigit() else None

    @property
    def is_monster(self) -> bool:
        return "ISMONSTER" in self.flags or "COUNTKILL" in self.flags

    @property
    def is_item(self) -> bool:
        return "COUNTITEM" in self.flags


def parse_decorate(text: str) -> list[DecorateActor]:
    """Parse a DECORATE lump and return all actor definitions.

    Handles nested braces, multi-line blocks, comments, and #include
    directives (recorded but not resolved).
    """
    # Strip comments
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)

    actors: list[DecorateActor] = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]
        i += 1

        m = _ACTOR_RE.match(line)
        if not m:
            continue

        actor = DecorateActor(
            name=m.group(1),
            parent=m.group(2) or "",
            doomednum=int(m.group(3)) if m.group(3) else None,
            replaces=m.group(4) or "",
        )

        # Find opening brace — collect all text between { and }
        # For inline blocks like "actor X 1 { Health 50 }", expand into lines
        full_body = ""
        brace_depth = 0

        # Check if opening brace is on the actor line itself
        if "{" in line:
            after_brace = line[line.index("{") + 1 :]
            full_body = after_brace + "\n"
            brace_depth = 1 + after_brace.count("{") - after_brace.count("}")
        else:
            while i < len(lines):
                bline = lines[i].strip()
                i += 1
                if "{" in bline:
                    after_brace = bline[bline.index("{") + 1 :]
                    full_body = after_brace + "\n"
                    brace_depth = 1 + after_brace.count("{") - after_brace.count("}")
                    break

        # Collect remaining body lines
        while i < len(lines) and brace_depth > 0:
            brace_depth += lines[i].count("{") - lines[i].count("}")
            if brace_depth > 0:
                full_body += lines[i] + "\n"
            else:
                # Include content before closing brace
                last = lines[i]
                close_idx = last.rfind("}")
                if close_idx > 0:
                    full_body += last[:close_idx] + "\n"
            i += 1

        # Now parse body lines
        body_lines = full_body.splitlines()

        in_states = False

        # Parse body
        for raw_line in body_lines:
            bline = raw_line.strip()

            if not bline:
                continue

            # States block
            if (
                bline.lower() == "states"
                or bline.lower().startswith("states{")
                or bline.lower().startswith("states {")
            ):
                in_states = True
                continue

            if in_states:
                sl = _STATE_LABEL_RE.match(raw_line)
                if sl:
                    actor.states.append(sl.group(1))
                continue

            # Flags (+FLAG / -FLAG) — may have multiple per line
            flag_matches = list(_FLAG_RE.finditer(raw_line))
            if flag_matches:
                for fm in flag_matches:
                    flag_name = fm.group(2).upper()
                    if fm.group(1) == "+":
                        actor.flags.add(flag_name)
                    else:
                        actor.antiflags.add(flag_name)
                continue

            # Properties
            pm = _PROPERTY_RE.match(raw_line)
            if pm:
                prop_name = pm.group(1).lower()
                prop_value = (pm.group(2) or "").strip().rstrip(";").strip()
                if prop_name == "monster":
                    actor.flags.add("ISMONSTER")
                elif prop_name == "projectile":
                    actor.flags.add("MISSILE")
                else:
                    actor.properties[prop_name] = prop_value

        actors.append(actor)

    return actors


def resolve_inheritance(actors: list[DecorateActor]) -> list[DecorateActor]:
    """Return new DecorateActor instances with inherited properties and flags filled in.

    Walk each actor's parent chain from the oldest ancestor forward, merging
    properties and flags with child definitions winning over parent definitions:

    - ``properties``: parent values are the base; child values override.
    - ``flags``: union of parent and child set-flags, then subtract child antiflags.
    - ``antiflags``: union of parent and child antiflags.
    - ``states``: child states list if non-empty, otherwise parent states.
    - ``doomednum``: child value if present, otherwise inherited from parent.
    - ``replaces``: child value always kept.

    Actors whose parent class is not in the input list are returned unchanged.
    Inheritance cycles are detected and broken at the cycle entry point.

    The input list and actor objects are not mutated; new instances are returned.
    """
    by_name: dict[str, DecorateActor] = {a.name.upper(): a for a in actors}

    def _resolve(actor: DecorateActor, visiting: frozenset[str]) -> DecorateActor:
        parent_upper = actor.parent.upper() if actor.parent else ""
        if not parent_upper or parent_upper not in by_name or parent_upper in visiting:
            return actor
        parent = _resolve(by_name[parent_upper], visiting | {actor.name.upper()})
        return replace(
            actor,
            properties={**parent.properties, **actor.properties},
            flags=(parent.flags | actor.flags) - actor.antiflags,
            antiflags=parent.antiflags | actor.antiflags,
            states=actor.states if actor.states else parent.states,
            doomednum=actor.doomednum if actor.doomednum is not None else parent.doomednum,
        )

    return [_resolve(a, frozenset({a.name.upper()})) for a in actors]


class DecorateLump(BaseLump[Any]):
    """A DECORATE lump containing ZDoom actor definitions."""

    @cached_property
    def actors(self) -> list[DecorateActor]:
        return parse_decorate(self.raw().decode("utf-8", errors="replace"))

    @cached_property
    def editor_numbers(self) -> dict[int, DecorateActor]:
        """Return actors keyed by DoomEdNum (only those with one assigned)."""
        return {a.doomednum: a for a in self.actors if a.doomednum is not None}
