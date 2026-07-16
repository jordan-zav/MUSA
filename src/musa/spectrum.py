from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .core import MUSAResult


def fit_quadratic_spectrum(alpha: np.ndarray, f_alpha: np.ndarray) -> dict[str, float | str]:
    x = np.asarray(alpha, dtype=float)
    y = np.asarray(f_alpha, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 3:
        return _blank_fit()

    a, b, c = np.polyfit(x, y, deg=2)
    y_hat = a * x**2 + b * x + c
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    vertex_alpha = float(-b / (2.0 * a)) if abs(a) > 1e-15 else float("nan")
    min_alpha = float(np.min(x))
    max_alpha = float(np.max(x))
    peak_valid = bool(a < 0 and np.isfinite(vertex_alpha) and min_alpha <= vertex_alpha <= max_alpha)
    alpha_peak = vertex_alpha if peak_valid else ""
    f_peak = float(a * vertex_alpha**2 + b * vertex_alpha + c) if peak_valid else ""
    left_width = vertex_alpha - min_alpha if peak_valid else ""
    right_width = max_alpha - vertex_alpha if peak_valid else ""
    delta_alpha = float(np.max(x) - np.min(x))
    asymmetry = float(left_width - right_width) if peak_valid else ""
    return {
        "quadratic_a": float(a),
        "quadratic_b": float(b),
        "quadratic_c": float(c),
        "quadratic_r2": float(r2),
        "alpha_peak": alpha_peak,
        "f_peak": f_peak,
        "delta_alpha": delta_alpha,
        "left_width": left_width,
        "right_width": right_width,
        "spectrum_asymmetry": asymmetry,
        "concavity": float(a),
        "is_concave": int(a < 0),
        "peak_in_range": int(peak_valid),
        "fit_valid": int(peak_valid and np.isfinite(r2)),
        "points_count": int(x.size),
    }


def spectrum_shape_diagnostics(
    q: np.ndarray,
    alpha: np.ndarray,
    f_alpha: np.ndarray,
) -> dict[str, float | int | str]:
    q_arr = np.asarray(q, dtype=float)
    alpha_arr = np.asarray(alpha, dtype=float)
    f_arr = np.asarray(f_alpha, dtype=float)
    mask = np.isfinite(q_arr) & np.isfinite(alpha_arr) & np.isfinite(f_arr)
    q_arr = q_arr[mask]
    alpha_arr = alpha_arr[mask]
    f_arr = f_arr[mask]
    if q_arr.size == 0:
        return {
            "alpha_q_monotonic": "insufficient",
            "alpha_q_turns": 0,
            "f_alpha_peak_q": "",
            "f_alpha_peak": "",
            "alpha_at_f_peak": "",
        }

    order = np.argsort(q_arr)
    q_sorted = q_arr[order]
    alpha_sorted = alpha_arr[order]
    f_sorted = f_arr[order]
    diffs = np.diff(alpha_sorted)
    signs = np.sign(diffs[np.abs(diffs) > 1e-12])
    if signs.size == 0:
        monotonic = "flat"
        turns = 0
    else:
        turns = int(np.sum(signs[1:] != signs[:-1]))
        if np.all(signs > 0):
            monotonic = "increasing"
        elif np.all(signs < 0):
            monotonic = "decreasing"
        else:
            monotonic = "non_monotonic"

    peak_idx = int(np.argmax(f_sorted))
    return {
        "alpha_q_monotonic": monotonic,
        "alpha_q_turns": turns,
        "f_alpha_peak_q": float(q_sorted[peak_idx]),
        "f_alpha_peak": float(f_sorted[peak_idx]),
        "alpha_at_f_peak": float(alpha_sorted[peak_idx]),
    }


def write_spectrum_fit_summary(output_dir: str | Path, result: MUSAResult) -> str:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "spectrum_fit_summary.csv"
    diagnostics = spectrum_shape_diagnostics(result.q, result.alpha, result.f_alpha)
    rows: list[dict[str, Any]] = []
    global_fit = fit_quadratic_spectrum(result.alpha, result.f_alpha)
    rows.append({
        "fit_type": "global_quadratic",
        "q_min": float(np.min(result.q)) if result.q.size else "",
        "q_max": float(np.max(result.q)) if result.q.size else "",
        **global_fit,
        **diagnostics,
    })
    branch_specs = [
        ("negative_q_branch", result.q < 0),
        ("nonnegative_q_branch", result.q >= 0),
        ("positive_q_branch", result.q > 0),
    ]
    for name, mask in branch_specs:
        if int(np.sum(mask)) < 3:
            continue
        branch_fit = fit_quadratic_spectrum(result.alpha[mask], result.f_alpha[mask])
        branch_diag = spectrum_shape_diagnostics(result.q[mask], result.alpha[mask], result.f_alpha[mask])
        rows.append({
            "fit_type": name,
            "q_min": float(np.min(result.q[mask])),
            "q_max": float(np.max(result.q[mask])),
            **branch_fit,
            **branch_diag,
        })
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def _blank_fit() -> dict[str, float | str]:
    return {
        "quadratic_a": "",
        "quadratic_b": "",
        "quadratic_c": "",
        "quadratic_r2": "",
        "alpha_peak": "",
        "f_peak": "",
        "delta_alpha": "",
        "left_width": "",
        "right_width": "",
        "spectrum_asymmetry": "",
        "concavity": "",
        "is_concave": 0,
        "peak_in_range": 0,
        "fit_valid": 0,
        "points_count": 0,
    }
