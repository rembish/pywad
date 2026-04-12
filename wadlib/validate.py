"""Lump validation — catch format and naming errors before they hit the WAD.

Provides validators for lump names, lump data (known format rules), and
whole-WAD structural integrity.  Used by ``WadArchive`` on write, but also
usable standalone::

    from wadlib.validate import validate_lump, validate_name

    issues = validate_name("TOO_LONG_NAME")
    issues = validate_lump("THINGS", data)
    issues = validate_wad(writer)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .writer import WadWriter


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation problem found in a lump or WAD structure."""

    severity: Severity
    lump: str
    message: str

    def __repr__(self) -> str:
        return f"<{self.severity.value}: {self.lump}: {self.message}>"


class InvalidLumpError(Exception):
    """Raised when validation fails on a lump write operation."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        msgs = "; ".join(i.message for i in issues)
        super().__init__(f"Validation failed: {msgs}")


# ---------------------------------------------------------------------------
# Valid lump name charset: printable ASCII that Doom engines accept.
# Letters, digits, brackets, dash, underscore, backslash are the safe set.
# ---------------------------------------------------------------------------
_VALID_NAME_RE = re.compile(r"^[A-Z0-9\[\]\-_\\]+$")

# ---------------------------------------------------------------------------
# Known lump record sizes (vanilla Doom format)
# ---------------------------------------------------------------------------
_RECORD_SIZES: dict[str, tuple[int, str]] = {
    "THINGS": (10, "Doom thing (10 bytes each)"),
    "VERTEXES": (4, "vertex (4 bytes each)"),
    "LINEDEFS": (14, "Doom linedef (14 bytes each)"),
    "SIDEDEFS": (30, "sidedef (30 bytes each)"),
    "SECTORS": (26, "sector (26 bytes each)"),
    "SEGS": (12, "seg (12 bytes each)"),
    "SSECTORS": (4, "subsector (4 bytes each)"),
    "NODES": (28, "node (28 bytes each)"),
}

# Hexen-format record sizes (detected by context — caller must specify)
_HEXEN_RECORD_SIZES: dict[str, tuple[int, str]] = {
    "THINGS": (20, "Hexen thing (20 bytes each)"),
    "LINEDEFS": (16, "Hexen linedef (16 bytes each)"),
}

# Fixed-size lumps
_FIXED_SIZES: dict[str, tuple[int, str]] = {
    "COLORMAP": (8704, "34 colormaps x 256 bytes"),
    "ENDOOM": (4000, "80x25 ANSI screen x 2 bytes"),
}

# Multiple-of sizes (not fixed, but must be a multiple)
_MULTIPLE_SIZES: dict[str, tuple[int, str]] = {
    "PLAYPAL": (768, "palette (256 colors x 3 bytes)"),
}

# Flat size
_FLAT_SIZE = 4096  # 64x64

# Namespace markers
_NAMESPACE_PAIRS: list[tuple[str, str]] = [
    ("F_START", "F_END"),
    ("FF_START", "FF_END"),
    ("S_START", "S_END"),
    ("SS_START", "SS_END"),
    ("P_START", "P_END"),
    ("PP_START", "PP_END"),
]

# Picture format minimum header: width(2) + height(2) + offsets(2+2) = 8 bytes
_PICTURE_HEADER_SIZE = 8
_MAX_PICTURE_DIM = 4096  # sanity limit


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------


def validate_name(name: str) -> list[ValidationIssue]:
    """Validate a lump name for WAD compatibility."""
    issues: list[ValidationIssue] = []
    if not name:
        issues.append(ValidationIssue(Severity.ERROR, name, "lump name is empty"))
        return issues
    if len(name) > 8:
        issues.append(
            ValidationIssue(Severity.ERROR, name, f"lump name too long ({len(name)} chars, max 8)")
        )
    upper = name.upper()
    if upper != name:
        issues.append(
            ValidationIssue(
                Severity.WARNING, name, "lump name contains lowercase (will be uppercased)"
            )
        )
    if not _VALID_NAME_RE.match(upper):
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                name,
                "lump name contains invalid characters (only A-Z, 0-9, []\\-_ allowed)",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Lump data validation
# ---------------------------------------------------------------------------


def validate_lump(  # pylint: disable=too-many-branches
    name: str,
    data: bytes,
    *,
    hexen: bool = False,
    is_flat: bool = False,
    is_picture: bool = False,
) -> list[ValidationIssue]:
    """Validate lump data against known format rules.

    Parameters:
        name:       The lump name (used to infer expected format).
        data:       The raw lump bytes.
        hexen:      If True, use Hexen record sizes for THINGS/LINEDEFS.
        is_flat:    If True, validate as a flat (64x64 raw pixels).
        is_picture: If True, validate the Doom picture header.

    Returns a list of issues (may be empty if everything looks good).
    """
    issues: list[ValidationIssue] = []
    upper = name.upper()

    # Name validation
    issues.extend(validate_name(name))

    # Empty data is always valid (markers, empty lumps)
    if not data:
        return issues

    # Record-size checks for map lumps
    record_table = _HEXEN_RECORD_SIZES if hexen else _RECORD_SIZES
    if upper in record_table:
        rec_size, desc = record_table[upper]
        if len(data) % rec_size != 0:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    upper,
                    f"size {len(data)} is not a multiple of {rec_size} ({desc})",
                )
            )
        # Also check vanilla fallback for non-overridden lumps
        if hexen and upper not in _HEXEN_RECORD_SIZES and upper in _RECORD_SIZES:
            rec_size, desc = _RECORD_SIZES[upper]
            if len(data) % rec_size != 0:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR,
                        upper,
                        f"size {len(data)} is not a multiple of {rec_size} ({desc})",
                    )
                )
    elif upper in _RECORD_SIZES:
        rec_size, desc = _RECORD_SIZES[upper]
        if len(data) % rec_size != 0:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    upper,
                    f"size {len(data)} is not a multiple of {rec_size} ({desc})",
                )
            )

    # Fixed-size lumps
    if upper in _FIXED_SIZES:
        expected, desc = _FIXED_SIZES[upper]
        if len(data) != expected:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    upper,
                    f"expected exactly {expected} bytes ({desc}), got {len(data)}",
                )
            )

    # Multiple-of lumps
    if upper in _MULTIPLE_SIZES:
        mult, desc = _MULTIPLE_SIZES[upper]
        if len(data) % mult != 0:
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    upper,
                    f"size {len(data)} is not a multiple of {mult} ({desc})",
                )
            )

    # Flat validation
    if is_flat and len(data) != _FLAT_SIZE:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                upper,
                f"flat must be exactly {_FLAT_SIZE} bytes (64x64), got {len(data)}",
            )
        )

    # Picture header validation
    if is_picture:
        issues.extend(_validate_picture_header(upper, data))

    return issues


def _validate_picture_header(name: str, data: bytes) -> list[ValidationIssue]:
    """Validate the Doom picture format header."""
    issues: list[ValidationIssue] = []
    if len(data) < _PICTURE_HEADER_SIZE:
        issues.append(
            ValidationIssue(
                Severity.ERROR, name, f"picture too small ({len(data)} bytes, need at least 8)"
            )
        )
        return issues

    width = int.from_bytes(data[0:2], "little")
    height = int.from_bytes(data[2:4], "little")

    if width == 0 or height == 0:
        issues.append(
            ValidationIssue(Severity.ERROR, name, f"picture has zero dimension ({width}x{height})")
        )
    elif width > _MAX_PICTURE_DIM or height > _MAX_PICTURE_DIM:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                name,
                f"picture dimensions unusually large ({width}x{height})",
            )
        )

    # Column offset table must fit in the lump
    min_size = _PICTURE_HEADER_SIZE + width * 4
    if len(data) < min_size:
        issues.append(
            ValidationIssue(
                Severity.ERROR,
                name,
                f"picture too small for {width} column offsets "
                f"(need {min_size} bytes, got {len(data)})",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Whole-WAD structural validation
# ---------------------------------------------------------------------------


def validate_wad(writer: WadWriter) -> list[ValidationIssue]:
    """Validate the structural integrity of a WAD being built.

    Checks:
    - All lump names are valid
    - Known lump types have correct sizes
    - Namespace markers are properly paired
    - Map lumps appear after a map marker
    """
    issues: list[ValidationIssue] = []
    names = writer.lump_names

    # Name and size validation per lump
    for entry in writer.lumps:
        issues.extend(validate_name(entry.name))
        if entry.data:
            issues.extend(validate_lump(entry.name, entry.data))

    # Namespace pairing
    for start, end in _NAMESPACE_PAIRS:
        s_idx = writer.find_lump(start)
        e_idx = writer.find_lump(end)
        if s_idx != -1 and e_idx == -1:
            issues.append(
                ValidationIssue(Severity.ERROR, start, f"'{start}' marker without matching '{end}'")
            )
        elif s_idx == -1 and e_idx != -1:
            issues.append(
                ValidationIssue(Severity.ERROR, end, f"'{end}' marker without matching '{start}'")
            )
        elif s_idx != -1 and e_idx != -1 and s_idx >= e_idx:
            issues.append(
                ValidationIssue(Severity.ERROR, start, f"'{start}' appears after '{end}'")
            )

    # Map lump ordering: map data lumps should follow a map marker
    from .constants import DOOM1_MAP_NAME_REGEX, DOOM2_MAP_NAME_REGEX
    from .enums import MapData

    map_data_names = set(MapData.names())
    in_map = False
    for name in names:
        is_marker = bool(DOOM1_MAP_NAME_REGEX.match(name) or DOOM2_MAP_NAME_REGEX.match(name))
        if is_marker:
            in_map = True
        elif name in map_data_names:
            if not in_map:
                issues.append(
                    ValidationIssue(
                        Severity.WARNING,
                        name,
                        f"map data lump '{name}' appears outside a map block",
                    )
                )
        else:
            in_map = False

    return issues
