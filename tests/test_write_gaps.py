"""Tests for closing read/write gaps: ACS assembler, ENDOOM builder, GL node serialization."""

from __future__ import annotations

import struct

from wadlib.lumps.behavior import assemble_acs, build_behavior, disassemble_acs, parse_behavior
from wadlib.lumps.endoom import build_endoom, build_endoom_ansi
from wadlib.lumps.glnodes import (
    GlNode,
    GlSeg,
    GlSubSector,
    GlVertex,
    gl_nodes_to_bytes,
    gl_segs_to_bytes,
    gl_ssectors_to_bytes,
    gl_verts_to_bytes,
    parse_gl_nodes,
    parse_gl_segs,
    parse_gl_ssectors,
    parse_gl_verts,
)


# ---------------------------------------------------------------------------
# ACS assembler
# ---------------------------------------------------------------------------


class TestAcsAssembler:
    def test_basic_assemble(self) -> None:
        code = assemble_acs("""
            PushNumber 42
            Terminate
        """)
        # PushNumber(3) + arg(42) + Terminate(1) = 12 bytes
        assert len(code) == 12
        assert struct.unpack("<I", code[:4])[0] == 3  # PushNumber
        assert struct.unpack("<i", code[4:8])[0] == 42
        assert struct.unpack("<I", code[8:12])[0] == 1  # Terminate

    def test_round_trip(self) -> None:
        original = """
            BeginPrint
            PushNumber 0
            PrintString
            EndPrint
            DelayDirect 35
            Terminate
        """
        code = assemble_acs(original)
        disasm = disassemble_acs(code, 0, strings=["Hello"])
        # Reassemble the disassembly
        code2 = assemble_acs(disasm)
        assert code == code2

    def test_comments_stripped(self) -> None:
        code = assemble_acs("""
            # This is a comment
            PushNumber 10  ; inline comment
            ; another comment
            Terminate
        """)
        assert len(code) == 12  # PushNumber + arg + Terminate

    def test_unknown_opcode_raises(self) -> None:
        import pytest

        with pytest.raises(ValueError, match="Unknown"):
            assemble_acs("FakeInstruction 42")

    def test_no_args(self) -> None:
        code = assemble_acs("NOP")
        assert len(code) == 4
        assert struct.unpack("<I", code[:4])[0] == 0

    def test_multi_arg(self) -> None:
        code = assemble_acs("RandomDirect 1 10")
        assert len(code) == 12  # opcode + 2 args


class TestBuildBehavior:
    def test_basic_build(self) -> None:
        code = assemble_acs("Terminate")
        data = build_behavior(
            scripts=[(1, 0, 0, code)],
            strings=["test"],
        )
        assert data[:4] == b"ACS\x00"
        info = parse_behavior(data)
        assert info.format == "ACS0"
        assert len(info.scripts) == 1
        assert info.scripts[0].number == 1
        assert len(info.strings) == 1
        assert info.strings[0] == "test"

    def test_open_script(self) -> None:
        code = assemble_acs("Terminate")
        data = build_behavior(scripts=[(1, 1, 0, code)])  # type 1 = open
        info = parse_behavior(data)
        assert info.scripts[0].number == 1
        assert info.scripts[0].script_type == 1  # open

    def test_multiple_scripts(self) -> None:
        code1 = assemble_acs("Terminate")
        code2 = assemble_acs("PushNumber 5\nTerminate")
        data = build_behavior(
            scripts=[(1, 0, 0, code1), (2, 0, 1, code2)],
            strings=["hello", "world"],
        )
        info = parse_behavior(data)
        assert len(info.scripts) == 2
        assert len(info.strings) == 2

    def test_full_round_trip(self) -> None:
        """Build → parse → disassemble → assemble → rebuild → verify."""
        original_code = assemble_acs("""
            BeginPrint
            PushNumber 0
            PrintString
            EndPrint
            Terminate
        """)
        lump1 = build_behavior(
            scripts=[(1, 1, 0, original_code)],
            strings=["Round trip works!"],
        )
        info1 = parse_behavior(lump1)
        disasm = disassemble_acs(lump1, info1.scripts[0].offset, info1.strings)
        rebuilt_code = assemble_acs(disasm)
        lump2 = build_behavior(
            scripts=[(1, 1, 0, rebuilt_code)],
            strings=["Round trip works!"],
        )
        info2 = parse_behavior(lump2)
        assert len(info2.scripts) == 1
        assert info2.strings == ["Round trip works!"]


# ---------------------------------------------------------------------------
# ENDOOM builder
# ---------------------------------------------------------------------------


class TestEndoomBuilder:
    def test_basic_build(self) -> None:
        data = build_endoom("Hello, Doom!")
        assert len(data) == 4000  # 80*25*2
        # First char should be 'H'
        assert data[0] == ord("H")

    def test_default_colours(self) -> None:
        data = build_endoom("X", fg=7, bg=0)
        # attr byte: bg=0, fg=7 → 0x07
        assert data[1] == 0x07

    def test_custom_colours(self) -> None:
        data = build_endoom("A", fg=14, bg=1)
        # attr: bg=1 (0x10) | fg=14 (0x0E) → 0x1E
        assert data[1] == 0x1E

    def test_multi_line(self) -> None:
        data = build_endoom("Line1\nLine2")
        assert data[0] == ord("L")
        # Second line starts at offset 80*2
        assert data[160] == ord("L")

    def test_padding(self) -> None:
        data = build_endoom("Hi")
        # Third char should be space (0x20)
        assert data[4] == 0x20

    def test_ansi_build(self) -> None:
        cells = [[(" ", 7, 0)] * 80 for _ in range(25)]
        cells[0][0] = ("X", 15, 4)  # bright white on red
        data = build_endoom_ansi(cells)
        assert len(data) == 4000
        assert data[0] == ord("X")
        assert data[1] == 0x4F  # bg=4, fg=15


# ---------------------------------------------------------------------------
# GL node serialization
# ---------------------------------------------------------------------------


class TestGlNodeSerialization:
    def test_gl_verts_v2_round_trip(self) -> None:
        verts = [GlVertex(100.5, -200.25), GlVertex(0.0, 0.0)]
        data = gl_verts_to_bytes(verts, version=2)
        parsed = parse_gl_verts(data)
        assert len(parsed) == 2
        assert abs(parsed[0].x - 100.5) < 0.001
        assert abs(parsed[0].y - (-200.25)) < 0.001

    def test_gl_verts_v1_round_trip(self) -> None:
        verts = [GlVertex(100.0, -200.0)]
        data = gl_verts_to_bytes(verts, version=1)
        parsed = parse_gl_verts(data)
        assert len(parsed) == 1
        assert parsed[0].x == 100.0

    def test_gl_segs_round_trip(self) -> None:
        segs = [GlSeg(0, 1, 5, 0, 0xFFFF), GlSeg(2, 3, 0xFFFF, 1, 0)]
        data = gl_segs_to_bytes(segs)
        parsed = parse_gl_segs(data)
        assert len(parsed) == 2
        assert parsed[0].linedef == 5
        assert parsed[1].is_miniseg

    def test_gl_ssectors_round_trip(self) -> None:
        ssectors = [GlSubSector(4, 0), GlSubSector(3, 4)]
        data = gl_ssectors_to_bytes(ssectors)
        parsed = parse_gl_ssectors(data)
        assert len(parsed) == 2
        assert parsed[1].first_seg == 4

    def test_gl_nodes_round_trip(self) -> None:
        nodes = [GlNode(0, 0, 64, 0, (64, 0, 0, 64), (0, -64, 0, 64), 0, 0x8001)]
        data = gl_nodes_to_bytes(nodes)
        parsed = parse_gl_nodes(data)
        assert len(parsed) == 1
        assert parsed[0].dx == 64
        assert parsed[0].left_child == 0x8001
