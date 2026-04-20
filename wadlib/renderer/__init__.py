"""wadlib.renderer — map rendering package.

Re-exports the public API so that ``from wadlib.renderer import MapRenderer``
continues to work after the single-file module was split into a package.
"""

from .ascii import AsciiMapRenderer as AsciiMapRenderer
from .core import MapRenderer as MapRenderer
from .core import RenderOptions as RenderOptions
from .geometry import _clip_poly as _clip_poly
