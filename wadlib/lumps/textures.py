"""PNAMES and TEXTURE1/TEXTURE2 lump readers.

Binary layout reference:

PNAMES:
  [4] num_patches (int32)
  repeated num_patches times:
    [8] patch_name (null-padded ASCII)

TEXTURE1 / TEXTURE2 (Doom format):
  [4]  num_textures (int32)
  repeated num_textures times:
    [4]  offset from start of lump (int32)
  at each offset:
    [8]  name (null-padded ASCII)
    [4]  masked (unused, int32)
    [2]  width (uint16)
    [2]  height (uint16)
    [4]  column_dir (unused, int32)
    [2]  patch_count (int16)
    repeated patch_count times:
      [2]  origin_x (int16)
      [2]  origin_y (int16)
      [2]  patch_index (int16)   -- index into PNAMES
      [2]  step_dir (unused)
      [2]  colormap (unused)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cached_property
from struct import calcsize, pack, unpack
from typing import Any

from ..exceptions import CorruptLumpError
from .base import BaseLump

# Correct layout (per Doom source):
#   name[8], masked[4], width[2], height[2], columndirectory[4], patchcount[2]
_TEX_HDR_FMT = "<8sIHHIH"
_TEX_HDR_SIZE = calcsize(_TEX_HDR_FMT)

# Each patch descriptor in a texture:
#   originx[2], originy[2], patch[2], stepdir[2], colormap[2]
_PATCH_DESC_FMT = "<hhHhh"
_PATCH_DESC_SIZE = calcsize(_PATCH_DESC_FMT)


def _encode_name8(name: str) -> bytes:
    """Encode a name to 8-byte null-padded ASCII."""
    return name.encode("ascii")[:8].ljust(8, b"\x00")


@dataclass
class PatchDescriptor:
    """A single patch reference within a TEXTUREx entry (origin + patch index)."""

    origin_x: int
    origin_y: int
    patch_index: int

    def to_bytes(self) -> bytes:
        """Serialize this patch descriptor to its binary form."""
        return pack(_PATCH_DESC_FMT, self.origin_x, self.origin_y, self.patch_index, 0, 0)


@dataclass
class TextureDef:
    """A composite texture definition from TEXTURE1 or TEXTURE2."""

    name: str
    width: int
    height: int
    patches: list[PatchDescriptor]

    def to_bytes(self) -> bytes:
        """Serialize this texture definition (header + patch descriptors)."""
        hdr = pack(
            _TEX_HDR_FMT,
            _encode_name8(self.name),
            0,  # masked (unused)
            self.width,
            self.height,
            0,  # columndirectory (unused)
            len(self.patches),
        )
        return hdr + b"".join(p.to_bytes() for p in self.patches)


class PNames(BaseLump[Any]):
    """PNAMES lump — ordered list of patch names."""

    @cached_property
    def names(self) -> list[str]:
        """Return all patch names as a list of strings."""
        if not self.readable():
            return []
        try:
            self.seek(0)
            (count,) = unpack("<I", self.read(4) or b"")
            result: list[str] = []
            for _ in range(count):
                raw = self.read(8) or b""
                result.append(raw.rstrip(b"\x00").decode("ascii", errors="replace"))
            return result
        except (struct.error, EOFError) as exc:
            raise CorruptLumpError(f"{self.name!r}: truncated PNAMES data") from exc

    def __len__(self) -> int:
        if not self.readable():
            return 0
        try:
            self.seek(0)
            (count,) = unpack("<I", self.read(4) or b"")
            return int(count)
        except (struct.error, EOFError):
            return 0


class TextureList(BaseLump[Any]):
    """TEXTURE1 or TEXTURE2 lump — list of composite texture definitions."""

    def _read_texture_at(self, offset: int) -> TextureDef:  # pylint: disable=too-many-locals
        try:
            self.seek(offset)
            hdr_raw = self.read(_TEX_HDR_SIZE) or b""
            name_raw, _masked, width, height, _coldir, patch_count = unpack(_TEX_HDR_FMT, hdr_raw)
            name = name_raw.rstrip(b"\x00").decode("ascii", errors="replace")
            patches: list[PatchDescriptor] = []
            for _ in range(patch_count):
                pd_raw = self.read(_PATCH_DESC_SIZE) or b""
                ox, oy, pidx, _step, _cmap = unpack(_PATCH_DESC_FMT, pd_raw)
                patches.append(PatchDescriptor(int(ox), int(oy), int(pidx)))
            return TextureDef(name, int(width), int(height), patches)
        except (struct.error, EOFError) as exc:
            raise CorruptLumpError(f"{self.name!r}: corrupt texture at offset {offset}") from exc

    @cached_property
    def textures(self) -> list[TextureDef]:
        """Parse and return all texture definitions."""
        if not self.readable():
            return []
        try:
            self.seek(0)
            (count,) = unpack("<I", self.read(4) or b"")
            offsets = list(unpack(f"<{int(count)}I", self.read(int(count) * 4) or b""))
        except (struct.error, EOFError) as exc:
            raise CorruptLumpError(f"{self.name!r}: truncated texture lump") from exc
        return [self._read_texture_at(int(off)) for off in offsets]

    def __len__(self) -> int:
        if not self.readable():
            return 0
        try:
            self.seek(0)
            (count,) = unpack("<I", self.read(4) or b"")
            return int(count)
        except (struct.error, EOFError):
            return 0

    def find(self, name: str) -> TextureDef | None:
        """Look up a texture by name (case-insensitive), or return None."""
        name_upper = name.upper()
        for tex in self.textures:
            if tex.name.upper() == name_upper:
                return tex
        return None


def pnames_to_bytes(names: list[str]) -> bytes:
    """Serialize a list of patch names to PNAMES lump bytes."""
    buf = pack("<I", len(names))
    for name in names:
        buf += _encode_name8(name)
    return buf


def texturelist_to_bytes(textures: list[TextureDef]) -> bytes:
    """Serialize a list of TextureDefs to a TEXTURE1/TEXTURE2 lump."""
    count = len(textures)
    # First: count (4 bytes) + offset table (count x 4 bytes)
    header_size = 4 + count * 4
    # Serialize each texture definition
    tex_blobs = [t.to_bytes() for t in textures]
    # Compute offsets (relative to start of lump)
    offsets: list[int] = []
    pos = header_size
    for blob in tex_blobs:
        offsets.append(pos)
        pos += len(blob)
    buf = pack("<I", count)
    buf += pack(f"<{count}I", *offsets)
    buf += b"".join(tex_blobs)
    return buf
