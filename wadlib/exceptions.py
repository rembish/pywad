class BaseWadException(Exception):
    """Base class for all wadlib exceptions."""


class WadFormatError(BaseWadException):
    """Raised when a WAD file is structurally malformed."""


class BadHeaderWadException(WadFormatError):
    """Raised when the WAD magic bytes are not 'IWAD' or 'PWAD'."""


class TruncatedWadError(WadFormatError):
    """Raised when a WAD file is shorter than its header or directory require."""


class InvalidDirectoryError(WadFormatError):
    """Raised when a WAD directory entry references data outside the file."""


class CorruptLumpError(WadFormatError):
    """Raised when a lump's binary payload is internally malformed.

    Examples: truncated picture column data, bad flat size, palette read failure.
    """
