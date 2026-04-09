"""Texture compositor — blits patches onto a canvas to produce composite wall textures.

Usage::

    with WadFile("doom.wad") as wad:
        comp = TextureCompositor(wad)
        img = comp.compose("STARTAN3")   # returns PIL RGBA image
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image

from .lumps.playpal import Palette
from .lumps.textures import TextureDef

if TYPE_CHECKING:
    from .wad import WadFile


class TextureCompositor:
    """Composes TEXTURE1/TEXTURE2 definitions into PIL images by blitting patches.

    Args:
        wad:      open WadFile that contains PNAMES, TEXTURE1/TEXTURE2, and patch lumps.
        palette:  RGB palette to use for decoding patches.  If omitted, palette 0
                  from PLAYPAL is used.
    """

    def __init__(self, wad: WadFile, palette: Palette | None = None) -> None:
        self._wad = wad
        if palette is None:
            assert wad.playpal is not None, "WAD has no PLAYPAL lump"
            palette = wad.playpal.get_palette(0)
        self._palette = palette

        assert wad.pnames is not None, "WAD has no PNAMES lump"
        self._patch_names = wad.pnames.names

    def _get_texture_def(self, name: str) -> TextureDef | None:
        for tlist in (self._wad.texture1, self._wad.texture2):
            if tlist is not None:
                td = tlist.find(name)
                if td is not None:
                    return td
        return None

    def compose(self, name: str) -> Image.Image | None:
        """Compose texture *name* and return a PIL RGBA image, or None if unknown."""
        td = self._get_texture_def(name)
        if td is None:
            return None

        canvas = Image.new("RGBA", (td.width, td.height), (0, 0, 0, 255))

        for pd in td.patches:
            if pd.patch_index >= len(self._patch_names):
                continue
            patch_name = self._patch_names[pd.patch_index]
            pic = self._wad.get_picture(patch_name)
            if pic is None:
                continue
            patch_img = pic.decode(self._palette)
            canvas.paste(patch_img, (pd.origin_x, pd.origin_y), mask=patch_img)

        return canvas

    def compose_all(self) -> dict[str, Image.Image]:
        """Compose every texture in TEXTURE1 and TEXTURE2, return as name→image dict."""
        result: dict[str, Image.Image] = {}
        for tlist in (self._wad.texture1, self._wad.texture2):
            if tlist is None:
                continue
            for td in tlist.textures:
                img = self.compose(td.name)
                if img is not None:
                    result[td.name] = img
        return result
