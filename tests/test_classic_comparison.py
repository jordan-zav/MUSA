import csv
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import linregress
from shapely.geometry import LineString, box

from musa import MUSA, classic_box_counting, write_classic_comparison
from musa.control import AnalysisCancelled
from musa.partition import line_cell_segments
from musa.scaling import ScalingOptions, assess_lineament_scaling, renyi_entropy
from musa.workflow import RunConfig, execute_analysis


def model(lines, boundary=None):
    return MUSA.from_line_geometries(lines, boundary if boundary is not None else box(0, 0, 1000, 1000),
                                     "EPSG:32718", q_values=[0, 1, 2])


def test_classic_matches_independent_h0_slope_on_same_grid_and_interval(tmp_path):
    lines = [LineString([(10, 15), (920, 870)]), LineString([(40, 700), (800, 130)])]
    analyzer = model(lines)
    scales, origin = np.geomspace(5, 200, 12), (13., -27.)
    result = classic_box_counting(analyzer, scales, origin=origin)
    entropies, counts = [], []
    for scale in scales:
        masses = {}
        for key, length, _ in line_cell_segments(lines, scale, origin):
            masses[key] = masses.get(key, 0) + length
        counts.append(len(masses))
        probabilities = np.array(list(masses.values()))
        entropies.append(renyi_entropy(probabilities / probabilities.sum(), 0))
    fit = linregress(np.log(1 / scales), entropies)
    assert result["occupied_boxes"] == counts
    assert result["dimension"] == pytest.approx(fit.slope, abs=1e-12)
    assert result["r2"] == pytest.approx(fit.rvalue ** 2, abs=1e-12)
    files = write_classic_comparison(tmp_path, result)
    assert json.loads(Path(files["classic_comparison_json"]).read_text())["comparison"] == result
    with Path(files["classic_comparison_csv"]).open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(scales)
    assert all(r["comparison_only"] == "True" and r["scaling_diagnostic"] == "not_applied" for r in rows)


def test_finite_cantor_has_high_classic_r2_and_insufficient_musa_support():
    # Existing analytic geometry generator, evaluated only on four declared scales.
    path = Path(__file__).resolve().parents[1] / "scripts/run_author_benchmarks.py"
    spec = importlib.util.spec_from_file_location("classic_analytic_controls", path)
    controls = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controls)
    analyzer = model(controls.cantor(.5), box(0, 0, controls.SIDE, controls.SIDE))
    scales = controls.SIDE / 3. ** np.arange(2, 6)
    result = classic_box_counting(analyzer, scales)
    assessment = assess_lineament_scaling(analyzer, scales, ScalingOptions(.01))
    assert result["r2"] > .99
    assert result["dimension"] == pytest.approx(np.log(2) / np.log(3), abs=.02)
    q0 = next(row for row in assessment["q_results"] if row["q"] == 0)
    assert q0["status"] == "insufficient_information"
    assert "too_few_resolved_scales" in q0["reasons"]


def test_comparison_preserves_all_existing_workflow_products_and_old_recipes(tmp_path):
    rng = np.random.default_rng(24)
    lines = [LineString([(0, y), (1000, y + 30)]) for y in rng.uniform(0, 960, 25)]
    config = RunConfig(mother_cell_m=1000, scaling_resolution_m=1, q_min=0, q_max=2,
                       local=False, structural=False, plots=False, gis=False, min_r2=0)
    recipe = config.recipe()
    del recipe["parameters"]["classic_comparison"]
    assert RunConfig.from_recipe(recipe).classic_comparison is False
    first = execute_analysis(model(lines), config, tmp_path / "default")
    second = execute_analysis(model(lines), replace(config, classic_comparison=True), tmp_path / "comparison")
    assert not (tmp_path / "default/classic_comparison.json").exists()
    for filename, digest in first["files"].items():
        if filename not in ("recipe.json",):
            assert second["files"][filename] == digest, filename
    assert (tmp_path / "comparison/classic_comparison.json").exists()


def test_empty_support_constant_counts_validation_and_cancellation():
    analyzer = model([LineString([(0, 500), (1000, 500)])])
    constant = classic_box_counting(analyzer, [2000, 3000])
    assert constant["r2"] is None
    empty = model([LineString([(0, 500), (1000, 500)])])
    empty._line_geometries = []
    result = classic_box_counting(empty, [10, 20])
    assert result["dimension"] is None and result["calculation_status"] == "empty_support"
    for scales in ([10], [10, 10], [0, 10], [float("nan"), 10]):
        with pytest.raises(ValueError):
            classic_box_counting(analyzer, scales)
    with pytest.raises(AnalysisCancelled):
        classic_box_counting(analyzer, [10, 20], cancelled=lambda: True)


def test_numpy_partition_counts_serialize_without_acceleration(monkeypatch, tmp_path):
    # QGIS can use the Python partition fallback with NumPy scalar lengths.
    monkeypatch.setattr("musa.classic.line_masses", lambda *args: {(0, 0): np.float64(12.)})
    result = classic_box_counting(model([LineString([(0, 500), (1000, 500)])]), [10, 20])
    assert all(type(count) is int for count in result["occupied_boxes"])
    write_classic_comparison(tmp_path, result)
