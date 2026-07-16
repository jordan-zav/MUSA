import csv
import math
from pathlib import Path

from musa.core import MUSA


def test_zeta_sensitivity_summary_matches_profiles(tmp_path):
    rows = [
        {"profile": "baseline", "mother_ix": 0, "mother_iy": 0, "q": 2, "alpha_w": 1.0, "f_alpha_w": 0.8, "alpha_w_r2": 0.95, "f_alpha_w_r2": 0.96},
        {"profile": "baseline", "mother_ix": 1, "mother_iy": 0, "q": 2, "alpha_w": 1.2, "f_alpha_w": 0.9, "alpha_w_r2": 0.92, "f_alpha_w_r2": 0.93},
        {"profile": "soft", "mother_ix": 0, "mother_iy": 0, "q": 2, "alpha_w": 1.1, "f_alpha_w": 0.82, "alpha_w_r2": 0.91, "f_alpha_w_r2": 0.94},
        {"profile": "soft", "mother_ix": 1, "mother_iy": 0, "q": 2, "alpha_w": 1.5, "f_alpha_w": 0.95, "alpha_w_r2": 0.80, "f_alpha_w_r2": 0.91},
        {"profile": "mass-heavy", "mother_ix": 0, "mother_iy": 0, "q": 2, "alpha_w": 0.95, "f_alpha_w": 0.79, "alpha_w_r2": 0.99, "f_alpha_w_r2": 0.99},
    ]
    source = tmp_path / "multifractal_mother_zeta_sensitivity.csv"
    with source.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    out = MUSA.export_zeta_sensitivity_summary(tmp_path)

    with Path(out).open(newline="", encoding="utf-8") as fp:
        summary = list(csv.DictReader(fp))
    soft = next(row for row in summary if row["profile"] == "soft")
    assert soft["q"] == "2.0"
    assert soft["mother_count"] == "2"
    assert math.isclose(float(soft["alpha_w_median"]), 1.3, abs_tol=1e-9)
    assert math.isclose(float(soft["median_abs_delta_vs_baseline"]), 0.2, abs_tol=1e-9)
    assert math.isclose(float(soft["unstable_fraction"]), 0.5, abs_tol=1e-9)
    assert math.isclose(float(soft["reliable_fraction"]), 0.5, abs_tol=1e-9)
