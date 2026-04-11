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


def build_endoom(text: str, fg: int = 7, bg: int = 0) -> bytes:
    """Build an ENDOOM lump from plain text.

    Parameters:
        text:  Up to 25 lines of up to 80 characters each.
        fg:    Default foreground CGA colour (0-15, default 7 = light grey).
        bg:    Default background CGA colour (0-7, default 0 = black).

    Returns:
        4000 bytes (80x25x2) suitable for an ENDOOM lump.

    CGA colours: 0=black 1=blue 2=green 3=cyan 4=red 5=magenta 6=brown
    7=light grey 8=dark grey 9=light blue 10=light green 11=light cyan
    12=light red 13=light magenta 14=yellow 15=white.

    Example::

        from wadlib.lumps.endoom import build_endoom

        endoom = build_endoom("Hello, Doom World!\\nGoodbye.", fg=14, bg=1)
    """
    attr = (bg & 0x07) << 4 | (fg & 0x0F)
    data = bytearray(_ENDOOM_SIZE)
    lines = text.splitlines()

    for row in range(_ROWS):
        line = lines[row] if row < len(lines) else ""
        for col in range(_COLS):
            idx = (row * _COLS + col) * _CELL_SIZE
            char = ord(line[col]) if col < len(line) else 0x20
            data[idx] = char & 0xFF
            data[idx + 1] = attr

    return bytes(data)


def build_endoom_ansi(cells: list[list[tuple[str, int, int]]]) -> bytes:
    """Build an ENDOOM lump from per-cell character + colour data.

    Parameters:
        cells:  25 rows of 80 ``(char, fg, bg)`` tuples.

    Example::

        cells = [[(" ", 7, 0)] * 80 for _ in range(25)]
        cells[12][35] = ("H", 15, 4)  # bright white on red
        endoom = build_endoom_ansi(cells)
    """
    data = bytearray(_ENDOOM_SIZE)

    for row in range(_ROWS):
        row_data = cells[row] if row < len(cells) else []
        for col in range(_COLS):
            idx = (row * _COLS + col) * _CELL_SIZE
            if col < len(row_data):
                char, fg, bg = row_data[col]
                data[idx] = ord(char[0]) if char else 0x20
                data[idx + 1] = (bg & 0x07) << 4 | (fg & 0x0F)
            else:
                data[idx] = 0x20
                data[idx + 1] = 0x07

    return bytes(data)
