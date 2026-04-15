"""Tests for the SNDSEQ lump parser."""

from __future__ import annotations

import struct
import tempfile

from wadlib.lumps.sndseq import SndSeq, SndSeqCommand, serialize_sndseq
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# serialize_sndseq — unit tests, no WAD needed
# ---------------------------------------------------------------------------


def test_serialize_sndseq_basic() -> None:
    seq = SndSeq(name="DoorOpen", commands=[SndSeqCommand("playuntildone", "DoorOpen", None)])
    text = serialize_sndseq([seq])
    assert ":DoorOpen" in text
    assert "playuntildone DoorOpen" in text
    assert "end" in text


def test_serialize_sndseq_with_tics() -> None:
    seq = SndSeq(
        name="Platform",
        commands=[
            SndSeqCommand("playrepeat", "PlatMove", None),
            SndSeqCommand("delay", None, 4),
        ],
    )
    text = serialize_sndseq([seq])
    assert "playrepeat PlatMove" in text
    assert "delay 4" in text


def test_serialize_sndseq_multiple() -> None:
    seqs = [
        SndSeq("A", [SndSeqCommand("stopsound", None, None)]),
        SndSeq("B", [SndSeqCommand("playuntildone", "SomeSound", None)]),
    ]
    text = serialize_sndseq(seqs)
    assert ":A" in text
    assert ":B" in text


# ---------------------------------------------------------------------------
# SndSeqLump.sequences — synthetic WAD tests
# ---------------------------------------------------------------------------


def _make_sndseq_wad(text: str) -> str:
    data = text.encode("latin-1")
    dir_offset = 12 + len(data)
    header = struct.pack("<4sII", b"PWAD", 1, dir_offset)
    entry = struct.pack("<II8s", 12, len(data), b"SNDSEQ\x00\x00")
    raw = header + data + entry
    with tempfile.NamedTemporaryFile(suffix=".wad", delete=False) as f:
        f.write(raw)
        return f.name


def test_sndseq_parses_basic_sequence() -> None:
    path = _make_sndseq_wad(":DoorOpen\n  playuntildone DoorOpen\n  end\n")
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        seqs = wad.sndseq.sequences
        assert len(seqs) == 1
        assert seqs[0].name == "DoorOpen"
        assert seqs[0].commands[0].command == "playuntildone"
        assert seqs[0].commands[0].sound == "DoorOpen"


def test_sndseq_parses_command_with_tics() -> None:
    path = _make_sndseq_wad(":Plat\n  playrepeat PlatMove 4\n  end\n")
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        cmd = wad.sndseq.sequences[0].commands[0]
        assert cmd.tics == 4


def test_sndseq_skips_comments_and_orphan_lines() -> None:
    # Lines before any label are ignored (covers the current is None branch)
    path = _make_sndseq_wad("; comment\norphan line\n:MySeq\n  stopsound\n  end\n")
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        seqs = wad.sndseq.sequences
        assert len(seqs) == 1
        assert seqs[0].name == "MySeq"


def test_sndseq_multiple_sequences() -> None:
    text = ":SeqA\n  playuntildone A\n  end\n:SeqB\n  stopsound\n  end\n"
    path = _make_sndseq_wad(text)
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        seqs = wad.sndseq.sequences
        assert len(seqs) == 2
        assert seqs[0].name == "SeqA"
        assert seqs[1].name == "SeqB"


def test_sndseq_get_by_name() -> None:
    path = _make_sndseq_wad(":DoorOpen\n  playuntildone DoorOpen\n  end\n")
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        seq = wad.sndseq.get_sequence("dooropen")  # case-insensitive
        assert seq is not None
        assert seq.name == "DoorOpen"


def test_sndseq_get_missing_returns_none() -> None:
    path = _make_sndseq_wad(":DoorOpen\n  end\n")
    with WadFile(path) as wad:
        assert wad.sndseq is not None
        assert wad.sndseq.get_sequence("MISSING") is None
