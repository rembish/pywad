"""Texture and flat usage scanner — report which assets maps actually use.

Scans all maps in a WAD and reports which wall textures, floor/ceiling
flats, and thing types are referenced.  Useful for:

- Extracting only the assets a PWAD actually needs from the IWAD
- Finding unused lumps
- Auditing resource dependencies

Usage::

    from wadlib.scanner import scan_usage
    from wadlib.wad import WadFile

    with WadFile("mymod.wad") as wad:
        usage = scan_usage(wad)
        print("Textures:", usage.textures)
        print("Flats:", usage.flats)
        print("Thing types:", usage.thing_types)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .wad import WadFile


@dataclass
class UsageReport:
    """Aggregated resource usage across all maps in a WAD."""

    textures: set[str] = field(default_factory=set)
    flats: set[str] = field(default_factory=set)
    thing_types: set[int] = field(default_factory=set)
    # Per-map breakdown
    per_map: dict[str, MapUsage] = field(default_factory=dict)

    @property
    def total_unique_textures(self) -> int:
        return len(self.textures)

    @property
    def total_unique_flats(self) -> int:
        return len(self.flats)

    @property
    def total_unique_thing_types(self) -> int:
        return len(self.thing_types)


@dataclass
class MapUsage:
    """Resource usage for a single map."""

    name: str
    textures: set[str] = field(default_factory=set)
    flats: set[str] = field(default_factory=set)
    thing_types: set[int] = field(default_factory=set)
    thing_count: int = 0
    linedef_count: int = 0
    sector_count: int = 0


_NO_TEXTURE = "-"


def scan_usage(wad: WadFile) -> UsageReport:
    """Scan all maps in a WAD and report texture/flat/thing usage."""
    report = UsageReport()

    for m in wad.maps:
        mu = MapUsage(name=m.name)

        # Scan sidedefs for wall textures
        if m.sidedefs:
            for sd in m.sidedefs:
                for tex in (sd.upper_texture, sd.lower_texture, sd.middle_texture):
                    name = tex.upper() if isinstance(tex, str) else tex
                    if name and name != _NO_TEXTURE:
                        mu.textures.add(name)
                        report.textures.add(name)

        # Scan sectors for floor/ceiling flats
        if m.sectors:
            mu.sector_count = len(m.sectors)
            for sec in m.sectors:
                for flat_name in (sec.floor_texture, sec.ceiling_texture):
                    name = flat_name.upper() if isinstance(flat_name, str) else flat_name
                    if name and name != _NO_TEXTURE:
                        mu.flats.add(name)
                        report.flats.add(name)

        # Scan things for type usage
        if m.things:
            mu.thing_count = len(list(m.things))
            for thing in m.things:
                mu.thing_types.add(thing.type)
                report.thing_types.add(thing.type)

        if m.lines:
            mu.linedef_count = len(list(m.lines))

        report.per_map[m.name] = mu

    return report


def find_unused_textures(wad: WadFile) -> set[str]:
    """Return texture names defined in TEXTURE1/2 but not used by any map."""
    usage = scan_usage(wad)
    defined: set[str] = set()
    for tl in (wad.texture1, wad.texture2):
        if tl:
            defined.update(t.name.upper() for t in tl.textures)
    return defined - usage.textures


def find_unused_flats(wad: WadFile) -> set[str]:
    """Return flat names in F_START/F_END but not used by any map."""
    usage = scan_usage(wad)
    defined = {name.upper() for name in wad.flats}
    return defined - usage.flats
