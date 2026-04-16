"""Strife DIALOGUE lump parser — NPC dialogue pages and player choices.

In vanilla Strife, per-map NPC dialogue data is stored in a WAD lump named
``DIALOGUE`` (the ``CONVERSATION`` label used in ZDoom documentation refers
to the same binary format, but ``DIALOGUE`` is the actual 8-character lump
name used in ``STRIFE1.WAD``).

The lump contains a flat array of ``mapdialog_t`` records, each 1 516 bytes
long.  Every record describes one NPC dialogue page: the speaker, associated
sprite, background picture, displayed text, and up to five response choices.

This parser extracts the binary data into frozen dataclasses.  No runtime
dialogue logic (quest tracking, branch jumps, NPC AI) is emulated.

Binary layout (little-endian), per Chocolate Strife ``src/strife/p_dialog.h``:

Page header (376 bytes):
  - speakerid    i32   — thing type of the NPC speaker
  - dropitem     i32   — thing type dropped on death (0 = nothing)
  - checkitem[3] 3xi32 — thing types required in inventory (0 = unused)
  - jumptoconv   i32   — 1-based page index to jump to (0 = none)
  - name         16 B  — NPC display name, null-padded
  - voice        8 B   — audio lump name, null-padded (empty = silent)
  - backpic      8 B   — background flat/picture lump name
  - text         320 B — dialogue text shown on screen

5 x choice record (228 bytes each):
  - giveitem       i32   — thing type given on success (0 = nothing)
  - needitems[3]   3xi32 — required inventory item types (0 = unused)
  - needamounts[3] 3xi32 — required item counts
  - text           32 B  — choice button label shown to the player
  - textok         80 B  — response text displayed on success
  - next           i32   — next page index (0 = end conversation, -1 = close)
  - objective      i32   — log objective page index (0 = none)
  - textno         80 B  — response text displayed on failure

References:
  - Chocolate Strife source: ``src/strife/p_dialog.h``
  - https://doomwiki.org/wiki/CONVERSATION

Usage::

    from wadlib.lumps.strife_conversation import parse_conversation

    with open("DIALOGUE.lmp", "rb") as f:
        pages = parse_conversation(f.read())
    print(f"{len(pages)} dialogue pages")
    for page in pages[:3]:
        print(page.name, "->", [c.text for c in page.choices if c.text])

    # Via WadFile convenience property:
    with WadFile("STRIFE1.WAD") as wad:
        lump = wad.dialogue  # ConversationLump | None
        if lump:
            print(len(lump.pages), "pages in base WAD")
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from ..exceptions import CorruptLumpError
from .base import BaseLump

# ---------------------------------------------------------------------------
# Layout constants (from p_dialog.h)
# ---------------------------------------------------------------------------

_CHOICE_SIZE = 228
_PAGE_HEADER_SIZE = 376
_PAGE_SIZE = _PAGE_HEADER_SIZE + 5 * _CHOICE_SIZE  # 1 516

# struct format strings — no padding inserted (all fields explicitly sized)
# Page header: speakerid, dropitem, checkitemx3, jumptoconv, name, voice, backpic, text
_PAGE_HEADER_FMT = "<ii3ii16s8s8s320s"
# Choice: giveitem, needitemsx3, needamountsx3, text, textok, next, objective, textno
_CHOICE_FMT = "<i3i3i32s80sii80s"

assert struct.calcsize(_PAGE_HEADER_FMT) == _PAGE_HEADER_SIZE
assert struct.calcsize(_CHOICE_FMT) == _CHOICE_SIZE


def _decode(buf: bytes) -> str:
    """Decode a null-padded fixed-width byte field to str (latin-1)."""
    end = buf.find(b"\x00")
    return buf[:end].decode("latin-1") if end != -1 else buf.decode("latin-1")


def _encode(s: str, size: int) -> bytes:
    """Encode *s* to a null-padded fixed-width latin-1 byte field of *size* bytes."""
    encoded = s.encode("latin-1")[:size]
    return encoded.ljust(size, b"\x00")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConversationChoice:
    """One of up to five player-response options within a dialogue page.

    A choice with an empty ``text`` field is unused and can be ignored.

    Attributes:
        give_item:    Thing type given to the player on a successful exchange
                      (0 = nothing).
        need_items:   Up to three inventory item types required (0 = unused).
        need_amounts: Corresponding quantities required for each *need_items*
                      slot.
        text:         Short button label shown in the choice menu.
        text_ok:      Response text displayed when all requirements are met.
        next:         Next page index after accepting (0 = end conversation,
                      -1 = close immediately).
        objective:    Objective log page index (0 = none).
        text_no:      Response text displayed when requirements are not met.
    """

    give_item: int
    need_items: tuple[int, int, int]
    need_amounts: tuple[int, int, int]
    text: str
    text_ok: str
    next: int
    objective: int
    text_no: str

    def to_bytes(self) -> bytes:
        """Serialize this choice back to its 228-byte binary representation."""
        return struct.pack(
            _CHOICE_FMT,
            self.give_item,
            *self.need_items,
            *self.need_amounts,
            _encode(self.text, 32),
            _encode(self.text_ok, 80),
            self.next,
            self.objective,
            _encode(self.text_no, 80),
        )


@dataclass(frozen=True)
class ConversationPage:
    """One dialogue page (``mapdialog_t``) from a CONVERSATION lump.

    Each page represents the full state of an NPC dialogue screen: who is
    speaking, what they say, what background image to show, and the set of
    response choices available to the player.

    Attributes:
        speaker_id:  Thing type of the NPC speaker (matches the thing catalog).
        drop_item:   Thing type dropped when the NPC dies (0 = nothing).
        check_items: Up to three inventory items required to start this
                     dialogue branch (0 = unused slot).
        jump_to:     1-based index of the page to jump to before displaying
                     this page's text (0 = show this page directly).
        name:        Display name of the NPC shown in the dialogue UI.
        voice:       Name of the audio lump to play (empty string = silent).
        back_pic:    Name of the background flat or picture lump.
        text:        Dialogue text shown on screen.
        choices:     Tuple of exactly five ``ConversationChoice`` objects; slots
                     with an empty ``text`` are unused padding.
    """

    speaker_id: int
    drop_item: int
    check_items: tuple[int, int, int]
    jump_to: int
    name: str
    voice: str
    back_pic: str
    text: str
    choices: tuple[
        ConversationChoice,
        ConversationChoice,
        ConversationChoice,
        ConversationChoice,
        ConversationChoice,
    ]

    def to_bytes(self) -> bytes:
        """Serialize this page back to its 1 516-byte binary representation."""
        header = struct.pack(
            _PAGE_HEADER_FMT,
            self.speaker_id,
            self.drop_item,
            *self.check_items,
            self.jump_to,
            _encode(self.name, 16),
            _encode(self.voice, 8),
            _encode(self.back_pic, 8),
            _encode(self.text, 320),
        )
        return header + b"".join(c.to_bytes() for c in self.choices)

    @property
    def active_choices(self) -> list[ConversationChoice]:
        """Return only the choices whose ``text`` field is non-empty."""
        return [c for c in self.choices if c.text]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_choice(data: bytes, offset: int) -> ConversationChoice:
    try:
        (
            give_item,
            ni0,
            ni1,
            ni2,
            na0,
            na1,
            na2,
            raw_text,
            raw_textok,
            next_page,
            objective,
            raw_textno,
        ) = struct.unpack_from(_CHOICE_FMT, data, offset)
    except struct.error as exc:
        raise CorruptLumpError(f"Truncated CONVERSATION choice at offset {offset}") from exc
    return ConversationChoice(
        give_item=give_item,
        need_items=(ni0, ni1, ni2),
        need_amounts=(na0, na1, na2),
        text=_decode(raw_text),
        text_ok=_decode(raw_textok),
        next=next_page,
        objective=objective,
        text_no=_decode(raw_textno),
    )


def _parse_page(data: bytes, offset: int) -> ConversationPage:
    try:
        (
            speaker_id,
            drop_item,
            ci0,
            ci1,
            ci2,
            jump_to,
            raw_name,
            raw_voice,
            raw_backpic,
            raw_text,
        ) = struct.unpack_from(_PAGE_HEADER_FMT, data, offset)
    except struct.error as exc:
        raise CorruptLumpError(f"Truncated CONVERSATION page at offset {offset}") from exc

    choice_offset = offset + _PAGE_HEADER_SIZE
    choices = tuple(_parse_choice(data, choice_offset + i * _CHOICE_SIZE) for i in range(5))
    return ConversationPage(
        speaker_id=speaker_id,
        drop_item=drop_item,
        check_items=(ci0, ci1, ci2),
        jump_to=jump_to,
        name=_decode(raw_name),
        voice=_decode(raw_voice),
        back_pic=_decode(raw_backpic),
        text=_decode(raw_text),
        choices=choices,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_conversation(data: bytes) -> list[ConversationPage]:
    """Parse raw CONVERSATION lump bytes into a list of dialogue pages.

    Args:
        data: Raw bytes from the CONVERSATION lump.

    Returns:
        A list of :class:`ConversationPage` objects, one per ``mapdialog_t``
        record, in lump order.

    Raises:
        :class:`~wadlib.exceptions.CorruptLumpError`: If the lump is not a
            multiple of 1 516 bytes, or if any record is structurally invalid.
    """
    if len(data) % _PAGE_SIZE != 0:
        raise CorruptLumpError(
            f"CONVERSATION lump size {len(data)} is not a multiple of {_PAGE_SIZE} bytes"
        )
    count = len(data) // _PAGE_SIZE
    return [_parse_page(data, i * _PAGE_SIZE) for i in range(count)]


def conversation_to_bytes(pages: list[ConversationPage]) -> bytes:
    """Serialize a list of dialogue pages to raw CONVERSATION lump bytes.

    This is the inverse of :func:`parse_conversation`.  The returned bytes can
    be written directly to a ``DIALOGUE`` lump in a WAD file.

    Args:
        pages: A list of :class:`ConversationPage` objects.

    Returns:
        Raw bytes suitable for a CONVERSATION lump (``len(pages) * 1516``
        bytes).
    """
    return b"".join(p.to_bytes() for p in pages)


class ConversationLump(BaseLump[Any]):
    """A CONVERSATION lump containing Strife NPC dialogue pages."""

    @cached_property
    def pages(self) -> list[ConversationPage]:
        """All dialogue pages parsed from this lump."""
        return parse_conversation(self.raw())

    def to_bytes(self) -> bytes:
        """Serialize the parsed pages back to raw CONVERSATION lump bytes."""
        return conversation_to_bytes(self.pages)

    def __len__(self) -> int:
        return len(self.pages)
