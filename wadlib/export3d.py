"""3D mesh exporter — convert Doom maps to OBJ (Wavefront) format.

Constructs a 3D mesh from map geometry:
- **Floor polygons**: subsector shapes at sector floor heights
- **Ceiling polygons**: same shapes at sector ceiling heights
- **Wall quads**: linedefs extruded between adjacent sector heights

The Y axis from the WAD (north/south) maps to Z in OBJ (up is positive Y
in OBJ), and floor/ceiling heights become OBJ Y coordinates.  One map unit
equals one OBJ unit.

Usage::

    from wadlib.export3d import map_to_obj
    from wadlib.wad import WadFile

    with WadFile("DOOM2.WAD") as wad:
        obj_text = map_to_obj(wad.maps[0])
        with open("MAP01.obj", "w") as f:
            f.write(obj_text)

    # With material names (texture references)
    obj, mtl = map_to_obj(wad.maps[0], materials=True)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .lumps.map import BaseMapEntry


def map_to_obj(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    level: BaseMapEntry,
    *,
    scale: float = 1.0,
    materials: bool = False,
) -> str | tuple[str, str]:
    """Export a Doom map to Wavefront OBJ format.

    Parameters:
        level:      A parsed map entry (``wad.maps[0]``).
        scale:      Scale factor (default 1.0 — one map unit = one OBJ unit).
        materials:  If True, return ``(obj_text, mtl_text)`` with material
                    references for wall/floor/ceiling textures.

    Returns:
        OBJ text string, or ``(obj, mtl)`` tuple if ``materials=True``.
    """
    if not level.vertices or not level.lines or not level.sidedefs or not level.sectors:
        empty = f"# {level.name} — empty map\n"
        return (empty, "") if materials else empty

    verts: list[Any] = list(level.vertices)
    sides: list[Any] = list(level.sidedefs)
    sectors: list[Any] = list(level.sectors)

    s = scale

    # Collect unique 3D vertices: (x, z, y) in OBJ space
    # WAD (x, y, floor_h/ceil_h) → OBJ (x, h, -y)  [Doom Y → OBJ -Z]
    obj_verts: list[tuple[float, float, float]] = []
    vert_index: dict[tuple[float, float, float], int] = {}

    def _add_vert(x: float, h: float, y: float) -> int:
        """Add a 3D vertex and return its 1-based OBJ index."""
        key = (x * s, h * s, -y * s)
        if key in vert_index:
            return vert_index[key]
        obj_verts.append(key)
        idx = len(obj_verts)
        vert_index[key] = idx
        return idx

    faces: list[tuple[str, list[int]]] = []  # (material_name, [v1, v2, ...])
    mtl_names: set[str] = set()

    # --- Walls from linedefs ---
    for line in level.lines:
        sv = line.start_vertex
        ev = line.finish_vertex
        if sv >= len(verts) or ev >= len(verts):
            continue

        v1 = verts[sv]
        v2 = verts[ev]
        x1, y1 = float(v1.x), float(v1.y)
        x2, y2 = float(v2.x), float(v2.y)

        right_idx = line.right_sidedef
        left_idx = line.left_sidedef if hasattr(line, "left_sidedef") else -1

        # Right side wall
        if 0 <= right_idx < len(sides):
            right_side = sides[right_idx]
            if right_side.sector < len(sectors):
                right_sector = sectors[right_side.sector]
                floor_h = float(right_sector.floor_height)
                ceil_h = float(right_sector.ceiling_height)

                if left_idx < 0 or left_idx >= len(sides):
                    # One-sided line — full wall
                    tex = right_side.middle_texture if right_side.middle_texture != "-" else "WALL"
                    _add_wall_quad(
                        faces,
                        mtl_names,
                        tex,
                        x1,
                        y1,
                        x2,
                        y2,
                        floor_h,
                        ceil_h,
                        _add_vert,
                    )
                else:
                    # Two-sided line — upper/lower walls
                    left_side = sides[left_idx]
                    if left_side.sector < len(sectors):
                        left_sector = sectors[left_side.sector]
                        l_floor = float(left_sector.floor_height)
                        l_ceil = float(left_sector.ceiling_height)

                        # Upper wall (right ceiling to left ceiling)
                        if ceil_h > l_ceil:
                            tex = (
                                right_side.upper_texture
                                if right_side.upper_texture != "-"
                                else "WALL"
                            )
                            _add_wall_quad(
                                faces,
                                mtl_names,
                                tex,
                                x1,
                                y1,
                                x2,
                                y2,
                                l_ceil,
                                ceil_h,
                                _add_vert,
                            )

                        # Lower wall (left floor to right floor)
                        if floor_h < l_floor:
                            tex = (
                                right_side.lower_texture
                                if right_side.lower_texture != "-"
                                else "WALL"
                            )
                            _add_wall_quad(
                                faces,
                                mtl_names,
                                tex,
                                x1,
                                y1,
                                x2,
                                y2,
                                floor_h,
                                l_floor,
                                _add_vert,
                            )

    # --- Floors and ceilings from subsectors ---
    if level.segs and level.ssectors:
        segs_list: list[Any] = list(level.segs)

        for ssector in level.ssectors:
            seg_indices = range(ssector.first_seg, ssector.first_seg + ssector.seg_count)
            poly_verts: list[tuple[float, float]] = []
            sector_idx: int | None = None

            for si in seg_indices:
                if si >= len(segs_list):
                    break
                seg = segs_list[si]

                # Determine sector from seg's linedef
                if (
                    sector_idx is None
                    and hasattr(seg, "linedef")
                    and seg.linedef < len(list(level.lines))
                ):
                    ld = list(level.lines)[seg.linedef]
                    side_idx = ld.right_sidedef if seg.direction == 0 else ld.left_sidedef
                    if 0 <= side_idx < len(sides):
                        sector_idx = sides[side_idx].sector

                if seg.start_vertex < len(verts):
                    v = verts[seg.start_vertex]
                    poly_verts.append((float(v.x), float(v.y)))

            if len(poly_verts) >= 3 and sector_idx is not None and sector_idx < len(sectors):
                sec = sectors[sector_idx]
                floor_h = float(sec.floor_height)
                ceil_h = float(sec.ceiling_height)

                # Floor polygon
                floor_tex = sec.floor_texture if sec.floor_texture != "-" else "FLOOR"
                floor_indices = [_add_vert(px, floor_h, py) for px, py in poly_verts]
                mtl_names.add(floor_tex)
                faces.append((floor_tex, floor_indices))

                # Ceiling polygon (reversed winding for correct normal)
                ceil_tex = sec.ceiling_texture if sec.ceiling_texture != "-" else "CEIL"
                ceil_indices = [_add_vert(px, ceil_h, py) for px, py in reversed(poly_verts)]
                mtl_names.add(ceil_tex)
                faces.append((ceil_tex, ceil_indices))

    # --- Build OBJ text ---
    obj_lines: list[str] = []
    obj_lines.append(f"# {level.name} — exported by wadlib")
    obj_lines.append(f"# {len(obj_verts)} vertices, {len(faces)} faces")
    if materials:
        obj_lines.append(f"mtllib {level.name}.mtl")
    obj_lines.append("")

    for vx, vy, vz in obj_verts:
        obj_lines.append(f"v {vx:.4f} {vy:.4f} {vz:.4f}")
    obj_lines.append("")

    current_mtl = ""
    for mtl, face_verts in faces:
        if materials and mtl != current_mtl:
            obj_lines.append(f"usemtl {mtl}")
            current_mtl = mtl
        obj_lines.append("f " + " ".join(str(v) for v in face_verts))

    obj_text = "\n".join(obj_lines) + "\n"

    if materials:
        mtl_lines = [f"# Materials for {level.name}"]
        for name in sorted(mtl_names):
            mtl_lines.append(f"\nnewmtl {name}")
            mtl_lines.append("Ka 0.2 0.2 0.2")
            mtl_lines.append("Kd 0.8 0.8 0.8")
            mtl_lines.append("Ks 0.0 0.0 0.0")
        mtl_text = "\n".join(mtl_lines) + "\n"
        return obj_text, mtl_text

    return obj_text


def _add_wall_quad(
    faces: list[tuple[str, list[int]]],
    mtl_names: set[str],
    texture: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    bottom: float,
    top: float,
    add_vert: Any,
) -> None:
    """Add a wall quad between two 2D points at bottom/top heights."""
    if top <= bottom:
        return
    # Quad: bottom-left, bottom-right, top-right, top-left
    bl = add_vert(x1, bottom, y1)
    br = add_vert(x2, bottom, y2)
    tr = add_vert(x2, top, y2)
    tl = add_vert(x1, top, y1)
    mtl_names.add(texture)
    faces.append((texture, [bl, br, tr, tl]))
