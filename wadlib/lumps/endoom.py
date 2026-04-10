"""ENDOOM lump decoder — 80x25 CGA text screen shown on exit."""

from __future__ import annotations

from typing import Any, ClassVar

from .base import BaseLump

_COLS: int = 80
_ROWS: int = 25
_CELL_SIZE: int = 2
_ENDOOM_SIZE: int = _COLS * _ROWS * _CELL_SIZE

_CGA_TO_ANSI: list[int] = [0, 4, 2, 6, 1, 5, 3, 7]


class Endoom(BaseLump[Any]):
    """The ENDOOM lump — a 80x25 CGA text screen."""

    _CGA_TO_ANSI: ClassVar[list[int]] = _CGA_TO_ANSI

    def to_text(self) -> str:
        """Return the screen as 25 plain-text lines (no attributes)."""
        data = self.raw()
        lines = []
        for row in range(_ROWS):
            chars = []
            for col in range(_COLS):
                idx = (row * _COLS + col) * _CELL_SIZE
                chars.append(chr(data[idx]))
            lines.append("".join(chars).rstrip())
        return "\n".join(lines)

    def to_ansi(self) -> str:
        """Return the screen rendered with ANSI escape codes for color."""
        data = self.raw()
        parts = []
        for row in range(_ROWS):
            for col in range(_COLS):
                idx = (row * _COLS + col) * _CELL_SIZE
                char = chr(data[idx])
                attr = data[idx + 1]
                fg = attr & 0x0F
                bg = (attr >> 4) & 0x07
                bold = 1 if fg >= 8 else 0
                fg_ansi = 30 + _CGA_TO_ANSI[fg & 7]
                bg_ansi = 40 + _CGA_TO_ANSI[bg]
                parts.append(f"\x1b[{bold};{fg_ansi};{bg_ansi}m{char}")
            parts.append("\n")
        parts.append("\x1b[0m")
        return "".join(parts)
