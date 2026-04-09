"""Backward-compatible MapExporter shim.

.. deprecated::
    Use :class:`wadlib.renderer.MapRenderer` instead.
    MapExporter will be removed in a future release.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from .renderer import MapRenderer, RenderOptions

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry


class MapExporter(MapRenderer):
    """Deprecated alias for :class:`wadlib.renderer.MapRenderer`.

    Pass ``scale=`` as a keyword argument; a value of 0 (default) auto-fits
    the map.  Call :meth:`process` then :meth:`save` / :meth:`show`.
    """

    def __init__(self, map_entry: BaseMapEntry, scale: float = 0.0) -> None:
        warnings.warn(
            "MapExporter is deprecated; use MapRenderer from wadlib.renderer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(map_entry, options=RenderOptions(scale=scale))

    def process(self) -> None:
        """Render linedefs and things (deprecated; use render() instead)."""
        self.render()
