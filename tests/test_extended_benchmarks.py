from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
import pytest
from scipy import sparse
from scipy.io import savemat
from shapely.geometry import LineString, box

from extended_benchmark_inputs import load_bristol, read_fracpaq, skeleton_lines, thin_mask, write_case, CRS_WKT
from run_extended_benchmarks import exact_cascade_validation, independent_mask_counts


def test_diagonal_skeleton_preserves_euclidean_length_and_isolated_pixels():
    mask = np.eye(5, dtype=bool)
    mask[0, 4] = True
    lines, domain, qa, skeleton = skeleton_lines(mask, pixel_size=2.)
    assert len(lines) == 4
    assert sum(line.length for line in lines) == pytest.approx(8*np.sqrt(2))
    assert qa["isolated_skeleton_pixels"] == 1
    assert skeleton.sum() == 6
    assert all(domain.covers(line) for line in lines)


def test_orthogonal_corner_has_no_artificial_diagonal_shortcut():
    mask = np.zeros((5, 5), bool)
    mask[2, 1:4] = True
    mask[1:3, 3] = True
    lines, _, _, _ = skeleton_lines(mask, already_thin=True)
    assert sum(line.length for line in lines) == pytest.approx(3.)


def test_thinning_reduces_thick_cross_and_preserves_arms():
    mask = np.zeros((21, 21), bool)
    mask[3:18, 9:12] = True
    mask[9:12, 3:18] = True
    skeleton = thin_mask(mask)
    assert skeleton.sum() < mask.sum()
    assert skeleton[5, 10] and skeleton[15, 10]
    assert skeleton[10, 5] and skeleton[10, 15]
    from scipy.ndimage import label
    assert label(skeleton, structure=np.ones((3, 3)))[1] == 1


def test_bristol_sparse_graph_deduplicates_undirected_edges_and_records_qa(tmp_path):
    path = tmp_path / "graph.mat"
    savemat(path, dict(node_xy=np.array([[0., 0.], [3., 0.], [3., 4.]]),
                      node_connectivity=sparse.csr_matrix([[1, 1, 0], [1, 0, 1], [0, 0, 0]])))
    lines, qa = load_bristol(path)
    assert len(lines) == 2
    assert sum(line.length for line in lines) == 7
    assert qa["asymmetric_entries"] == 2 and qa["self_loops"] == 1


def test_fracpaq_variable_length_rows_and_invalid_coordinate_pairs(tmp_path):
    path = tmp_path / "traces.txt"
    path.write_text("0\t0\t3\t0\t3\t4\t\n1\t1\t2\t2\n")
    assert [line.length for line in read_fracpaq(path)] == pytest.approx([7, np.sqrt(2)])
    path.write_text("1\t2\t3\n")
    with pytest.raises(ValueError, match="coordinate pairs"):
        read_fracpaq(path)


def test_exact_two_dimensional_cascade_spectra_and_independent_mask_capacity(tmp_path):
    result = exact_cascade_validation(tmp_path)
    assert result["passed"] and result["max_absolute_error"] < 1e-10
    assert next(row for row in result["q_results"] if row["q"] == 0)["estimated"]["dq"] == pytest.approx(2.)
    capacity = independent_mask_counts(np.ones((16, 16), bool), [1, 2, 4, 8])
    assert capacity["occupied_boxes"] == [256, 64, 16, 4]
    assert capacity["d0_slope"] == pytest.approx(2.)


def test_input_union_removes_coincident_multiplicity_with_recorded_lengths(tmp_path):
    line = LineString([(0, 5), (10, 5)])
    result = write_case(tmp_path, "duplicate", "test", [line, line], box(0, 0, 10, 10), CRS_WKT,
                        dict(units="model units"), .01, False)
    assert result["clipped_length"] == 20 and result["unique_length"] == 10
    assert result["original_features"] == 2 and result["unique_parts"] == 1
    assert result["scales"][0] == pytest.approx(10/128)
    assert result["scales"][-1] == pytest.approx(2.5)
    assert not result["georeferenced"]


def test_irregular_windows_keep_missing_observables_without_export_failure(tmp_path):
    import json
    from shapely.geometry import Polygon
    from run_extended_benchmarks import run_case
    result = write_case(tmp_path, "irregular", "test", [LineString([(10, 10), (80, 10)])],
                        Polygon([(0, 0), (100, 0), (0, 100)]), CRS_WKT, dict(units="model units"), .01, False)
    manifest = run_case(result, tmp_path)
    assert manifest["status"] == "complete"
    reports = json.loads((tmp_path / "results/irregular/scaling_support.json").read_text())["supports"]
    low = [report for report in reports if report["coverage"] < .8]
    assert low
    assert all(row["dimension"] is None for report in low for row in report["q_results"])
    changed = dict(result, resolution=.02)
    with pytest.raises(ValueError, match="nonmatching"):
        run_case(changed, tmp_path)
    assert json.loads((tmp_path / "results/irregular/run_manifest.json").read_text())["options"]["resolution_m"] == .01


def test_actual_geometric_canonical_core_matches_exact_weighted_cascade(tmp_path):
    from run_extended_benchmarks import geometric_cascade_validation
    result = geometric_cascade_validation(tmp_path, levels=4)
    assert result["passed"] and result["max_absolute_error"] < 1e-9
    assert result["line_features"] == 256


def test_interior_window_rule_improves_circle_coverage_without_changing_threshold():
    from shapely.geometry import Point
    circle = Point(0, 0).buffer(1, quad_segs=128)
    quarter = box(-1, -1, 0, 0)
    interior = box(-.75, -.75, .25, .25)
    assert circle.intersection(quarter).area/quarter.area == pytest.approx(np.pi/4, abs=1e-4)
    assert circle.intersection(quarter).area/quarter.area < .8
    assert circle.intersection(interior).area/interior.area > .98
