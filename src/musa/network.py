from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any


def compute_lineament_network_stats(
    line_geometries: Iterable[Any],
    boundary_geom: Any | None = None,
) -> dict[str, float | int]:
    lines = []
    for geom in line_geometries:
        if geom is None or geom.is_empty:
            continue
        clipped = geom.intersection(boundary_geom) if boundary_geom is not None else geom
        if clipped.is_empty:
            continue
        lines.extend([part for part in _iter_line_parts(clipped) if part.length > 0])

    n = len(lines)
    adjacency = [set() for _ in range(n)]
    intersection_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            inter = lines[i].intersection(lines[j])
            if inter.is_empty:
                continue
            adjacency[i].add(j)
            adjacency[j].add(i)
            intersection_count += 1

    components = _component_sizes(adjacency)
    total_length = sum(float(line.length) for line in lines)
    connected_length = sum(float(lines[i].length) for i, neigh in enumerate(adjacency) if neigh)
    area_km2 = _area_km2(boundary_geom, lines)
    return {
        "component_count": int(len(components)),
        "largest_component_fraction": float(max(components) / n) if n else 0.0,
        "node_count": int(n),
        "edge_count": int(intersection_count),
        "mean_degree": float(sum(len(neigh) for neigh in adjacency) / n) if n else 0.0,
        "intersection_density_per_km2": float(intersection_count / area_km2) if area_km2 > 0 else 0.0,
        "connected_length_fraction": float(connected_length / total_length) if total_length > 0 else 0.0,
    }


def _iter_line_parts(geom: Any):
    geom_type = getattr(geom, "geom_type", "")
    if geom_type == "LineString":
        yield geom
    elif geom_type == "MultiLineString":
        yield from geom.geoms
    elif geom_type == "GeometryCollection":
        for part in geom.geoms:
            yield from _iter_line_parts(part)


def _component_sizes(adjacency: list[set[int]]) -> list[int]:
    seen: set[int] = set()
    sizes: list[int] = []
    for start in range(len(adjacency)):
        if start in seen:
            continue
        queue: deque[int] = deque([start])
        seen.add(start)
        size = 0
        while queue:
            node = queue.popleft()
            size += 1
            for nxt in adjacency[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        sizes.append(size)
    return sizes


def _area_km2(boundary_geom: Any | None, lines: list[Any]) -> float:
    if boundary_geom is not None and not boundary_geom.is_empty:
        return float(boundary_geom.area) / 1_000_000.0
    if not lines:
        return 0.0
    minx = min(line.bounds[0] for line in lines)
    miny = min(line.bounds[1] for line in lines)
    maxx = max(line.bounds[2] for line in lines)
    maxy = max(line.bounds[3] for line in lines)
    return max((maxx - minx) * (maxy - miny), 0.0) / 1_000_000.0
