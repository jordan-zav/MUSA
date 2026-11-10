"""Two-sided null tail and coarse-end trimming options of the scaling diagnostic."""
from dataclasses import replace

import numpy as np
import pytest
from shapely.geometry import LineString, box

from musa import MUSA
from musa.workflow import RunConfig
from musa import scaling


def lines_model(lines, qs=(0, 2)):
    return MUSA.from_line_geometries(lines, box(0, 0, 1000, 1000), "EPSG:32718", q_values=qs)


def grid_lines(n=8):
    return [LineString([(100, float(y)), (900, float(y))]) for y in np.linspace(100, 900, n)]


LOOSE = dict(min_r2=0, slope_tolerance=10, curvature_effect=10, renyi_order_policy="inform_q0_q2")


def test_defaults_keep_legacy_behaviour():
    options = scaling.ScalingOptions(1)
    assert options.null_tail == "upper"
    assert options.coarse_trim_min_effective_q2 == 0
    config = RunConfig()
    assert config.scaling_null_tail == "upper"
    assert config.scaling_coarse_trim_min_effective_q2 == 0


@pytest.mark.parametrize("kwargs", [{"null_tail": "lower"}, {"coarse_trim_min_effective_q2": .5},
                                    {"coarse_trim_min_effective_q2": float("nan")}])
def test_invalid_options_are_rejected(kwargs):
    with pytest.raises(ValueError):
        scaling.ScalingOptions(1, **kwargs).validate()
    with pytest.raises(ValueError):
        RunConfig(scaling_support=True, scaling_resolution_m=1,
                  **{("scaling_" + k if k == "null_tail" else "scaling_" + k): v
                     for k, v in kwargs.items()}).validate()


def test_two_sided_p_matches_definition_and_ties_count_against_rejection():
    values = np.array([1., 2., 2., 3., 4., 5., 6., 7., 8., 9.])
    result = scaling.monte_carlo_two_sided(2., values)
    assert result["p_upper"] == pytest.approx(10 / 11)
    assert result["p_lower"] == pytest.approx(4 / 11)
    assert result["p_value"] == pytest.approx(8 / 11)
    extreme = scaling.monte_carlo_two_sided(-1., values)
    assert extreme["p_value"] == pytest.approx(2 / 11)
    assert scaling.monte_carlo_two_sided(99., values)["p_value"] == pytest.approx(2 / 11)


def test_two_sided_engine_report_uses_same_replicates_as_upper():
    lines = grid_lines()
    upper = scaling.ScalingOptions(1, null_replicates=19, **LOOSE)
    two = replace(upper, null_tail="two_sided")
    a = scaling.assess_lineament_scaling(lines_model(lines), np.geomspace(2, 125, 8), upper)
    b = scaling.assess_lineament_scaling(lines_model(lines), np.geomspace(2, 125, 8), two)
    assert a["null"]["status"] == b["null"]["status"] == "complete"
    assert a["null"]["values"] == b["null"]["values"]
    assert a["null"]["tail"] == "upper" and b["null"]["tail"] == "two_sided"
    expected = scaling.monte_carlo_two_sided(b["null"]["observed"], b["null"]["values"])
    assert b["null"]["p_value"] == pytest.approx(expected["p_value"])
    assert b["null"]["p_upper"] == pytest.approx(a["null"]["p_value"])
    assert b["null"]["minimum_p"] == pytest.approx(2 / 20)
    assert b["null"]["direction_vs_null_median"] in ("above", "below", "equal")


def test_holm_resolution_accounts_for_two_sided_minimum(tmp_path):
    lines = grid_lines()
    opts = scaling.ScalingOptions(1, null_replicates=19, null_tail="two_sided", **LOOSE)
    report = scaling.assess_lineament_scaling(lines_model(lines), np.geomspace(2, 125, 8), opts)
    scaling.write_scaling_reports(tmp_path, [report])
    assert report["null"]["minimum_possible_holm_p"] == pytest.approx(2 / 20)
    assert report["null"]["resolution_sufficient_for_family_at_0_05"] is False


def test_trimming_off_leaves_scales_untouched():
    report = scaling.assess_lineament_scaling(lines_model(grid_lines()), np.geomspace(2, 125, 8),
                                              scaling.ScalingOptions(1, **LOOSE))
    assert "scale_trimming" not in report
    assert len(report["used_scales_m"]) == 8


def test_trimming_removes_only_coarse_scales_with_few_effective_boxes():
    # Three short horizontal traces: coarse boxes hold all length in very few cells.
    lines = [LineString([(400, y), (600, y)]) for y in (480., 500., 520.)]
    scales = np.geomspace(2, 250, 12)
    opts = scaling.ScalingOptions(1, coarse_trim_min_effective_q2=4, **LOOSE)
    report = scaling.assess_lineament_scaling(lines_model(lines), scales, opts)
    trim = report["scale_trimming"]
    assert trim["removed_count"] > 0
    effective = dict((s, e) for s, e in trim["effective_q2_by_scale"])
    assert all(effective[s] < 4 for s in trim["removed"])
    kept = report["used_scales_m"]
    assert effective[max(kept)] >= 4
    assert min(trim["removed"]) > max(kept)
    assert set(report["excluded_scales_m"]) >= set(trim["removed"])
    assert all(not m["used"] for m in report["scale_margins"] if m["scale_m"] in trim["removed"])


def test_trimming_below_one_decade_abstains_without_replicates(monkeypatch):
    calls = {"n": 0}
    original = scaling._relocate

    def counting(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(scaling, "_relocate", counting)
    lines = [LineString([(400, y), (600, y)]) for y in (480., 500., 520.)]
    opts = scaling.ScalingOptions(1, null_replicates=19, coarse_trim_min_effective_q2=1e6, **LOOSE)
    report = scaling.assess_lineament_scaling(lines_model(lines), np.geomspace(2, 250, 12), opts)
    assert report["scale_trimming"]["kept_count"] == 0
    assert report["null"]["p_value"] is None
    assert all(r["status"] == "insufficient_information" for r in report["q_results"])
    assert calls["n"] == 0


def test_trimming_matches_campaign_rule():
    """Same result as the archived campaign rule: per-scale q=2 effective boxes, coarse first."""
    lines = [LineString([(400, y), (600, y)]) for y in (480., 500., 520.)] + grid_lines(3)
    boundary = box(0, 0, 1000, 1000)
    scales = np.geomspace(2, 250, 12)
    offsets = np.array([(.137, .271), (.637, .271), (.137, .771), (.637, .771)])
    ordered = sorted(scales, reverse=True)
    effective = [float(scaling._curves(lines, boundary, np.array([s]), np.array([2.]), offsets)[1][0])
                 for s in ordered]
    k = 0
    while k < len(ordered) and effective[k] < 4:
        k += 1
    kept, trim = scaling._trim_coarse(lines, boundary, scales, offsets, 4.0)
    assert kept.tolist() == ordered[k:]
    assert trim["removed_count"] == k
