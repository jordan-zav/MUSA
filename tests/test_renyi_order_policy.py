"""Policy contracts on controlled curves; no T3 calibration is performed."""
import csv
import json
from dataclasses import replace

import numpy as np
import pytest
from shapely.geometry import LineString, box

from musa import MUSA
from musa import scaling


def model(qs=(0, 2)):
    return MUSA.from_line_geometries([LineString([(10, 50), (990, 50)])],
                                     box(0, 0, 1000, 1000), "EPSG:32718", q_values=qs)


@pytest.fixture
def controlled_curves(monkeypatch):
    state = {"null_calls": 0, "relocations": 0, "curved": False, "degenerate": False,
             "fail_effective_at": None, "fail_placement_at": None}

    def curves(lines, boundary, scales, qs, offsets, cancelled=None, *, singularities=False):
        x = np.log(1 / np.asarray(scales))
        out = np.empty((len(offsets), len(qs), len(scales)))
        if not singularities:
            state["null_calls"] += 1
        for i, q in enumerate(qs):
            if singularities:
                y = 10 + x if q == 0 else 5 + 1.2 * x if q == 2 else 7.5 + 1.1 * x if q == 1 else 12 + .8 * x
                if q == 0 and state["curved"]:
                    y = y + .3 * (x - x.mean()) ** 2
            else:
                delta = .04 if state["degenerate"] else -.1 + .01 * state["null_calls"]
                y = 10 + x if q == 0 else 5 + (1 - delta) * x
            out[:, i] = y
        effective = np.full(len(qs), 20.)
        if not singularities and state["null_calls"] == state["fail_effective_at"]:
            effective[0] = 1.
        if singularities:
            return out, effective, {name: out.copy() for name in ("tau", "alpha", "f_alpha")}
        return out, effective

    def relocate(lines, boundary, rng, attempts, cancelled=None):
        state["relocations"] += 1
        return None if state["relocations"] == state["fail_placement_at"] else lines

    monkeypatch.setattr(scaling, "_curves", curves)
    monkeypatch.setattr(scaling, "_relocate", relocate)
    return state


def options(policy="inform_q0_q2"):
    return scaling.ScalingOptions(1, null_replicates=19, renyi_order_policy=policy)


def assess(qs=(0, 2), policy="inform_q0_q2"):
    return scaling.assess_lineament_scaling(model(qs), np.geomspace(2, 125, 16), options(policy))


def test_legacy_default_keeps_order_veto(controlled_curves):
    assert scaling.ScalingOptions(1).renyi_order_policy == "legacy_block"
    report = assess(policy="legacy_block")
    assert report["null"]["status"] == "inconsistent_renyi_dimension_order"
    assert report["null"]["p_value"] is None
    assert controlled_curves["relocations"] == 0


def test_inverted_slopes_with_ordered_entropies_only_warn(controlled_curves):
    report = assess()
    curves = {(r["q"], r["scale_m"]): r["origin_entropies"] for r in report["curves"]}
    for scale in report["used_scales_m"]:
        assert np.all(np.asarray(curves[0, scale]) >= curves[2, scale])
    assert report["renyi_pair_order"]["delta02"] == pytest.approx(.2)
    assert report["renyi_pair_order"]["warning"] is True
    assert report["renyi_pair_order"]["message"]
    assert report["renyi_spectrum_order"]["scope"] == "requested_q"
    assert report["null"]["status"] == "complete"
    assert report["null"]["observed"] == pytest.approx(-.2)
    assert controlled_curves["relocations"] == 19


def test_curvature_still_blocks_inform_policy(controlled_curves):
    controlled_curves["curved"] = True
    report = assess()
    assert "quadratic_predicts_better" in report["q_results"][0]["reasons"]
    assert report["null"]["status"] == "scaling_not_supported_for_q0_q2"
    assert report["null"]["p_value"] is None
    assert controlled_curves["relocations"] == 0


@pytest.mark.parametrize("qs", [(0, 1), (1, 2), (-1, 1)])
def test_missing_pair_member_cannot_be_called_compatible(controlled_curves, qs):
    report = assess(qs)
    assert report["renyi_pair_order"]["status"] == "not_evaluated"
    assert report["renyi_pair_order"]["delta02"] is None
    assert report["renyi_pair_order"]["warning"] is None
    assert report["null"]["status"] == "requires_q0_and_q2"
    assert report["null"]["p_value"] is None


@pytest.mark.parametrize("failure", ["fail_effective_at", "fail_placement_at"])
def test_failed_replicate_keeps_prefix_and_is_not_replaced(controlled_curves, failure):
    controlled_curves[failure] = 3
    report = assess()
    expected = "null_support_failed_no_p_value" if failure == "fail_effective_at" else "placement_failed_no_p_value"
    assert report["null"]["status"] == expected
    assert report["null"]["p_value"] is None
    assert len(report["null"]["values"]) == 2
    assert controlled_curves["relocations"] == 3


def test_degenerate_null_keeps_abstention(controlled_curves):
    controlled_curves["degenerate"] = True
    report = assess()
    assert report["null"]["status"] == "degenerate_null_no_p_value"
    assert report["null"]["p_value"] is None
    assert controlled_curves["relocations"] == 19


def test_actual_partitions_and_null_do_not_depend_on_extra_q():
    lines = [LineString([(100, float(y)), (900, float(y))]) for y in np.linspace(100, 900, 8)]
    opts = scaling.ScalingOptions(1, min_r2=0, slope_tolerance=10, curvature_effect=10,
                                 null_replicates=19, renyi_order_policy="inform_q0_q2")
    reports = []
    for qs in [(0, 2), (0, 1, 2), (-4, 0, 1, 2), (2, 1, 0, -4)]:
        analyzer = MUSA.from_line_geometries(lines, box(0, 0, 1000, 1000), "EPSG:32718", q_values=qs)
        reports.append(scaling.assess_lineament_scaling(analyzer, np.geomspace(2, 125, 8), opts))
    assert reports[0]["null"]["status"] == "complete"
    for report in reports[1:]:
        assert report["null"] == reports[0]["null"]
        assert report["renyi_pair_order"] == reports[0]["renyi_pair_order"]
        for q in [0, 2]:
            assert next(r for r in report["q_results"] if r["q"] == q) == next(
                r for r in reports[0]["q_results"] if r["q"] == q)


def test_json_csv_expose_policy_pair_and_signed_margins(controlled_curves, tmp_path):
    report = assess()
    paths = scaling.write_scaling_reports(tmp_path, [report])
    payload = json.loads(open(paths["scaling_support_json"], encoding="utf-8").read())
    assert payload["version"] == 2
    assert payload["supports"][0]["renyi_order_policy"] == "inform_q0_q2"
    assert payload["supports"][0]["renyi_pair_order"]["warning"] is True
    assert report["null"]["p_holm"] == report["null"]["p_value"]  # native singleton family
    with open(paths["scaling_support_csv"], encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    for csvrow, fit in zip(rows, report["q_results"]):
        assert csvrow["renyi_order_policy"] == "inform_q0_q2"
        assert csvrow["renyi_pair_order_warning"] == "True"
        assert float(csvrow["delta02"]) == report["renyi_pair_order"]["delta02"]
        assert float(csvrow["margin_r2"]) == fit["r2"] - .98
        assert float(csvrow["margin_coverage"]) == 1 - .8
        assert json.loads(csvrow["scale_margins_json"]) == report["scale_margins"]
        for name in ["quadratic", "segmented"]:
            margin = fit["margins"]["curvature"][name]
            assert float(csvrow["margin_" + name + "_effect"]) == margin["effect"]
            assert float(csvrow["margin_" + name + "_cv_ratio"]) == margin["ratio"]


@pytest.mark.parametrize("delta,warning", [(.1, False), (np.nextafter(.1, np.inf), True)])
def test_pair_order_exact_boundary_uses_fixed_point_one(delta, warning):
    result = scaling._pair_order([{"q": 0, "dimension": 0.}, {"q": 2, "dimension": delta}])
    assert result["warning"] is warning
    assert result["margin"] == .1 - delta


def fake_models(monkeypatch, *, r2=1., slope=1., line_cv=.16, alternate_cv=.04):
    def models(x, y):
        return {name: {"sse": (1 - r2) * float(np.sum((y - y.mean()) ** 2)),
                       "cv_rmse": line_cv if name == "linear" else alternate_cv,
                       "coefficients": [0., slope] + ([] if name == "linear" else [0.]),
                       "knot_centered_log_inverse_scale": None if name != "segmented" else 0.}
                for name in ["linear", "quadratic", "segmented"]}
    monkeypatch.setattr(scaling, "_models", models)


@pytest.mark.parametrize("r2,fails", [(.98, False), (np.nextafter(.98, 0), True)])
def test_exact_r2_boundary(monkeypatch, r2, fails):
    fake_models(monkeypatch, r2=r2, alternate_cv=.16)
    scales = np.exp(np.linspace(0, 4, 16))
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1))
    assert ("poor_linear_fit" in result["reasons"]) is fails
    assert result["margins"]["r2"] == result["r2"] - .98


def test_exact_curvature_effect_and_ratio_boundaries(monkeypatch):
    scales = np.exp(np.linspace(0, 4, 16))
    for line, alt, zero_margin in [(.16, .04, "effect"), (1., .75, "ratio")]:
        fake_models(monkeypatch, line_cv=line, alternate_cv=alt)
        result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1))
        for name in ["quadratic", "segmented"]:
            assert result["margins"]["curvature"][name][zero_margin] == 0
            assert name + "_predicts_better" not in result["reasons"]
    fake_models(monkeypatch, line_cv=.16, alternate_cv=np.nextafter(.04, 0))
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1))
    assert "quadratic_predicts_better" in result["reasons"]


@pytest.mark.parametrize("effective,fails", [(2., False), (2. - 5e-11, False), (2. - 2e-10, True)])
def test_native_effective_box_boundary_preserves_tolerance(effective, fails):
    scales = np.geomspace(1, 10, 8)
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1), min_effective=effective)
    assert ("insufficient_effective_boxes" in result["reasons"]) is fails
    assert result["margins"]["min_effective_boxes"] == effective - 2.
    assert result["margins"]["scale_count"] == 0
    assert result["margins"]["span_decades"] == 0
    assert result["margins"]["resolution_m"] == 0


@pytest.mark.parametrize("spread,fails", [(.1, False), (np.nextafter(.1, np.inf), True)])
def test_exact_origin_stability_boundary(spread, fails):
    scales = np.geomspace(1, 10, 8)
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1),
                                  origin_dimensions=[0, spread])
    assert ("grid_sensitive_dimension" in result["reasons"]) is fails
    assert result["margins"]["origin_dimension_range"] == .1 - spread


@pytest.mark.parametrize("spread,fails", [(.1, False), (np.nextafter(.1, np.inf), True)])
def test_exact_leave_scale_out_boundary(monkeypatch, spread, fails):
    fake_models(monkeypatch, slope=0., alternate_cv=.16)
    monkeypatch.setattr(scaling, "_fit", lambda *args: (0., np.array([0., spread]), None))
    scales = np.exp(np.linspace(0, 4, 16))
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1))
    assert ("scale_sensitive_dimension" in result["reasons"]) is fails
    assert result["margins"]["leave_scale_out_range"] == .1 - spread


@pytest.mark.parametrize("slope,fails", [(-.1, False), (2.1, False),
                                        (np.nextafter(-.1, -np.inf), True),
                                        (np.nextafter(2.1, np.inf), True)])
def test_exact_planar_dimension_boundaries(monkeypatch, slope, fails):
    fake_models(monkeypatch, slope=slope, alternate_cv=.16)
    monkeypatch.setattr(scaling, "_fit", lambda *args: (0., np.array([0., slope]), None))
    scales = np.exp(np.linspace(0, 4, 16))
    result = scaling.assess_curve(scales, np.log(1 / scales), scaling.ScalingOptions(1))
    assert ("dimension_outside_planar_range" in result["reasons"]) is fails
    assert result["margins"]["dimension_lower"] == slope + .1
    assert result["margins"]["dimension_upper"] == 2.1 - slope


def test_coverage_and_maximum_box_boundaries_are_unchanged():
    opts = scaling.ScalingOptions(1, renyi_order_policy="inform_q0_q2")
    scales = np.geomspace(1, 250, 16)
    report = scaling.assess_lineament_scaling(model(), scales, opts, nominal_area=1e6 / .8)
    assert report["margins"]["coverage"] == 0
    assert report["used_scales_m"][0] == 250
    assert report["scale_margins"][-1]["maximum_box_m"] == 0
    below = scaling.assess_lineament_scaling(model(), scales, opts,
                                            nominal_area=np.nextafter(1e6 / .8, np.inf))
    assert below["null"]["status"] == "insufficient_information"
    assert below["q_results"][0]["reasons"] == ["low_coverage"]
    assert below["renyi_pair_order"]["status"] == "not_evaluated"


def test_invalid_policy_is_rejected_and_dataclass_default_is_compatible():
    for value in ["unknown", "", None]:
        with pytest.raises(ValueError, match="renyi_order_policy"):
            scaling.ScalingOptions(1, renyi_order_policy=value).validate()
    assert replace(scaling.ScalingOptions(1), renyi_order_policy="inform_q0_q2").validate()
