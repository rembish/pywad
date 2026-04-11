"""Pure geometry helpers used by the renderer."""

from __future__ import annotations


def _clip_poly(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    polygon: list[tuple[float, float]],
    nx: float,
    ny: float,
    ndx: float,
    ndy: float,
    keep_right: bool,
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman clip of a convex polygon against a BSP half-plane.

    Half-plane convention (map-coordinate cross product):
        cross = (P.x - nx)*ndy - (P.y - ny)*ndx
        keep_right=True  → keep where cross >= 0  (Doom "right child" side)
        keep_right=False → keep where cross <= 0  (Doom "left child" side)
    """
    if len(polygon) < 2:
        return []

    def _cross(p: tuple[float, float]) -> float:
        return (p[0] - nx) * ndy - (p[1] - ny) * ndx

    def _intersect(p1: tuple[float, float], p2: tuple[float, float]) -> tuple[float, float]:
        c1, c2 = _cross(p1), _cross(p2)
        denom = c1 - c2
        if denom == 0.0:
            return p1
        t = c1 / denom
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))

    result: list[tuple[float, float]] = []
    n = len(polygon)
    for i in range(n):
        curr = polygon[i]
        prev = polygon[i - 1]
        cc = _cross(curr)
        pc = _cross(prev)
        curr_in = cc >= 0 if keep_right else cc <= 0
        prev_in = pc >= 0 if keep_right else pc <= 0
        if curr_in:
            if not prev_in:
                result.append(_intersect(prev, curr))
            result.append(curr)
        elif prev_in:
            result.append(_intersect(prev, curr))
    return result
