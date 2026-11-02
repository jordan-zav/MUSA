import itertools
import json

import numpy as np
import pytest
from shapely.geometry import LineString, box

from musa import MUSA
from musa.control import AnalysisCancelled
from musa.scaling import (
    ScalingOptions, assess_curve, assess_lineament_scaling, holm_adjust,
    monte_carlo_tail, renyi_entropy, write_scaling_reports, _relocate,
)


@pytest.mark.parametrize("q", [-4, 0, .5, 1, 1 + 1e-9, 2, 10])
def test_uniform_renyi_entropy_and_shannon_limit(q):
    assert renyi_entropy(np.ones(20), q) == pytest.approx(np.log(20), abs=1e-9)
    p = np.array([.1, .3, .6])
    if abs(q - 1) < 1e-7:
        expected = -np.sum(p * np.log(p))
    else:
        expected = np.log(np.sum(p ** q)) / (1 - q)
    assert renyi_entropy(p, q) == pytest.approx(expected, abs=1e-8)


def test_linear_dimension_is_invariant_to_scale_order_and_units():
    scales = np.geomspace(1, 100, 12)
    entropy = 10 + 1.3 * np.log(1 / scales)
    first = assess_curve(scales, entropy, ScalingOptions(.1))
    second = assess_curve(scales[::-1] * 1000, entropy[::-1], ScalingOptions(100))
    assert first["status"] == second["status"] == "compatible_finite_range"
    assert first["dimension"] == pytest.approx(1.3)
    assert second["dimension"] == pytest.approx(1.3)


@pytest.mark.parametrize("model", ["quadratic", "segmented"])
def test_curved_and_broken_scaling_is_rejected_by_nested_prediction(model):
    scales = np.geomspace(1, 100, 16)
    x = np.log(1 / scales)
    x -= x.mean()
    y = 5 + x + (.35 * x ** 2 if model == "quadratic" else 1.5 * np.maximum(x - .2, 0))
    result = assess_curve(scales, y, ScalingOptions(.1))
    assert result["status"] == "not_supported"
    assert model + "_predicts_better" in result["reasons"]
    assert result["models"][model]["cv_rmse"] < result["models"]["linear"]["cv_rmse"]


@pytest.mark.parametrize("scales,reason", [
    ([1, 2, 4, 8], "too_few_resolved_scales"),
    (np.linspace(1, 2, 10), "short_scaling_interval"),
    (np.geomspace(.01, 10, 12), "below_observation_resolution"),
])
def test_insufficient_information_is_not_negative_evidence(scales, reason):
    result = assess_curve(scales, np.log(1 / np.array(scales)), ScalingOptions(.1))
    assert result["status"] == "insufficient_information"
    assert reason in result["reasons"]
    assert result["dimension"] is None


def test_grid_instability_constant_curve_and_dominant_box_are_explicit():
    scales = np.geomspace(1, 100, 12)
    y = np.log(1 / scales)
    unstable = assess_curve(scales, y, ScalingOptions(.1), origin_dimensions=[.8, 1.2])
    assert "grid_sensitive_dimension" in unstable["reasons"]
    constant = assess_curve(scales, np.ones(12), ScalingOptions(.1))
    assert constant["status"] == "not_supported"
    assert "constant_curve" in constant["reasons"]
    dominant = assess_curve(scales, y, ScalingOptions(.1), min_effective=1.2)
    assert dominant["status"] == "insufficient_information"


def test_monte_carlo_ties_resolution_and_holm_under_dependence():
    assert monte_carlo_tail(10, [1] * 19) == .05
    assert monte_carlo_tail(1, [1] * 19) == 1
    assert holm_adjust([.01, .04, .03]) == pytest.approx([.03, .06, .06])
    assert holm_adjust([]) == []


def analyzer(lines, boundary=None, qs=(0, 1, 2)):
    return MUSA.from_line_geometries(lines, box(0, 0, 1000, 1000) if boundary is None else boundary,
                                     "EPSG:32718", q_values=qs)


def test_known_line_dimension_and_all_q_are_retained(tmp_path):
    model = analyzer([LineString([(0, 500), (1000, 500)])], qs=(-10, 0, 1, 2))
    result = assess_lineament_scaling(model, np.geomspace(2, 125, 12), ScalingOptions(1))
    assert len(result["q_results"]) == 4
    assert result["q_results"][0]["q"] == -10
    assert result["q_results"][0]["status"] == "insufficient_information"
    for row in result["q_results"][1:]:
        assert row["dimension"] == pytest.approx(1, abs=.04)
        assert row["status"] == "compatible_finite_range"
    paths = write_scaling_reports(tmp_path, [result])
    payload = json.loads(open(paths["scaling_support_json"], encoding="utf-8").read())
    assert payload["supports"][0]["null"]["p_holm"] is None


def test_finite_binomial_cantor_dimensions_follow_analytic_values():
    p, levels = .7, 7
    lines = []
    for bits in itertools.product((0, 1), repeat=levels):
        start = 1000 * sum(2 * b * 3. ** (-k - 1) for k, b in enumerate(bits))
        length = 1000 * 3. ** (-levels) * np.prod([p if b == 0 else 1 - p for b in bits]) / p ** levels
        center = start + 500 * 3. ** (-levels)
        lines.append(LineString([(center - length / 2, 500), (center + length / 2, 500)]))
    result = assess_lineament_scaling(analyzer(lines), np.geomspace(5, 100, 14), ScalingOptions(1))
    rows = {r["q"]: r for r in result["q_results"]}
    assert rows[0]["dimension"] == pytest.approx(np.log(2) / np.log(3), abs=.07)
    assert rows[2]["dimension"] == pytest.approx(-np.log(p * p + (1 - p) ** 2) / np.log(3), abs=.07)
    assert rows[0]["dimension"] - rows[2]["dimension"] > .1


def test_relocation_preserves_trace_shapes_lengths_and_containment_with_hole():
    boundary = box(0, 0, 1000, 1000).difference(box(400, 400, 600, 600))
    lines = [LineString([(50, 100), (100, 150), (200, 150)]), LineString([(700, 700), (800, 750)])]
    original = [line.wkb for line in lines]
    shifted = _relocate(lines, boundary, np.random.default_rng(42), 1000)
    assert [line.wkb for line in lines] == original
    for first, second in zip(lines, shifted):
        assert first.length == pytest.approx(second.length)
        np.testing.assert_allclose(np.diff(first.coords, axis=0), np.diff(second.coords, axis=0))
        assert boundary.covers(second)


def test_resolution_exclusions_and_partial_boundary_coverage_are_recorded():
    model = analyzer([LineString([(0, 500), (1000, 500)])])
    result = assess_lineament_scaling(model, [0.1, 1, 10, 300, 500], ScalingOptions(1))
    assert result["excluded_scales_m"] == [0.1, 300., 500.]
    low = assess_lineament_scaling(model, [10, 20], ScalingOptions(1), nominal_area=2e6)
    assert all(row["reasons"] == ["low_coverage"] for row in low["q_results"])


def test_coincident_segments_rejected_and_cancel_is_cooperative():
    line = LineString([(0, 500), (1000, 500)])
    with pytest.raises(ValueError, match="Deduplicate"):
        assess_lineament_scaling(analyzer([line, line]), [10, 20], ScalingOptions(1))
    with pytest.raises(AnalysisCancelled):
        assess_lineament_scaling(analyzer([line]), np.geomspace(2, 125, 12), ScalingOptions(1), cancelled=lambda: True)


@pytest.mark.parametrize("kwargs", [{"resolution_m": 0}, {"resolution_m": float("nan")},
                                      {"null_replicates": 5}, {"min_scales": 3}, {"seed": -1}])
def test_invalid_scientific_configuration_is_rejected(kwargs):
    values = {"resolution_m": 1, **kwargs}
    with pytest.raises(ValueError):
        ScalingOptions(**values).validate()


def test_invalid_probabilities_and_duplicate_scales_are_rejected():
    for probabilities in ([0, 1], [float("nan"), 1], [float("inf"), 1], [1e308, 1e308]):
        with np.errstate(over="ignore"), pytest.raises(ValueError):
            renyi_entropy(probabilities, 2)
    with pytest.raises(ValueError, match="Duplicate scales"):
        assess_curve([1, 1, 2], [1, 1, 2], ScalingOptions(1))
    bad = assess_curve(np.geomspace(1, 100, 8), np.arange(8), ScalingOptions(1), min_effective=float("nan"))
    assert bad["status"] == "insufficient_information"


def null_model():
    return analyzer([LineString([(100, float(y)), (900, float(y))]) for y in np.linspace(100, 900, 8)])


def null_options():
    # Relax fit gates ONLY here to exercise MC machinery irrespective of shape.
    # These tolerances do not serve as a calibration or scaling acceptance test.
    return ScalingOptions(1, min_r2=0, slope_tolerance=10, curvature_effect=10, null_replicates=19)


def test_conditional_null_is_reproducible_and_family_adjusted(tmp_path):
    scales = np.geomspace(2, 125, 8)
    a = assess_lineament_scaling(null_model(), scales, null_options())
    b = assess_lineament_scaling(null_model(), scales, null_options())
    assert a["null"]["status"] == "complete"
    assert a["null"] == b["null"]
    assert len(a["null"]["values"]) == 19
    assert a["null"]["p_value"] >= 1 / 20
    b["support_id"] = "untestable"
    b["null"]["p_value"] = None
    write_scaling_reports(tmp_path, [a, b])
    assert a["null"]["p_holm"] == min(1, 2 * a["null"]["p_value"])
    assert b["null"]["p_holm"] is None
    assert a["null"]["holm_family_size"] == 2


def test_failed_null_placement_is_not_replaced_until_success(monkeypatch):
    import musa.scaling as scaling
    monkeypatch.setattr(scaling, "_relocate", lambda *a, **kw: None)
    report = assess_lineament_scaling(null_model(), np.geomspace(2, 125, 8), null_options())
    assert report["null"]["status"] == "placement_failed_no_p_value"
    assert report["null"]["p_value"] is None


def test_degenerate_null_is_not_called_significant():
    report = assess_lineament_scaling(analyzer([LineString([(0, 500), (1000, 500)])]),
                                      np.geomspace(2, 125, 8), null_options())
    assert report["null"]["status"] == "degenerate_null_no_p_value"
    assert report["null"]["p_value"] is None
