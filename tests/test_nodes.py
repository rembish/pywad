"""Tests for NODES lump."""

from struct import calcsize

from wadlib.lumps.nodes import NODE_FORMAT, SSECTOR_FLAG, BBox, Node
from wadlib.wad import WadFile


def test_node_format_size() -> None:
    assert calcsize(NODE_FORMAT) == 28


def test_nodes_attached(doom1_wad: WadFile) -> None:
    assert doom1_wad.maps[0].nodes is not None


def test_nodes_non_empty(doom1_wad: WadFile) -> None:
    assert len(doom1_wad.maps[0].nodes) > 0


def test_node_is_node(doom1_wad: WadFile) -> None:
    n = doom1_wad.maps[0].nodes[0]
    assert isinstance(n, Node)


def test_node_bboxes_are_bbox(doom1_wad: WadFile) -> None:
    n = doom1_wad.maps[0].nodes[0]
    assert isinstance(n.right_bbox, BBox)
    assert isinstance(n.left_bbox, BBox)


def test_node_bbox_top_ge_bottom(doom1_wad: WadFile) -> None:
    for node in doom1_wad.maps[0].nodes:
        assert node.right_bbox.top >= node.right_bbox.bottom
        assert node.left_bbox.top >= node.left_bbox.bottom


def test_node_ssector_flag(doom1_wad: WadFile) -> None:
    nodes = doom1_wad.maps[0].nodes
    # At least some leaf nodes should point to subsectors
    has_ssector = any(n.right_is_subsector or n.left_is_subsector for n in nodes)
    assert has_ssector


def test_ssector_flag_constant() -> None:
    assert SSECTOR_FLAG == 0x8000


def test_nodes_doom2(doom2_wad: WadFile) -> None:
    assert doom2_wad.maps[0].nodes is not None
    assert len(doom2_wad.maps[0].nodes) > 0
