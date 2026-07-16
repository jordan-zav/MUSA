import csv
import math
from pathlib import Path

import numpy as np

from musa.core import MUSAResult
from musa.spectrum import (
    fit_quadratic_spectrum,
    spectrum_shape_diagnostics,
    write_spectrum_fit_summary,
)


def test_fit_quadratic_spectrum_reports_peak_width_and_r2():
    alpha = np.array([1.0, 1.5, 2.0, 2.5, 3.0], dtype=float)
    f_alpha = -1.2 * (alpha - 2.0) ** 2 + 1.8

    fit = fit_quadratic_spectrum(alpha, f_alpha)

    assert math.isclose(fit["quadratic_r2"], 1.0, abs_tol=1e-12)
    assert math.isclose(fit["alpha_peak"], 2.0, abs_tol=1e-12)
    assert math.isclose(fit["f_peak"], 1.8, abs_tol=1e-12)
    assert math.isclose(fit["delta_alpha"], 2.0, abs_tol=1e-12)
    assert fit["concavity"] < 0
    assert fit["fit_valid"] == 1


def test_fit_quadratic_spectrum_flags_convex_curve_as_not_valid_peak():
    alpha = np.array([1.0, 1.5, 2.0, 2.5, 3.0], dtype=float)
    f_alpha = 1.2 * (alpha - 2.0) ** 2 + 1.0

    fit = fit_quadratic_spectrum(alpha, f_alpha)

    assert math.isclose(fit["quadratic_r2"], 1.0, abs_tol=1e-12)
    assert fit["fit_valid"] == 0
    assert fit["alpha_peak"] == ""
    assert fit["f_peak"] == ""


def test_write_spectrum_fit_summary_writes_global_fit(tmp_path):
    result = MUSAResult(
        q=np.array([0, 1, 2], dtype=float),
        scales=np.array([4000, 2000, 1000], dtype=float),
        dq=np.array([1, 1, 1], dtype=float),
        tau=np.array([0, 0, 0], dtype=float),
        alpha=np.array([1.0, 2.0, 3.0], dtype=float),
        f_alpha=np.array([1.0, 2.0, 1.0], dtype=float),
        r2=np.array([0.99, 0.99, 0.99], dtype=float),
        p_values=np.array([0.01, 0.01, 0.01], dtype=float),
        alpha_r2=np.array([0.99, 0.99, 0.99], dtype=float),
        f_alpha_r2=np.array([0.99, 0.99, 0.99], dtype=float),
        min_r2=0.9,
        rejected_q=np.array([], dtype=float),
        rejected_r2=np.array([], dtype=float),
        rejected_alpha_r2=np.array([], dtype=float),
        rejected_f_alpha_r2=np.array([], dtype=float),
    )

    path = write_spectrum_fit_summary(tmp_path, result)

    with Path(path).open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    assert rows[0]["fit_type"] == "global_quadratic"
    assert math.isclose(float(rows[0]["alpha_peak"]), 2.0, abs_tol=1e-12)


def test_spectrum_shape_diagnostics_flags_non_monotonic_alpha_by_q():
    q = np.array([-4, -3, -2, -1, 0, 1, 2, 3, 4], dtype=float)
    alpha = np.array([1.414, 1.415, 1.399, 1.219, 1.267, 1.533, 1.608, 1.601, 1.575])
    f_alpha = np.array([1.048, 1.064, 1.132, 1.386, 1.418, 1.533, 1.634, 1.614, 1.521])

    diagnostics = spectrum_shape_diagnostics(q, alpha, f_alpha)

    assert diagnostics["alpha_q_monotonic"] == "non_monotonic"
    assert diagnostics["alpha_q_turns"] == 3
    assert diagnostics["f_alpha_peak_q"] == 2.0


def test_write_spectrum_fit_summary_adds_q_branch_rows(tmp_path):
    result = MUSAResult(
        q=np.array([-3, -2, -1, 0, 1, 2, 3], dtype=float),
        scales=np.array([4000, 2000, 1000], dtype=float),
        dq=np.ones(7, dtype=float),
        tau=np.zeros(7, dtype=float),
        alpha=np.array([2.8, 2.6, 2.2, 2.0, 1.8, 1.6, 1.4], dtype=float),
        f_alpha=np.array([0.7, 1.0, 1.7, 2.0, 1.85, 1.5, 1.0], dtype=float),
        r2=np.ones(7, dtype=float) * 0.99,
        p_values=np.ones(7, dtype=float) * 0.01,
        alpha_r2=np.ones(7, dtype=float) * 0.99,
        f_alpha_r2=np.ones(7, dtype=float) * 0.99,
        min_r2=0.9,
        rejected_q=np.array([], dtype=float),
        rejected_r2=np.array([], dtype=float),
        rejected_alpha_r2=np.array([], dtype=float),
        rejected_f_alpha_r2=np.array([], dtype=float),
    )

    path = write_spectrum_fit_summary(tmp_path, result)

    with Path(path).open(newline="", encoding="utf-8") as fp:
        rows = list(csv.DictReader(fp))
    row_types = {row["fit_type"] for row in rows}
    assert "global_quadratic" in row_types
    assert "negative_q_branch" in row_types
    assert "nonnegative_q_branch" in row_types
    assert "positive_q_branch" in row_types
    global_row = next(row for row in rows if row["fit_type"] == "global_quadratic")
    assert global_row["alpha_q_monotonic"] == "decreasing"
