"""DEHACKED lump parser — extracts PAR times from DeHackEd patches."""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

from .base import BaseLump

# par E M seconds  (Doom 1)
_PAR1_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# par MM seconds   (Doom 2)
_PAR2_RE = re.compile(r"^\s*par\s+(\d+)\s+(\d+)\s*$", re.IGNORECASE)
# start/end of a bracketed section
_SECTION_RE = re.compile(r"^\s*\[(\w+)\]")


class DehackedLump(BaseLump):
    """DEHACKED lump: DeHackEd patch embedded in a WAD.

    Currently exposes only PAR times.  The full DEHACKED format covers
    thing/weapon/frame/sound/text replacements; those sections are
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
            # Strip inline comments
            line = re.sub(r"#.*$", "", line)

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
