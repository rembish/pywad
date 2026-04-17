from enum import Enum


class ExtendedEnum(Enum):
    """Base enum with a ``names()`` helper for member name lists."""

    @classmethod
    def names(cls) -> list[str]:
        """Return a list of all member names for this enum."""
        return cls._member_names_  # pylint: disable=no-member


class WadType(ExtendedEnum):
    """WAD file type: IWAD (base game data) or PWAD (patch/mod)."""

    IWAD = "Internal WAD"
    PWAD = "Patch WAD"


class MapData(ExtendedEnum):
    """Names of all recognized map sub-lumps (THINGS, LINEDEFS, etc.)."""
    THINGS = "Map Things"
    LINEDEFS = "Map Lines"
    SIDEDEFS = "Map Sides"
    VERTEXES = "Map Vertices"
    SEGS = "Map Segments"
    SSECTORS = "Map Subsectors"
    NODES = "Map Nodes"
    SECTORS = "Map Sectors"
    REJECT = "Map Reject Table"
    BLOCKMAP = "Map Blockmap"
    BEHAVIOR = "Map Compiled Script"
    ZNODES = "Map Extended BSP Nodes"
    TEXTMAP = "UDMF Map Text"
    ENDMAP = "UDMF Map End Marker"
