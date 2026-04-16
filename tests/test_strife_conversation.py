"""Tests for the Strife CONVERSATION lump parser.

Vanilla Strife stores dialogue data in a per-map lump named ``DIALOGUE``
(8 chars, fits the WAD directory format).  All tests use synthetic binary
fixtures; no STRIFE1.WAD is required.
"""

from __future__ import annotations

import os
import struct
import tempfile

import pytest

from wadlib.exceptions import CorruptLumpError
from wadlib.lumps.strife_conversation import (
    _CHOICE_FMT,
    _CHOICE_SIZE,
    _PAGE_HEADER_FMT,
    _PAGE_SIZE,
    ConversationChoice,
    ConversationLump,
    ConversationPage,
    conversation_to_bytes,
    parse_conversation,
)
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Helpers — build synthetic CONVERSATION binary data
# ---------------------------------------------------------------------------


def _pack_choice(
    *,
    give_item: int = 0,
    need_items: tuple[int, int, int] = (0, 0, 0),
    need_amounts: tuple[int, int, int] = (0, 0, 0),
    text: bytes = b"",
    text_ok: bytes = b"",
    next_page: int = 0,
    objective: int = 0,
    text_no: bytes = b"",
) -> bytes:
    raw = struct.pack(
        _CHOICE_FMT,
        give_item,
        *need_items,
        *need_amounts,
        text.ljust(32, b"\x00")[:32],
        text_ok.ljust(80, b"\x00")[:80],
        next_page,
        objective,
        text_no.ljust(80, b"\x00")[:80],
    )
    assert len(raw) == _CHOICE_SIZE
    return raw


def _pack_page(
    *,
    speaker_id: int = 0,
    drop_item: int = 0,
    check_items: tuple[int, int, int] = (0, 0, 0),
    jump_to: int = 0,
    name: bytes = b"",
    voice: bytes = b"",
    back_pic: bytes = b"",
    text: bytes = b"",
    choices: list[bytes] | None = None,
) -> bytes:
    header = struct.pack(
        _PAGE_HEADER_FMT,
        speaker_id,
        drop_item,
        *check_items,
        jump_to,
        name.ljust(16, b"\x00")[:16],
        voice.ljust(8, b"\x00")[:8],
        back_pic.ljust(8, b"\x00")[:8],
        text.ljust(320, b"\x00")[:320],
    )
    if choices is None:
        choices = []
    # Pad to exactly 5 choices with blank entries
    while len(choices) < 5:
        choices.append(_pack_choice())
    raw = header + b"".join(choices[:5])
    assert len(raw) == _PAGE_SIZE
    return raw


def _make_wad_with_lump(lump_name: bytes, lump_data: bytes) -> str:
    """Write a minimal PWAD with one named lump; return the temp file path."""
    data_start = 12
    dir_offset = data_start + len(lump_data)
    wad_bytes = (
        struct.pack("<4sII", b"PWAD", 1, dir_offset)
        + lump_data
        + struct.pack("<II8s", data_start, len(lump_data), lump_name.ljust(8, b"\x00")[:8])
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wad") as f:
        f.write(wad_bytes)
        return f.name


# ---------------------------------------------------------------------------
# parse_conversation — basic structural tests
# ---------------------------------------------------------------------------


def test_empty_lump_returns_empty_list() -> None:
    assert parse_conversation(b"") == []


def test_single_page_count() -> None:
    pages = parse_conversation(_pack_page())
    assert len(pages) == 1


def test_multiple_pages_count() -> None:
    pages = parse_conversation(_pack_page() * 3)
    assert len(pages) == 3


def test_size_not_multiple_raises_corrupt() -> None:
    data = _pack_page() + b"\x00" * 10  # 1 516 + 10 — not aligned
    with pytest.raises(CorruptLumpError, match="not a multiple"):
        parse_conversation(data)


def test_returns_conversation_page_instances() -> None:
    pages = parse_conversation(_pack_page())
    assert isinstance(pages[0], ConversationPage)


# ---------------------------------------------------------------------------
# Field decoding — page header
# ---------------------------------------------------------------------------


def test_speaker_id_decoded() -> None:
    assert parse_conversation(_pack_page(speaker_id=142))[0].speaker_id == 142


def test_drop_item_decoded() -> None:
    assert parse_conversation(_pack_page(drop_item=57))[0].drop_item == 57


def test_check_items_decoded() -> None:
    page = parse_conversation(_pack_page(check_items=(10, 20, 30)))[0]
    assert page.check_items == (10, 20, 30)


def test_jump_to_decoded() -> None:
    assert parse_conversation(_pack_page(jump_to=3))[0].jump_to == 3


def test_name_decoded_without_null_padding() -> None:
    page = parse_conversation(_pack_page(name=b"BlackSmith\x00\x00\x00\x00\x00\x00"))[0]
    assert page.name == "BlackSmith"


def test_voice_decoded() -> None:
    assert parse_conversation(_pack_page(voice=b"VOCA1\x00\x00\x00"))[0].voice == "VOCA1"


def test_back_pic_decoded() -> None:
    assert parse_conversation(_pack_page(back_pic=b"BGRND1\x00\x00"))[0].back_pic == "BGRND1"


def test_dialogue_text_decoded() -> None:
    long_text = b"Hello, stranger. What brings you to this place?" + b"\x00" * 273
    page = parse_conversation(_pack_page(text=long_text))[0]
    assert page.text.startswith("Hello, stranger.")


def test_empty_name_is_empty_string() -> None:
    assert parse_conversation(_pack_page(name=b""))[0].name == ""


def test_empty_voice_is_empty_string() -> None:
    assert parse_conversation(_pack_page(voice=b""))[0].voice == ""


# ---------------------------------------------------------------------------
# Field decoding — choices
# ---------------------------------------------------------------------------


def test_choices_tuple_has_five_elements() -> None:
    page = parse_conversation(_pack_page())[0]
    assert len(page.choices) == 5


def test_choice_give_item_decoded() -> None:
    choice = _pack_choice(give_item=99)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].give_item == 99


def test_choice_need_items_decoded() -> None:
    choice = _pack_choice(need_items=(5, 10, 15))
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].need_items == (5, 10, 15)


def test_choice_need_amounts_decoded() -> None:
    choice = _pack_choice(need_amounts=(1, 2, 3))
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].need_amounts == (1, 2, 3)


def test_choice_text_decoded_without_null() -> None:
    choice = _pack_choice(text=b"Buy sword\x00" + b"\x00" * 22)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].text == "Buy sword"


def test_choice_text_ok_decoded() -> None:
    choice = _pack_choice(text_ok=b"Here you go!\x00" + b"\x00" * 67)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].text_ok == "Here you go!"


def test_choice_text_no_decoded() -> None:
    choice = _pack_choice(text_no=b"Not enough gold.\x00" + b"\x00" * 63)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].text_no == "Not enough gold."


def test_choice_next_decoded() -> None:
    choice = _pack_choice(next_page=7)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].next == 7


def test_choice_next_minus_one_means_close() -> None:
    """next == -1 means close conversation immediately."""
    choice = _pack_choice(next_page=-1)
    assert parse_conversation(_pack_page(choices=[choice]))[0].choices[0].next == -1


def test_choice_objective_decoded() -> None:
    choice = _pack_choice(objective=4)
    page = parse_conversation(_pack_page(choices=[choice]))[0]
    assert page.choices[0].objective == 4


def test_choice_instances_are_conversation_choice() -> None:
    for choice in parse_conversation(_pack_page())[0].choices:
        assert isinstance(choice, ConversationChoice)


# ---------------------------------------------------------------------------
# active_choices property
# ---------------------------------------------------------------------------


def test_active_choices_empty_when_all_blank() -> None:
    # All five choices have empty text — all are unused slots
    assert parse_conversation(_pack_page())[0].active_choices == []


def test_active_choices_filters_blank_slots() -> None:
    c1 = _pack_choice(text=b"Trade\x00" + b"\x00" * 26)
    c2 = _pack_choice(text=b"Ask about map\x00" + b"\x00" * 18)
    page = parse_conversation(_pack_page(choices=[c1, c2]))[0]
    assert len(page.active_choices) == 2
    assert page.active_choices[0].text == "Trade"
    assert page.active_choices[1].text == "Ask about map"


def test_active_choices_all_five_non_empty() -> None:
    choices = [
        _pack_choice(text=f"Option {i}\x00".encode() + b"\x00" * (22 - len(f"Option {i}")))
        for i in range(5)
    ]
    page = parse_conversation(_pack_page(choices=choices))[0]
    assert len(page.active_choices) == 5


# ---------------------------------------------------------------------------
# Multiple pages — ordering
# ---------------------------------------------------------------------------


def test_pages_returned_in_lump_order() -> None:
    page1 = _pack_page(speaker_id=10)
    page2 = _pack_page(speaker_id=20)
    page3 = _pack_page(speaker_id=30)
    pages = parse_conversation(page1 + page2 + page3)
    assert [p.speaker_id for p in pages] == [10, 20, 30]


def test_check_items_zero_unused_slots() -> None:
    """Unused check_item slots are stored as 0."""
    page = parse_conversation(_pack_page(check_items=(42, 0, 0)))[0]
    assert page.check_items[0] == 42
    assert page.check_items[1] == 0
    assert page.check_items[2] == 0


# ---------------------------------------------------------------------------
# ConversationLump wrapper (via WadFile + DirectoryEntry)
# ---------------------------------------------------------------------------


def test_conversation_lump_pages_property() -> None:
    """ConversationLump.pages returns parsed ConversationPage objects."""
    from wadlib.wad import WadFile

    raw_lump = _pack_page(speaker_id=42) + _pack_page(speaker_id=99)
    path = _make_wad_with_lump(b"DIALOGUE", raw_lump)

    with WadFile(path) as wad:
        entry = wad.directory[0]
        lump = ConversationLump(entry)
        assert len(lump.pages) == 2
        assert lump.pages[0].speaker_id == 42
        assert lump.pages[1].speaker_id == 99


def test_conversation_lump_len() -> None:
    """ConversationLump.__len__ returns the page count."""
    from wadlib.wad import WadFile

    raw_lump = _pack_page() * 4
    path = _make_wad_with_lump(b"DIALOGUE", raw_lump)

    with WadFile(path) as wad:
        entry = wad.directory[0]
        lump = ConversationLump(entry)
        assert len(lump) == 4


def test_conversation_lump_registry_lookup() -> None:
    """LUMP_REGISTRY.find_and_decode('DIALOGUE') returns a ConversationLump."""
    from wadlib.registry import LUMP_REGISTRY
    from wadlib.wad import WadFile

    raw_lump = _pack_page(speaker_id=7)
    path = _make_wad_with_lump(b"DIALOGUE", raw_lump)

    with WadFile(path) as wad:
        lump = LUMP_REGISTRY.find_and_decode("DIALOGUE", wad)
        assert isinstance(lump, ConversationLump)
        assert lump.pages[0].speaker_id == 7


# ---------------------------------------------------------------------------
# Error handling — CorruptLumpError paths
# ---------------------------------------------------------------------------


def test_corrupt_size_one_byte_off() -> None:
    data = _pack_page()[:-1]  # one byte short of a full page
    with pytest.raises(CorruptLumpError):
        parse_conversation(data)


def test_corrupt_size_extra_bytes() -> None:
    data = _pack_page() + b"\xff"  # one extra byte
    with pytest.raises(CorruptLumpError):
        parse_conversation(data)


def test_corrupt_size_half_page() -> None:
    data = _pack_page()[:758]  # half of _PAGE_SIZE — wrong multiple
    with pytest.raises(CorruptLumpError):
        parse_conversation(data)


# ---------------------------------------------------------------------------
# Serialization — to_bytes() and conversation_to_bytes() (Finding #4)
# ---------------------------------------------------------------------------


def test_choice_to_bytes_size() -> None:
    """ConversationChoice.to_bytes() must produce exactly 228 bytes."""
    pages = parse_conversation(_pack_page())
    choice = pages[0].choices[0]
    assert len(choice.to_bytes()) == _CHOICE_SIZE


def test_page_to_bytes_size() -> None:
    """ConversationPage.to_bytes() must produce exactly 1 516 bytes."""
    pages = parse_conversation(_pack_page())
    assert len(pages[0].to_bytes()) == _PAGE_SIZE


def test_page_to_bytes_round_trip_speaker_id() -> None:
    """parse → to_bytes → re-parse must preserve speaker_id."""
    original = parse_conversation(_pack_page(speaker_id=99))[0]
    restored = parse_conversation(original.to_bytes())[0]
    assert restored.speaker_id == 99


def test_page_to_bytes_round_trip_strings() -> None:
    """parse → to_bytes → re-parse must preserve text string fields."""
    raw = _pack_page(
        name=b"Guard",
        voice=b"VGUARD1",
        back_pic=b"BCKGRD1",
        text=b"Halt! Who goes there?",
    )
    original = parse_conversation(raw)[0]
    restored = parse_conversation(original.to_bytes())[0]
    assert restored.name == original.name
    assert restored.voice == original.voice
    assert restored.back_pic == original.back_pic
    assert restored.text == original.text


def test_choice_to_bytes_round_trip() -> None:
    """parse → to_bytes → re-parse must preserve all choice fields."""
    choice_raw = _pack_choice(
        give_item=5,
        need_items=(1, 2, 3),
        need_amounts=(10, 20, 30),
        text=b"Yes",
        text_ok=b"Here you go!",
        next_page=2,
        objective=1,
        text_no=b"You need more.",
    )
    raw = _pack_page(choices=[choice_raw])
    pages = parse_conversation(raw)
    original = pages[0].choices[0]
    # Serialize the whole page back to bytes, re-parse, and inspect the choice.
    restored = parse_conversation(pages[0].to_bytes())[0].choices[0]
    assert restored.give_item == original.give_item
    assert restored.need_items == original.need_items
    assert restored.need_amounts == original.need_amounts
    assert restored.text == original.text
    assert restored.text_ok == original.text_ok
    assert restored.next == original.next
    assert restored.objective == original.objective
    assert restored.text_no == original.text_no


def test_conversation_to_bytes_length() -> None:
    """conversation_to_bytes() returns len(pages) * _PAGE_SIZE bytes."""
    raw = _pack_page(speaker_id=1) + _pack_page(speaker_id=2) + _pack_page(speaker_id=3)
    pages = parse_conversation(raw)
    result = conversation_to_bytes(pages)
    assert len(result) == 3 * _PAGE_SIZE


def test_conversation_to_bytes_round_trip() -> None:
    """conversation_to_bytes is the inverse of parse_conversation."""
    raw = _pack_page(speaker_id=10) + _pack_page(speaker_id=20)
    pages = parse_conversation(raw)
    restored = parse_conversation(conversation_to_bytes(pages))
    assert [p.speaker_id for p in restored] == [10, 20]


def test_conversation_lump_to_bytes() -> None:
    """ConversationLump.to_bytes() serializes the lump pages back to bytes."""
    raw_lump = _pack_page(speaker_id=7) + _pack_page(speaker_id=13)
    path = _make_wad_with_lump(b"DIALOGUE", raw_lump)
    try:
        with WadFile(path) as wad:
            entry = wad.directory[0]
            lump = ConversationLump(entry)
            result = lump.to_bytes()
        assert len(result) == 2 * _PAGE_SIZE
        restored = parse_conversation(result)
        assert restored[0].speaker_id == 7
        assert restored[1].speaker_id == 13
    finally:
        os.unlink(path)
