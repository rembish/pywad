from .analysis import DiagnosticItem, ValidationReport, analyze
from .archive import LumpInfo, WadArchive
from .exceptions import (
    BadHeaderWadException,
    CorruptLumpError,
    InvalidDirectoryError,
    TruncatedWadError,
    WadFormatError,
)
from .lumps.boom import (
    DOOM_SECTOR_SPECIALS,
    MBF21_LINEDEF_FLAGS,
    GeneralizedCategory,
    GeneralizedLinedef,
    GeneralizedSpeed,
    GeneralizedTrigger,
    decode_generalized,
)
from .lumps.decorate import DecorateActor, DecorateLump, resolve_inheritance
from .lumps.strife_conversation import (
    ConversationChoice,
    ConversationLump,
    ConversationPage,
    parse_conversation,
)
from .lumps.udmf import UdmfParseError
from .lumps.zmapinfo import ZMapInfoCluster, ZMapInfoEntry, ZMapInfoEpisode
from .registry import LUMP_REGISTRY, DecoderRegistry
from .resolver import ResourceRef, ResourceResolver
from .source import LumpSource, MemoryLumpSource
from .validate import InvalidLumpError
from .wad import WadFile
from .writer import WadWriter

__all__ = [
    "DOOM_SECTOR_SPECIALS",
    "LUMP_REGISTRY",
    "MBF21_LINEDEF_FLAGS",
    "BadHeaderWadException",
    "ConversationChoice",
    "ConversationLump",
    "ConversationPage",
    "CorruptLumpError",
    "DecoderRegistry",
    "DecorateActor",
    "DecorateLump",
    "DiagnosticItem",
    "GeneralizedCategory",
    "GeneralizedLinedef",
    "GeneralizedSpeed",
    "GeneralizedTrigger",
    "InvalidDirectoryError",
    "InvalidLumpError",
    "LumpInfo",
    "LumpSource",
    "MemoryLumpSource",
    "ResourceRef",
    "ResourceResolver",
    "TruncatedWadError",
    "UdmfParseError",
    "ValidationReport",
    "WadArchive",
    "WadFile",
    "WadFormatError",
    "WadWriter",
    "ZMapInfoCluster",
    "ZMapInfoEntry",
    "ZMapInfoEpisode",
    "analyze",
    "decode_generalized",
    "parse_conversation",
    "resolve_inheritance",
]
