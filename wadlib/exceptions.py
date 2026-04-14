class BaseWadException(Exception):
    pass


class WadFormatError(BaseWadException):
    """Raised when a WAD file is structurally malformed."""

    pass


class BadHeaderWadException(WadFormatError):
    """Raised when the WAD magic bytes are not 'IWAD' or 'PWAD'."""

    pass


class TruncatedWadError(WadFormatError):
    """Raised when a WAD file is shorter than its header or directory require."""

    pass


class InvalidDirectoryError(WadFormatError):
    """Raised when a WAD directory entry references data outside the file."""

    pass
