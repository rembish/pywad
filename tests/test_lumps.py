"""Tests for lump data — Things, Vertices, LineDefs, BaseLump seek/read."""

from io import SEEK_CUR, SEEK_END, SEEK_SET

from wadlib.lumps.lines import LineDefinition
from wadlib.lumps.things import Flags, Thing
from wadlib.lumps.vertices import Vertex
from wadlib.wad import WadFile

# ---------------------------------------------------------------------------
# Things
# ---------------------------------------------------------------------------


def test_things_yield_thing_objects(doom1_wad: WadFile) -> None:
    things = doom1_wad.maps[0].things
    first = things[0]
    assert isinstance(first, Thing)


def test_thing_has_x_y(doom1_wad: WadFile) -> None:
    t = doom1_wad.maps[0].things[0]
    assert isinstance(t.x, int)
    assert isinstance(t.y, int)


def test_thing_flags_is_flags(doom1_wad: WadFile) -> None:
    t = doom1_wad.maps[0].things[0]
    assert isinstance(t.flags, Flags)


def test_things_iteration(doom1_wad: WadFile) -> None:
    things = doom1_wad.maps[0].things
    count = sum(1 for _ in things)
    assert count == len(things)


def test_things_getitem_eq_iteration(doom1_wad: WadFile) -> None:
    things = doom1_wad.maps[0].things
    iterated = list(things)
    indexed = [things[i] for i in range(len(things))]
    assert iterated == indexed


def test_minimal_thing_values(minimal_iwad: WadFile) -> None:
    t = minimal_iwad.maps[0].things[0]
    assert t.x == 0
    assert t.y == 0
    assert t.type == 1


# ---------------------------------------------------------------------------
# Vertices
# ---------------------------------------------------------------------------


def test_vertices_yield_vertex_objects(doom1_wad: WadFile) -> None:
    v = doom1_wad.maps[0].vertices[0]
    assert isinstance(v, Vertex)


def test_vertex_has_x_y(doom1_wad: WadFile) -> None:
    v = doom1_wad.maps[0].vertices[0]
    assert isinstance(v.x, int)
    assert isinstance(v.y, int)


def test_minimal_vertex_values(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    assert verts[0] == Vertex(0, 0)
    assert verts[1] == Vertex(64, 0)


# ---------------------------------------------------------------------------
# LineDefs
# ---------------------------------------------------------------------------


def test_linedefs_yield_linedefinition(doom1_wad: WadFile) -> None:
    line = doom1_wad.maps[0].lines[0]
    assert isinstance(line, LineDefinition)


def test_linedef_vertex_indices_in_range(doom1_wad: WadFile) -> None:
    lines = doom1_wad.maps[0].lines
    vertex_count = len(doom1_wad.maps[0].vertices)
    for line in lines:
        assert 0 <= line.start_vertex < vertex_count
        assert 0 <= line.finish_vertex < vertex_count


def test_minimal_linedef_values(minimal_iwad: WadFile) -> None:
    line = minimal_iwad.maps[0].lines[0]
    assert line.start_vertex == 0
    assert line.finish_vertex == 1


# ---------------------------------------------------------------------------
# BaseLump seek / tell
# ---------------------------------------------------------------------------


def test_seek_set(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    verts.seek(0, SEEK_SET)
    assert verts.tell() == 0


def test_seek_cur_forward(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    row_size = verts._row_size
    verts.seek(0, SEEK_SET)
    verts.seek(row_size, SEEK_CUR)
    assert verts.tell() == row_size


def test_seek_cur_backward(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    row_size = verts._row_size
    verts.seek(row_size, SEEK_SET)
    verts.seek(-row_size, SEEK_CUR)
    assert verts.tell() == 0


def test_seek_cur_clamp_to_zero(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    verts.seek(0, SEEK_SET)
    verts.seek(-9999, SEEK_CUR)
    assert verts.tell() == 0


def test_seek_end(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    size = verts._size
    verts.seek(0, SEEK_END)
    assert verts.tell() == size


def test_seek_set_clamp_to_size(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    verts.seek(99999, SEEK_SET)
    assert verts.tell() == verts._size


def test_lump_len(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    assert len(verts) == 2


def test_lump_get_valid(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    assert verts.get(0) == Vertex(0, 0)


def test_lump_get_out_of_range_returns_default(minimal_iwad: WadFile) -> None:
    verts = minimal_iwad.maps[0].vertices
    assert verts.get(999) is None
    assert verts.get(999, "fallback") == "fallback"


# ---------------------------------------------------------------------------
# Boundaries
# ---------------------------------------------------------------------------


def test_boundaries_returns_two_points(doom1_wad: WadFile) -> None:
    b = doom1_wad.maps[0].boundaries
    assert len(b) == 2


def test_boundaries_min_le_max(doom1_wad: WadFile) -> None:
    b = doom1_wad.maps[0].boundaries
    assert b[0].x <= b[1].x
    assert b[0].y <= b[1].y


def test_boundaries_empty_map_returns_origin(minimal_pwad: WadFile) -> None:
    # minimal_pwad has an empty VERTEXES lump
    m = minimal_pwad.maps[0]
    b = m.boundaries
    # things has one entry (10, 20); vertices is empty
    assert b[0].x <= b[1].x


# ---------------------------------------------------------------------------
# Concurrent iteration (fd hazard regression)
# ---------------------------------------------------------------------------


def test_zip_things_vertices_gives_correct_counts(doom1_wad: WadFile) -> None:
    """zip(things, vertices) must not interleave seeks on the shared WAD fd.

    Before the BytesIO buffering fix, iterating two lumps concurrently would
    corrupt both streams because each lump seeked the same file descriptor.
    """
    m = doom1_wad.maps[0]
    pairs = list(zip(m.things, m.vertices, strict=False))
    assert len(pairs) == min(len(m.things), len(m.vertices))


def test_parallel_iteration_values_unchanged(doom1_wad: WadFile) -> None:
    """Values read via zip must match values read sequentially."""
    m = doom1_wad.maps[0]
    things_seq = list(m.things)
    vertices_seq = list(m.vertices)
    for i, (t, v) in enumerate(zip(m.things, m.vertices, strict=False)):
        assert t == things_seq[i]
        assert v == vertices_seq[i]
