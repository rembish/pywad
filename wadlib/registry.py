"""Lump decoder registry and map-data dispatch tables.

Centralises two previously inlined concerns from ``wad.py``:

1. **Map-data dispatch** — ``_DOOM_DISPATCH``, ``_HEXEN_OVERRIDES``, and
   ``attach_map_lumps`` (the function that wires raw directory entries into a
   ``BaseMapEntry``).

2. **Simple lump registry** — ``DecoderRegistry``, a name → constructor map
   that lets external callers (and future plug-ins) look up or extend the
   decoder for any named lump.  ``LUMP_REGISTRY`` is the default instance
   pre-populated with every decoder built into wadlib.

Usage::

    from wadlib.registry import LUMP_REGISTRY, DecoderRegistry

    # Decode a lump using the built-in registry
    lump = LUMP_REGISTRY.find_and_decode("PLAYPAL", wad)

    # Extend the registry with a custom decoder
    LUMP_REGISTRY.register("MYDATA", MyLump)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from .directory import DirectoryEntry
from .enums import MapData
from .lumps.animdefs import AnimDefsLump
from .lumps.base import BaseLump
from .lumps.behavior import BehaviorLump
from .lumps.blockmap import BlockMap, Reject
from .lumps.colormap import ColormapLump
from .lumps.decorate import DecorateLump
from .lumps.dehacked import DehackedLump
from .lumps.endoom import Endoom
from .lumps.hexen import HexenLineDefs, HexenThings
from .lumps.language import LanguageLump
from .lumps.lines import Lines
from .lumps.mapinfo import MapInfoLump
from .lumps.nodes import Nodes
from .lumps.playpal import PlayPal
from .lumps.sectors import Sectors
from .lumps.segs import Segs, SubSectors
from .lumps.sidedefs import SideDefs
from .lumps.sndinfo import SndInfo
from .lumps.sndseq import SndSeqLump
from .lumps.textures import PNames, TextureList
from .lumps.things import Things
from .lumps.udmf import UdmfLump
from .lumps.vertices import Vertices
from .lumps.zmapinfo import ZMapInfoLump
from .lumps.znodes import ZNodesLump

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry


# ---------------------------------------------------------------------------
# Protocol — anything with find_lump
# ---------------------------------------------------------------------------


class WadLike(Protocol):
    """Structural type for objects that expose lump look-up."""

    def find_lump(self, name: str) -> DirectoryEntry | None:
        """Return the directory entry for *name*, or ``None``."""
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Map-data dispatch (moved from wad.py)
# ---------------------------------------------------------------------------

# Doom-format lump dispatch: name -> (attach method, constructor)
_DOOM_DISPATCH: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
    "THINGS": ("attach_things", Things),
    "VERTEXES": ("attach_vertices", Vertices),
    "LINEDEFS": ("attach_linedefs", Lines),
    "SIDEDEFS": ("attach_sidedefs", SideDefs),
    "SECTORS": ("attach_sectors", Sectors),
    "SEGS": ("attach_segs", Segs),
    "SSECTORS": ("attach_ssectors", SubSectors),
    "NODES": ("attach_nodes", Nodes),
    "REJECT": ("attach_reject", Reject),
    "BLOCKMAP": ("attach_blockmap", BlockMap),
    "ZNODES": ("attach_znodes", ZNodesLump),
    "BEHAVIOR": ("attach_behavior", BehaviorLump),
    "TEXTMAP": ("attach_textmap", UdmfLump),
}

# Hexen overrides only differ for THINGS and LINEDEFS
_HEXEN_OVERRIDES: dict[str, tuple[str, Callable[[DirectoryEntry], object]]] = {
    "THINGS": ("attach_things", HexenThings),
    "LINEDEFS": ("attach_linedefs", HexenLineDefs),
}


def attach_map_lumps(map_entry: BaseMapEntry, lumps: list[DirectoryEntry], hexen: bool) -> None:
    """Attach *lumps* to *map_entry* using the appropriate dispatch table.

    This is the canonical implementation of the Doom map-lump wiring step,
    previously inlined as ``_attach_lumps`` in ``wad.py``.  Hexen maps use a
    different ``THINGS`` and ``LINEDEFS`` layout; set *hexen=True* to activate
    those overrides.
    """
    dispatch = dict(_DOOM_DISPATCH)
    if hexen:
        dispatch.update(_HEXEN_OVERRIDES)

    for entry in lumps:
        if entry.name not in MapData.names():
            continue
        action = dispatch.get(entry.name)
        if action:
            method_name, constructor = action
            getattr(map_entry, method_name)(constructor(entry))
        else:
            map_entry.attach(entry)


# ---------------------------------------------------------------------------
# Simple lump registry
# ---------------------------------------------------------------------------


class DecoderRegistry:
    """Maps lump names to their decoder constructors.

    The registry is intentionally simple: a name → constructor dict with
    ``register`` / ``decode`` / ``find_and_decode`` helpers.  External code
    (plug-ins, game-specific tooling) can extend the built-in ``LUMP_REGISTRY``
    without touching wadlib's source.

    Example::

        from wadlib.registry import LUMP_REGISTRY
        from myplugin import MyLump

        LUMP_REGISTRY.register("MYDATA", MyLump)

        with WadFile("custom.wad") as wad:
            lump = LUMP_REGISTRY.find_and_decode("MYDATA", wad)
    """

    def __init__(self) -> None:
        self._registry: dict[str, Callable[[DirectoryEntry], BaseLump[Any]]] = {}

    def register(self, name: str, constructor: Callable[[DirectoryEntry], BaseLump[Any]]) -> None:
        """Register *constructor* as the decoder for lumps named *name*."""
        self._registry[name] = constructor

    def decode(self, name: str, entry: DirectoryEntry) -> BaseLump[Any]:
        """Decode *entry* using the registered constructor for *name*.

        Falls back to ``BaseLump`` when no constructor is registered, so callers
        can always get *something* even for unknown lump types.
        """
        ctor = self._registry.get(name, BaseLump)
        return ctor(entry)

    def find_and_decode(self, name: str, wad: WadLike) -> BaseLump[Any] | None:
        """Find *name* in *wad* and decode it, or return ``None``.

        Uses ``wad.find_lump`` so it works with any :class:`WadLike` — including
        stacked PWAD configurations.
        """
        entry = wad.find_lump(name)
        return self.decode(name, entry) if entry else None

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)

    def names(self) -> list[str]:
        """Return the list of registered lump names."""
        return list(self._registry)


# ---------------------------------------------------------------------------
# Default registry — pre-populated with all built-in decoders
# ---------------------------------------------------------------------------

LUMP_REGISTRY: DecoderRegistry = DecoderRegistry()

_SIMPLE_LUMPS: list[tuple[str, Callable[[DirectoryEntry], BaseLump[Any]]]] = [
    ("PLAYPAL", PlayPal),
    ("COLORMAP", ColormapLump),
    ("PNAMES", PNames),
    ("TEXTURE1", TextureList),
    ("TEXTURE2", TextureList),
    ("ENDOOM", Endoom),
    ("SNDINFO", SndInfo),
    ("SNDSEQ", SndSeqLump),
    ("MAPINFO", MapInfoLump),
    ("ZMAPINFO", ZMapInfoLump),
    ("LANGUAGE", LanguageLump),
    ("ANIMDEFS", AnimDefsLump),
    ("DECORATE", DecorateLump),
    ("DEHACKED", DehackedLump),
]

for _name, _ctor in _SIMPLE_LUMPS:
    LUMP_REGISTRY.register(_name, _ctor)
