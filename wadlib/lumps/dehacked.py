"""DEHACKED lump parser — extracts PAR times and custom Thing definitions.

Supported formats:
- Classic DeHackEd v3.0 (Doom version = 19)
- BEX extensions (Doom version = 21, Patch format = 6 / DEHEXTRA/MBF21)

Thing blocks with an ``ID # = N`` field define new in-game DoomEd type IDs
that extend the stock type table.  Custom WADs like REKKR and Eviternity use
this mechanism to add monsters, decorations, and ambient-sound objects beyond
the 137 standard Doom 2 things.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

from .base import BaseLump

# par E M seconds  (Doom 1)
_PAR1_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# par MM seconds   (Doom 2)
_PAR2_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# start/end of a bracketed section
_SECTION_RE = re.compile(r"^\s*\[(\w+)\]")
# Thing block header:  "Thing N (Name)"
_THING_RE = re.compile(r"^Thing\s+(\d+)\s*(?:\(([^)]*)\))?", re.IGNORECASE)
# Property line:  "Key = value"
_PROP_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 #]*?)\s*=\s*(.+)$")

# Doom mobj flag bit values (from p_mobj.h)
_MF_COUNTKILL: int = 0x00400000   # counts toward kill percentage
_MF_COUNTITEM: int = 0x00800000   # counts toward item percentage

# BEX text → numeric bit mapping (subset; enough for category detection)
_BEX_BITS: dict[str, int] = {
    "SPECIAL":      0x00000001,
    "SOLID":        0x00000002,
    "SHOOTABLE":    0x00000004,
    "NOSECTOR":     0x00000008,
    "NOBLOCKMAP":   0x00000010,
    "AMBUSH":       0x00000020,
    "JUSTHIT":      0x00000040,
    "JUSTATTACKED": 0x00000080,
    "SPAWNCEILING": 0x00000100,
    "NOGRAVITY":    0x00000200,
    "DROPOFF":      0x00000400,
    "PICKUP":       0x00000800,
    "NOCLIP":       0x00001000,
    "SLIDE":        0x00002000,
    "FLOAT":        0x00004000,
    "TELEPORT":     0x00008000,
    "MISSILE":      0x00010000,
    "DROPPED":      0x00020000,
    "SHADOW":       0x00040000,
    "NOBLOOD":      0x00080000,
    "CORPSE":       0x00100000,
    "INFLOAT":      0x00200000,
    "COUNTKILL":    _MF_COUNTKILL,
    "COUNTITEM":    _MF_COUNTITEM,
    "SKULLFLY":     0x01000000,
    "NOTDMATCH":    0x02000000,
}


def _parse_bits(value: str) -> int:
    """Parse a DEHACKED Bits value: either a decimal integer or BEX flag names."""
    value = value.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    result = 0
    for token in re.split(r"[+|,\s]+", value.upper()):
        token = token.strip()
        if token:
            result |= _BEX_BITS.get(token, 0)
    return result


@dataclass
class DehackedThing:
    """A Thing block from a DEHACKED patch that defines a new in-game type.

    Only things with an ``ID # = N`` field are included; those without it
    simply modify existing stock Doom types and are handled by the base
    game type tables.
    """

    type_id: int          # DoomEd editor type number (from "ID # = N")
    name: str             # human-readable name from the block header
    bits: int             # raw mobj flags
    initial_frame: int | None = field(default=None)

    @property
    def is_monster(self) -> bool:
        return bool(self.bits & _MF_COUNTKILL)

    @property
    def is_item(self) -> bool:
        return bool(self.bits & _MF_COUNTITEM)


class DehackedLump(BaseLump[Any]):
    """DEHACKED lump: DeHackEd patch embedded in a WAD.

    Exposes PAR times and custom Thing type definitions.  The full DEHACKED
    format covers frame/weapon/sound/text replacements; those sections are
    accessible via ``raw()`` if needed.
    """

    @cached_property
    def _text(self) -> str:
        return self.raw().decode("latin-1")

    @cached_property
    def par_times(self) -> dict[str, int]:
        """Return PAR times keyed by map name (e.g. ``"E5M1"``, ``"MAP01"``).

        Reads the ``[PARS]`` section of the DEHACKED lump.  Both Doom-1 and
        Doom-2 par formats are supported::

            par 5 1 90    → {"E5M1": 90, …}
            par 01 120    → {"MAP01": 120, …}
        """
        result: dict[str, int] = {}
        in_pars = False

        for line in self._text.splitlines():
            # Strip trailing inline comments.  PAR lines use "par 1 1 30 # 00:30" style;
            # for the [PARS] section this is safe because no keyword contains a literal #.
            line = re.sub(r"\s+#.*$", "", line)

            sec = _SECTION_RE.match(line)
            if sec:
                in_pars = sec.group(1).upper() == "PARS"
                continue

            if not in_pars:
                continue

            m1 = _PAR1_RE.match(line)
            if m1:
                ep, mp, secs = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
                result[f"E{ep}M{mp}"] = secs
                continue

            m2 = _PAR2_RE.match(line)
            if m2:
                mapnum, secs = int(m2.group(1)), int(m2.group(2))
                result[f"MAP{mapnum:02d}"] = secs

        return result

    @cached_property
    def doom_version(self) -> int | None:
        """Return the ``Doom version`` field from the patch header, or ``None``."""
        m = re.search(r"^Doom version\s*=\s*(\d+)", self._text, re.MULTILINE | re.IGNORECASE)
        return int(m.group(1)) if m else None

    @cached_property
    def patch_format(self) -> int | None:
        """Return the ``Patch format`` field from the patch header, or ``None``."""
        m = re.search(r"^Patch format\s*=\s*(\d+)", self._text, re.MULTILINE | re.IGNORECASE)
        return int(m.group(1)) if m else None

    @cached_property
    def things(self) -> dict[int, DehackedThing]:
        """Return custom Thing type definitions keyed by in-game DoomEd type ID.

        Only includes Thing blocks that contain an ``ID # = N`` field — these
        are DEHEXTRA/BEX-extended types that go beyond the 137 stock Doom things.
        Blocks without ``ID #`` are stock-type overrides handled by the base
        game type tables.

        Example::

            deh = wad.dehacked
            if deh:
                for type_id, thing in deh.things.items():
                    print(type_id, thing.name, "monster:", thing.is_monster)
        """
        result: dict[int, DehackedThing] = {}
        lines = self._text.splitlines()
        in_block = False
        current_name = ""
        current_props: dict[str, str] = {}

        def _flush() -> None:
            raw_id = current_props.get("id #")
            if raw_id is None:
                return
            try:
                type_id = int(raw_id.strip())
            except ValueError:
                return
            bits = _parse_bits(current_props.get("bits", "0"))
            frame_str = current_props.get("initial frame")
            initial_frame = int(frame_str) if frame_str and frame_str.strip().isdigit() else None
            result[type_id] = DehackedThing(
                type_id=type_id,
                name=current_name,
                bits=bits,
                initial_frame=initial_frame,
            )

        for line in lines:
            # Skip full-line comments (# must be the first non-space character).
            # Do NOT strip inline # — "ID # = N" uses # as part of the property name.
            stripped = line.rstrip()
            if re.match(r"^\s*#", stripped):
                continue

            m = _THING_RE.match(stripped)
            if m:
                if in_block:
                    _flush()
                in_block = True
                current_name = (m.group(2) or "").strip()
                current_props = {}
                continue

            if not in_block:
                continue

            # Blank line or a new top-level section header ends the block
            if not stripped:
                _flush()
                in_block = False
                current_props = {}
                continue

            # Any new non-Thing top-level keyword (e.g. "Frame N", "Weapon N", "[PARS]")
            # also ends the block
            if _SECTION_RE.match(stripped) or re.match(
                r"^(Frame|Weapon|Sound|Sprite|Ammo|Misc|Text|Cheat|Pointer)\s+\d+",
                stripped, re.IGNORECASE,
            ):
                _flush()
                in_block = False
                current_props = {}
                continue

            pm = _PROP_RE.match(stripped)
            if pm:
                key = pm.group(1).strip().lower()
                current_props[key] = pm.group(2).strip()

        # Flush the last block if file ends without trailing blank line
        if in_block:
            _flush()

        return result


class DehackedFile(DehackedLump):
    """Standalone ``.deh`` file on disk (not embedded in a WAD lump).

    Presents the same API as :class:`DehackedLump` so it can be used
    wherever a ``DehackedLump`` is expected::

        deh = DehackedFile("rekkr.deh")
        print(deh.par_times)
    """

    def __init__(self, path: str | Path) -> None:  # pylint: disable=super-init-not-called
        # Skip BaseLump.__init__ — we have no DirectoryEntry.
        object.__init__(self)  # pylint: disable=non-parent-init-called
        self._deh_path = Path(path)

    @cached_property
    def _text(self) -> str:
        return self._deh_path.read_bytes().decode("latin-1")

    def raw(self) -> bytes:
        return self._deh_path.read_bytes()
