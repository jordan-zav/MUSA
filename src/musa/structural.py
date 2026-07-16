from __future__ import annotations

from collections.abc import Iterable
from math import atan2, cos, degrees, floor, hypot, pi, radians, sin
from typing import Any

import numpy as np


def compute_lineament_mother_structural_stats(
    line_geometries: Iterable[Any],
    boundary_geom: Any,
    mother_scale: float,
    orientation_bin_degrees: int = 10,
    origin: Iterable[float] | None = None,
) -> list[dict[str, float | int | str]]:
    if mother_scale <= 0 or not np.isfinite(mother_scale):
        raise ValueError("mother_scale debe ser positivo y finito.")
    if orientation_bin_degrees <= 0 or 180 % int(orientation_bin_degrees) != 0:
        raise ValueError("orientation_bin_degrees debe dividir exactamente 180.")
    if boundary_geom is None or boundary_geom.is_empty:
        raise ValueError("boundary_geom no puede estar vacio.")

    from shapely.geometry import box

    ox, oy = _origin_xy(boundary_geom, origin)
    minx, miny, maxx, maxy = boundary_geom.bounds
    ix0 = int(floor((minx - ox) / mother_scale))
    ix1 = int(floor((maxx - ox - 1e-12) / mother_scale))
    iy0 = int(floor((miny - oy) / mother_scale))
    iy1 = int(floor((maxy - oy - 1e-12) / mother_scale))
    bins = _bin_names(orientation_bin_degrees)
    accum: dict[tuple[int, int], dict[str, Any]] = {}

    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            cell = _mother_box(ox, oy, ix, iy, mother_scale)
            if cell.intersection(boundary_geom).is_empty:
                continue
            accum[(ix, iy)] = {
                "lengths": [],
                "azimuths": [],
                "bins": {name: 0.0 for name in bins},
            }

    for geom in line_geometries:
        if geom is None or geom.is_empty:
            continue
        clipped = geom.intersection(boundary_geom)
        if clipped.is_empty:
            continue
        gminx, gminy, gmaxx, gmaxy = clipped.bounds
        gx0 = int(floor((gminx - ox) / mother_scale))
        gx1 = int(floor((gmaxx - ox) / mother_scale))
        gy0 = int(floor((gminy - oy) / mother_scale))
        gy1 = int(floor((gmaxy - oy) / mother_scale))
        for ix in range(gx0, gx1 + 1):
            for iy in range(gy0, gy1 + 1):
                key = (ix, iy)
                if key not in accum:
                    continue
                inter = clipped.intersection(_mother_box(ox, oy, ix, iy, mother_scale))
                if inter.is_empty:
                    continue
                for segment in _iter_line_parts(inter):
                    length = float(segment.length)
                    if length <= 0:
                        continue
                    azimuth = _axial_azimuth(segment)
                    bin_name = _bin_name_for_azimuth(azimuth, orientation_bin_degrees)
                    accum[key]["lengths"].append(length)
                    accum[key]["azimuths"].append(azimuth)
                    accum[key]["bins"][bin_name] += length

    rows: list[dict[str, float | int | str]] = []
    mother_area_km2 = (mother_scale * mother_scale) / 1_000_000.0
    for key in sorted(accum):
        ix, iy = key
        data = accum[key]
        lengths = np.array(data["lengths"], dtype=float)
        azimuths = np.array(data["azimuths"], dtype=float)
        total = float(np.sum(lengths)) if lengths.size else 0.0
        row: dict[str, float | int | str] = {
            "mother_ix": int(ix),
            "mother_iy": int(iy),
            "mother_centroid_x": ox + (ix + 0.5) * mother_scale,
            "mother_centroid_y": oy + (iy + 0.5) * mother_scale,
            "mother_scale_m": float(mother_scale),
            "mother_area_km2": float(mother_area_km2),
            "measure_sum_m": float(total),
            "density_m_per_km2": float(total / mother_area_km2) if mother_area_km2 > 0 else "",
            "segment_count": int(lengths.size),
        }
        if lengths.size:
            mean_azimuth, resultant = _weighted_axial_mean(azimuths, lengths)
            row.update(
                {
                    "dominant_azimuth_deg": _dominant_bin_center(data["bins"], orientation_bin_degrees),
                    "mean_azimuth_deg": mean_azimuth,
                    "circular_variance": 1.0 - resultant,
                    "mean_resultant_length": resultant,
                    "anisotropy_ratio": _anisotropy_ratio(data["bins"]),
                }
            )
        else:
            row.update(
                {
                    "dominant_azimuth_deg": "",
                    "mean_azimuth_deg": "",
                    "circular_variance": "",
                    "mean_resultant_length": "",
                    "anisotropy_ratio": "",
                }
            )
        for name in bins:
            row[name] = float(data["bins"][name])
        rows.append(row)
    return rows


def _origin_xy(boundary_geom: Any, origin: Iterable[float] | None) -> tuple[float, float]:
    if origin is None:
        minx, miny, *_ = boundary_geom.bounds
        return float(minx), float(miny)
    vals = list(origin)
    return float(vals[0]), float(vals[1])


def _mother_box(ox: float, oy: float, ix: int, iy: int, scale: float):
    from shapely.geometry import box

    return box(ox + ix * scale, oy + iy * scale, ox + (ix + 1) * scale, oy + (iy + 1) * scale)


def _iter_line_parts(geom: Any):
    geom_type = getattr(geom, "geom_type", "")
    if geom_type == "LineString":
        yield geom
    elif geom_type == "MultiLineString":
        yield from geom.geoms
    elif geom_type == "GeometryCollection":
        for part in geom.geoms:
            yield from _iter_line_parts(part)


def _axial_azimuth(line: Any) -> float:
    coords = list(line.coords)
    if len(coords) < 2:
        return 0.0
    x0, y0 = coords[0][:2]
    x1, y1 = coords[-1][:2]
    angle = degrees(atan2(y1 - y0, x1 - x0)) % 180.0
    if np.isclose(angle, 180.0):
        return 0.0
    return float(angle)


def _weighted_axial_mean(azimuths: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    doubled = np.radians(2.0 * azimuths)
    sum_cos = float(np.sum(weights * np.cos(doubled)))
    sum_sin = float(np.sum(weights * np.sin(doubled)))
    total = float(np.sum(weights))
    if total <= 0:
        return float("nan"), float("nan")
    mean = (0.5 * degrees(atan2(sum_sin, sum_cos))) % 180.0
    resultant = hypot(sum_cos, sum_sin) / total
    if np.isclose(mean, 180.0):
        mean = 0.0
    return float(mean), float(resultant)


def _bin_names(step: int) -> list[str]:
    return [f"bin_{start:03d}_{start + step:03d}_m" for start in range(0, 180, step)]


def _bin_name_for_azimuth(azimuth: float, step: int) -> str:
    start = min(int(floor((azimuth % 180.0) / step)) * step, 180 - step)
    return f"bin_{start:03d}_{start + step:03d}_m"


def _dominant_bin_center(bin_lengths: dict[str, float], step: int) -> float | str:
    if not bin_lengths or max(bin_lengths.values()) <= 0:
        return ""
    name = max(bin_lengths, key=lambda k: (bin_lengths[k], -int(k[4:7])))
    return float(int(name[4:7]) + step / 2.0 if int(name[4:7]) != 0 else 0.0)


def _anisotropy_ratio(bin_lengths: dict[str, float]) -> float | str:
    values = sorted((float(v) for v in bin_lengths.values() if v > 0), reverse=True)
    if not values:
        return ""
    if len(values) == 1:
        return float("inf")
    return float(values[0] / values[1]) if values[1] > 0 else float("inf")
