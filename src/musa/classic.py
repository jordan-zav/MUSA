"""Optional occupied-box comparison; independent of scaling decisions."""

import json
from pathlib import Path

import numpy as np

from .control import check_cancelled
from .mass_partition import line_masses
from .network import _iter_line_parts


def classic_box_counting(analyzer, scales_m, *, origin=None, cancelled=None):
    """OLS of ln N against ln(1/eps), using every supplied scale and one grid.

    Occupation means positive trace length inside the observed polygon. There
    is no length threshold, interval trimming, origin averaging or fit gate.
    The default origin is the lower-left corner of the domain bounding box.
    """
    check_cancelled(cancelled)
    if analyzer._kind != "lines":
        raise ValueError("Classic comparison requires line geometries.")
    scales = np.asarray(scales_m, dtype=float)
    if (scales.ndim != 1 or len(scales) < 2 or not np.isfinite(scales).all()
            or (scales <= 0).any() or len(np.unique(scales)) != len(scales)):
        raise ValueError("Use at least two distinct positive finite box sizes.")
    grid = np.asarray(analyzer._boundary_geom.bounds[:2] if origin is None else origin, dtype=float)
    if grid.shape != (2,) or not np.isfinite(grid).all():
        raise ValueError("Use one finite two-coordinate grid origin.")
    lines = []
    for geometry in analyzer._line_geometries:
        check_cancelled(cancelled)
        lines.extend(part for part in _iter_line_parts(geometry.intersection(analyzer._boundary_geom))
                     if part.length > 0)
    counts = []
    for scale in scales:
        check_cancelled(cancelled)
        counts.append(int(sum(value > 0 for value in line_masses(lines, scale, grid).values())))
    result = {"comparison_only": True, "method": "classic_box_counting", "support_id": "global",
              "origin": grid.tolist(), "scales_m": scales.tolist(), "occupied_boxes": counts,
              "dimension": None, "intercept": None, "r2": None,
              "calculation_status": "empty_support", "scaling_diagnostic": "not_applied"}
    if all(counts):
        x, y = np.log(1 / scales), np.log(counts)
        slope, intercept = np.linalg.lstsq(np.column_stack([x, np.ones(len(x))]), y, rcond=None)[0]
        residual = float(np.sum((y - (slope * x + intercept)) ** 2))
        total = float(np.sum((y - y.mean()) ** 2))
        result.update(dimension=float(slope), intercept=float(intercept),
                      r2=float(1 - residual / total) if total > 0 else None,
                      calculation_status="computed")
    return result


def write_classic_comparison(output_dir, result):
    """Keep the comparison in its own JSON block and CSV table."""
    import csv

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target, table = out / "classic_comparison.json", out / "classic_comparison.csv"
    target.write_text(json.dumps({"comparison": result}, indent=2, allow_nan=False), encoding="utf-8")
    fields = ["comparison_only", "method", "support_id", "scale_m", "occupied_boxes", "dimension", "r2",
              "origin_x", "origin_y", "calculation_status", "scaling_diagnostic"]
    with table.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for scale, count in zip(result["scales_m"], result["occupied_boxes"]):
            writer.writerow({**{key: result[key] for key in fields if key in result},
                             "scale_m": scale, "occupied_boxes": count,
                             "origin_x": result["origin"][0], "origin_y": result["origin"][1]})
    return {"classic_comparison_json": str(target), "classic_comparison_csv": str(table)}
