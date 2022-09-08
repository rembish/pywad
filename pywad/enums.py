from enum import Enum


class ExtendedEnum(Enum):
    @classmethod
    def names(cls):
        return cls._member_names_


class WadType(ExtendedEnum):
    IWAD = "Internal WAD"
    PWAD = "Patch WAD"


class MapData(ExtendedEnum):
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
