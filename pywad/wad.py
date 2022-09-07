from struct import unpack, calcsize

from .enums import WadType
from .exceptions import BadHeaderWadException


class WadFile:
    def __init__(self, filename):
        self.fd = open(filename, "rb")

        header_format = "<4sII"
        magic, self.number_of_lumps, self.directory_offset = \
            unpack(header_format, self.fd.read(calcsize(header_format)))
        magic = magic.decode("ascii")
        if magic not in ("IWAD", "PWAD"):
            raise BadHeaderWadException(magic)

        self.wad_type = WadType[magic]

    def close(self):
        if not self.fd.closed:
            self.fd.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
