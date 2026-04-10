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

from dataclasses import dataclass
from functools import cached_property
from struct import calcsize, unpack
from typing import Any

from .base import BaseLump

# Correct layout (per Doom source):
#   name[8], masked[4], width[2], height[2], columndirectory[4], patchcount[2]
_TEX_HDR_FMT = "<8sIHHIH"
_TEX_HDR_SIZE = calcsize(_TEX_HDR_FMT)

# Each patch descriptor in a texture:
#   originx[2], originy[2], patch[2], stepdir[2], colormap[2]
_PATCH_DESC_FMT = "<hhHhh"
_PATCH_DESC_SIZE = calcsize(_PATCH_DESC_FMT)


@dataclass
class PatchDescriptor:
    origin_x: int
    origin_y: int
    patch_index: int


@dataclass
class TextureDef:
    name: str
    width: int
    height: int
    patches: list[PatchDescriptor]


class PNames(BaseLump[Any]):
    """PNAMES lump — ordered list of patch names."""

    @cached_property
    def names(self) -> list[str]:
        """Return all patch names as a list of strings."""
        if not self.readable():
            return []
        assert self._size is not None
        self.seek(0)
        raw_count = self.read(4)
        assert raw_count is not None
        (count,) = unpack("<I", raw_count)
        result: list[str] = []
        for _ in range(count):
            raw = self.read(8)
            assert raw is not None
            result.append(raw.rstrip(b"\x00").decode("ascii", errors="replace"))
        return result

    def __len__(self) -> int:
        if not self.readable():
            return 0
        self.seek(0)
        raw = self.read(4)
        if raw is None:
            return 0
        (count,) = unpack("<I", raw)
        return int(count)


class TextureList(BaseLump[Any]):
    """TEXTURE1 or TEXTURE2 lump — list of composite texture definitions."""

    def _read_texture_at(self, offset: int) -> TextureDef:  # pylint: disable=too-many-locals
        self.seek(offset)
        hdr_raw = self.read(_TEX_HDR_SIZE)
        assert hdr_raw is not None
        name_raw, _masked, width, height, _coldir, patch_count = unpack(_TEX_HDR_FMT, hdr_raw)
        name = name_raw.rstrip(b"\x00").decode("ascii", errors="replace")
        patches: list[PatchDescriptor] = []
        for _ in range(patch_count):
            pd_raw = self.read(_PATCH_DESC_SIZE)
            assert pd_raw is not None
            ox, oy, pidx, _step, _cmap = unpack(_PATCH_DESC_FMT, pd_raw)
            patches.append(PatchDescriptor(int(ox), int(oy), int(pidx)))
        return TextureDef(name, int(width), int(height), patches)

    @cached_property
    def textures(self) -> list[TextureDef]:
        """Parse and return all texture definitions."""
        if not self.readable():
            return []
        assert self._size is not None

        self.seek(0)
        raw_count = self.read(4)
        assert raw_count is not None
        (count,) = unpack("<I", raw_count)

        raw_offsets = self.read(int(count) * 4)
        assert raw_offsets is not None
        offsets = list(unpack(f"<{int(count)}I", raw_offsets))

        return [self._read_texture_at(int(off)) for off in offsets]

    def __len__(self) -> int:
        if not self.readable():
            return 0
        self.seek(0)
        raw = self.read(4)
        if raw is None:
            return 0
        (count,) = unpack("<I", raw)
        return int(count)

    def find(self, name: str) -> TextureDef | None:
        """Look up a texture by name (case-insensitive), or return None."""
        name_upper = name.upper()
        for tex in self.textures:
            if tex.name.upper() == name_upper:
                return tex
        return None
