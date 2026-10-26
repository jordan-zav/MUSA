import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, box

from musa import MUSA
from musa import analyze_moving_windows
from musa.candidates import classify_candidate_evidence
from musa.proximity import analyze_fault_proximity
from musa.structural import compute_lineament_mother_structural_stats
from test_candidates import evidence_fixture
from test_proximity import model


def test_shared_border_length_and_cell_threshold_are_segmentation_invariant():
    coords = [(.2,.2),(1,.2),(1,1.8),(1.8,1.8)]
    whole = LineString(coords)
    pieces = [LineString([a,b]) for a,b in zip(coords[:-1],coords[1:])]
    for threshold in (0, .9):
        a = MUSA._line_length_cells([whole], 1, np.zeros(2), threshold)
        b = MUSA._line_length_cells(pieces, 1, np.zeros(2), threshold)
        assert a == pytest.approx(b)
        if threshold == 0:
            assert sum(a.values()) == pytest.approx(whole.length)


def test_partition_conserves_random_lines_and_reversal():
    rng = np.random.default_rng(12)
    for _ in range(20):
        coords = rng.uniform(-5, 5, (8,2))
        line = LineString(coords)
        a = MUSA._line_length_cells([line], .7, np.array([.3,-.2]))
        b = MUSA._line_length_cells([LineString(coords[::-1])], .7, np.array([.3,-.2]))
        assert sum(a.values()) == pytest.approx(line.length)
        assert a == pytest.approx(b, abs=1e-12)


def test_curved_line_orientation_uses_primitive_lengths():
    coords = [(100,100),(900,100),(900,900)]
    variants = [[LineString(coords)], [LineString(coords[:2]),LineString(coords[1:])]]
    rows = [compute_lineament_mother_structural_stats(v,box(0,0,1000,1000),1000)[0] for v in variants]
    for row in rows:
        assert row['measure_sum_m'] == pytest.approx(1600)
        assert row['mean_resultant_length'] == pytest.approx(0,abs=1e-12)
        assert row['anisotropy_ratio'] == pytest.approx(1)


def test_structural_cells_conserve_shared_and_outer_boundary_length():
    lines = [LineString([(1,0),(1,2)]), LineString([(0,2),(2,2)])]
    rows = compute_lineament_mother_structural_stats(lines,box(0,0,2,2),1)
    assert sum(r['measure_sum_m'] for r in rows) == pytest.approx(4)


def test_structural_partition_preserves_lines_on_hole_boundaries():
    boundary = box(0,0,3,3).difference(box(1,1,2,2))
    lines = [LineString([(1,1),(1,2),(2,2),(2,1),(1,1)])]
    rows = compute_lineament_mother_structural_stats(lines,boundary,1)
    assert sum(r['measure_sum_m'] for r in rows) == pytest.approx(4)


def test_window_outer_edges_do_not_create_zero_area_boxes():
    import json
    a = model([LineString([(0,0),(1000,0),(1000,1000),(0,1000),(0,0)])])
    windows,_,_ = analyze_moving_windows(a,[1000],500,centers=[(500,500)])
    diagnostics = json.loads(windows.iloc[0].scale_diagnostics_json)
    assert diagnostics[0]['occupied_boxes'] == 4
    assert all(d['mass_m'] == pytest.approx(4000) for d in diagnostics)
    assert all(d['occupancy'] <= 1 for d in diagnostics)


def test_proximity_invariant_to_endpoint_splits_and_input_order():
    a = LineString([(100,100),(900,100)])
    b = LineString([(100,200),(900,200)])
    pieces = [LineString([(100,100),(500,100)]),LineString([(500,100),(900,100)])]
    outputs = [analyze_fault_proximity(model(v),[150])[0] for v in ([a,b],pieces+[b],[b]+pieces[::-1])]
    assert all(len(r)==1 for r in outputs)
    assert all(r.geometry.iloc[0].equals(outputs[0].geometry.iloc[0]) for r in outputs)


def test_small_positive_contrast_below_phase_spread_is_not_supported_high_class():
    args = evidence_fixture(widths=(.100001,)*3, shifted_widths=(.099,)*3)
    seeds,bg,primary,shifted,sizes = args
    bg.loc[bg.q==2,'alpha']=1.4
    result,_,_ = classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    row=result.iloc[0]
    assert row.score == 100  # Descriptive rank is preserved, not a probability.
    assert row.relative_class == 3
    assert pd.isna(row.evidence_class)
    assert row.class_status == 'contrast_below_phase_resolution'
