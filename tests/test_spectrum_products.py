import csv
import json
import sqlite3
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import LineString, box

from musa import MUSA
from musa.control import AnalysisCancelled
from musa.scaling import ScalingOptions, assess_curve, assess_lineament_scaling, write_scaling_reports
from musa.spectrum import fit_quadratic_spectrum
from musa.spectrum_products import (
    _point, identity_diagnostics, summarize_spectrum, write_spectrum_products,
    list_spectra, read_spectrum, spectrum_figure,
)


def lognormal_points(qs=(-1, 0, 1, 2, 3)):
    d, a = 1.5, .1
    return [_point(q, {"dq": d - a * q, "tau": (q - 1) * (d - a * q),
                       "alpha": d + a - 2 * a * q, "f_alpha": d - a * q * q}, True, "accepted") for q in qs]


def result_from(points):
    return SimpleNamespace(q=np.array([p["q"] for p in points]),
                           **{name: np.array([p[name] for p in points]) for name in ("dq", "tau", "alpha", "f_alpha")})


def test_peak_definitions_remain_distinct_and_three_points_are_descriptive():
    points = [_point(0, dict(dq=1, tau=-1, alpha=2, f_alpha=1), True, "accepted"),
              _point(1, dict(dq=1.1, tau=0, alpha=1.4, f_alpha=1.4), True, "accepted"),
              _point(2, dict(dq=.7, tau=.7, alpha=.9, f_alpha=1.1), True, "accepted")]
    summary = summarize_spectrum(points)
    assert summary["alpha_q0"] == 2
    assert summary["observed_peak_alpha"] == 1.4
    assert not np.isclose(summary["fit_peak_alpha"], 1.4)
    assert summary["fit_status"] == "interpolation_only"
    assert not summary["observed_peak_at_q_edge"]


def test_q0_missing_or_rejected_never_uses_nearest_q_or_interpolation():
    points = lognormal_points([.1, 1, 2])
    assert summarize_spectrum(points)["alpha_q0_status"] == "q0_not_evaluated"
    points = lognormal_points()
    points[1]["accepted"] = False
    assert summarize_spectrum(points)["alpha_q0"] is None
    assert summarize_spectrum(points)["alpha_q0_status"] == "q0_not_supported"


def test_monofractal_ties_and_degenerate_fit_are_retained_without_warning():
    points = [_point(q, dict(dq=1, tau=q - 1, alpha=1, f_alpha=1), True, "accepted") for q in (-1, 0, 1, 2)]
    summary = summarize_spectrum(points)
    assert summary["observed_peak_tied"]
    assert summary["observed_peak_qs"] == [-1, 0, 1, 2]
    assert summary["observed_peak_alpha"] == 1
    assert summary["alpha_q0"] == 1
    assert summary["fit_peak_alpha"] is None
    assert summary["fit_status"] == "degenerate_alpha_or_rank"
    assert fit_quadratic_spectrum(np.ones(3), np.ones(3))["fit_valid"] == 0
    assert fit_quadratic_spectrum(np.array([1, 1, 2]), np.array([1, 2, 3]))["fit_valid"] == 0


def test_equal_heights_at_distinct_alpha_have_no_arbitrary_peak():
    points = [_point(0, dict(dq=1, tau=-1, alpha=2, f_alpha=1), True, "accepted"),
              _point(1, dict(dq=1, tau=0, alpha=1, f_alpha=1), True, "accepted"),
              _point(2, dict(dq=0, tau=0, alpha=.5, f_alpha=1), True, "accepted")]
    summary = summarize_spectrum(points)
    assert summary["observed_peak_alpha"] is None
    assert summary["observed_peak_alphas"] == [2, 1, .5]


def test_boundary_peak_is_not_extrapolated_and_inconsistent_points_are_not_fit():
    summary = summarize_spectrum(lognormal_points([1, 2, 3]))
    assert summary["observed_peak_at_q_edge"]
    assert summary["fit_peak_alpha"] is None
    assert summary["fit_status"] == "nonconcave_constant_or_vertex_outside_range"
    points = lognormal_points()
    bad = points[1]
    bad["f_alpha"] += .4
    bad["identities"] = identity_diagnostics(bad["q"], *(bad[n] for n in ("dq", "tau", "alpha", "f_alpha")))
    summary = summarize_spectrum(points)
    assert summary["identity_status"] == "discrepancy"
    assert summary["alpha_q0"] is None


def test_same_probability_features_satisfy_identities_and_tau_one_is_not_a_fit():
    model = MUSA.from_line_geometries([LineString([(0, 500), (1000, 500)])],
                                     box(0, 0, 1000, 1000), "EPSG:32718", q_values=[0, 1, 2])
    # Resolve the straight-line asymptote well below its total length; partial
    # edge boxes otherwise bias alpha(q=0) at finite coarse scales.
    report = assess_lineament_scaling(model, np.geomspace(.5, 8, 12), ScalingOptions(.1))
    for row in report["q_results"]:
        assert row["identities"]["status"] == "consistent"
        assert row["alpha"] == pytest.approx(1, abs=.04)
        assert row["f_alpha"] == pytest.approx(1, abs=.04)
        assert row["tau"] == pytest.approx(row["q"] - 1, abs=.04)
        if row["q"] == 1:
            assert row["observables"]["tau"]["status"] == "identity"
            assert row["observables"]["tau"]["r2"] is None
    for feature in report["curves"]:
        assert feature["f_alpha_feature"] == pytest.approx(
            feature["q"] * feature["alpha_feature"] - feature["tau_feature"], abs=1e-10)


def test_tau_can_be_negative_and_alpha_can_exceed_embedding_dimension():
    scales = np.geomspace(1, 100, 12)
    x = np.log(1 / scales)
    tau = assess_curve(scales, -x, ScalingOptions(1), observable="tau")
    alpha = assess_curve(scales, 3 * x, ScalingOptions(1), observable="alpha")
    assert tau["status"] == alpha["status"] == "compatible_finite_range"
    assert assess_curve(scales, 3 * x, ScalingOptions(1))["status"] == "not_supported"


def test_readonly_index_preserves_sources_all_q_and_json_nulls(tmp_path):
    model = MUSA.from_line_geometries([LineString([(0, 500), (1000, 500)])],
                                     box(0, 0, 1000, 1000), "EPSG:32718", q_values=[0, 1, 2])
    report = assess_lineament_scaling(model, np.geomspace(2, 125, 8), ScalingOptions(1))
    write_scaling_reports(tmp_path, [report])
    points = lognormal_points([0, 1, 2])
    paths = write_spectrum_products(tmp_path, result=result_from(points), requested_q=[-1, 0, 1, 2])
    index = list_spectra(paths["spectrum_curves"])
    assert len(index) == 2
    selected = read_spectrum(paths["spectrum_curves"], "analysis|global|canonical")
    assert len(selected["points"]) == 4
    assert selected["points"][0]["dq"] is None
    assert not selected["points"][0]["accepted"]
    assert selected["summary"]["valid_q_count"] == 3
    with open(paths["spectrum_summary"], newline="", encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 2
    with pytest.raises(KeyError):
        read_spectrum(paths["spectrum_curves"], "'; DROP TABLE spectra; --")
    absent = tmp_path / "absent.sqlite"
    with pytest.raises(sqlite3.OperationalError):
        list_spectra(absent)
    assert not absent.exists()


def test_cancelled_rebuild_preserves_previous_complete_cache(tmp_path):
    points = lognormal_points()
    paths = write_spectrum_products(tmp_path, result=result_from(points), requested_q=[p["q"] for p in points])
    from pathlib import Path
    before = Path(paths["spectrum_curves"]).read_bytes()
    with pytest.raises(AnalysisCancelled):
        write_spectrum_products(tmp_path, result=result_from(points), requested_q=[p["q"] for p in points], cancelled=lambda: True)
    assert Path(paths["spectrum_curves"]).read_bytes() == before


def test_figure_has_four_panels_and_does_not_bridge_rejected_q(tmp_path):
    points = lognormal_points()
    points[2]["accepted"] = False
    spectrum = dict(support_id="window_2_1000m", source="analysis", estimator="canonical", support_basis="legacy_fit",
                    points=points, summary=summarize_spectrum(points))
    figure = spectrum_figure(spectrum)
    assert len(figure.axes) >= 4
    assert np.isnan(figure.axes[0].lines[0].get_ydata()[2])
    assert np.isnan(figure.axes[3].lines[0].get_xdata()[2])
    figure.savefig(tmp_path / "curves.png")
    figure.savefig(tmp_path / "curves.svg")
    assert (tmp_path / "curves.png").stat().st_size > 1000
    assert "<svg" in (tmp_path / "curves.svg").read_text(encoding="utf-8")
    json.dumps(spectrum, allow_nan=False)
