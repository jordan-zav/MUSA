import numpy as np
import geopandas as gpd
import pytest
from shapely.geometry import LineString, box

from musa import MUSA, analyze_moving_windows, export_moving_windows
from musa.moving import fracture_nodes
from musa.structural import compute_lineament_mother_structural_stats


def analyzer(lines, boundary=box(0, 0, 1000, 1000)):
    return MUSA(gpd.GeoDataFrame(geometry=lines, crs=32618),
                boundary=gpd.GeoDataFrame(geometry=[boundary], crs=32618), q_values=[0, 1, 2, 8])


def test_three_crossing_lines_are_one_junction_and_segmentation_invariant():
    lines = [LineString([(0, 500), (1000, 500)]), LineString([(500, 0), (500, 1000)]),
             LineString([(0, 0), (1000, 1000)])]
    nodes = fracture_nodes(lines, box(0, 0, 1000, 1000))
    assert [(n['degree'], n['boundary_node']) for n in nodes if n['degree'] >= 3] == [(6, False)]
    split = [LineString([(0, 500), (500, 500)]), LineString([(500, 500), (1000, 500)])]
    assert fracture_nodes(split + lines[1:], box(0, 0, 1000, 1000)) == nodes


def test_density_uses_observed_area():
    row = compute_lineament_mother_structural_stats(
        [LineString([(0, 250), (500, 250)])], box(0, 0, 500, 1000), 1000)[0]
    assert row['mother_area_km2'] == .5
    assert row['coverage_fraction'] == .5
    assert row['density_m_per_km2'] == 1000


def test_uniform_line_has_dimension_one_and_duplicates_do_not_change_mass(tmp_path):
    line = LineString([(0, 500), (1000, 500)])
    a = analyzer([line, line])
    windows, nodes, config = analyze_moving_windows(a, [1000], 500, centers=[(500, 500)])
    assert np.allclose(windows.dq, 1)
    assert np.allclose(windows.alpha, 1)
    assert np.allclose(windows.f_alpha, 1)
    assert (windows.length_m == 1000).all()
    assert windows.accepted.all()
    paths = export_moving_windows(a, tmp_path, [1000], 500, centers=[(500, 500)])
    saved = gpd.read_file(paths['moving_gis'], layer='window_spectra')
    assert len(saved) == 4
    assert saved.geometry.area.eq(1000000).all()
    assert config['measure'].startswith('unique')
    import sqlite3
    with sqlite3.connect(paths['moving_gis']) as db:
        styles = db.execute('SELECT f_table_name,useAsDefault FROM layer_styles').fetchall()
    assert set(styles) == {('window_spectra', 1), ('structural_candidates', 1), ('topology_controls', 1), ('trap_candidates', 1), ('node_classes', 1), ('pathway_multifractal', 1)}
    controls = gpd.read_file(paths['moving_gis'], layer='topology_controls')
    assert (controls.role != 'structural_candidate').all()
    assert gpd.read_file(paths['moving_gis'], layer='structural_candidates').empty


def test_edge_coverage_and_high_q_are_not_silently_accepted():
    lines = [LineString([(0, 500), (1000, 500)]), LineString([(0, 510), (20, 510)])]
    w, _, _ = analyze_moving_windows(analyzer(lines), [1000], 500, q_values=[100], centers=[(100, 100), (500, 500)])
    assert w.iloc[0].reason == 'low_coverage'
    assert np.isfinite(w.iloc[1].dq)
    assert np.isfinite(w.iloc[1].min_effective_boxes)
    assert not w.iloc[1].accepted


def test_moving_centers_and_sizes_are_separate():
    a = analyzer([LineString([(0, 500), (1000, 500)])])
    w, _, _ = analyze_moving_windows(a, [500, 1000], 250)
    assert w.center_id.nunique() == 16
    assert set(w.window_m) == {500, 1000}
    with pytest.raises(ValueError, match='Too many'):
        analyze_moving_windows(a, [500], 1, max_windows=10)
    with pytest.raises(ValueError, match='four'):
        analyze_moving_windows(a, [500], 250, divisors=[2, 4])


def test_disconnected_lines_have_no_junctions():
    lines = [LineString([(0, y), (1000, y)]) for y in (200, 400, 600)]
    w, _, _ = analyze_moving_windows(analyzer(lines), [1000], 500, centers=[(500, 500)])
    assert (w.junction_count == 0).all()


def test_equal_length_networks_differ_in_junctions():
    parallel = [LineString([(0, y), (1000, y)]) for y in (250, 750)]
    crossed = [LineString([(0, 500), (1000, 500)]), LineString([(500, 0), (500, 1000)])]
    a, _, _ = analyze_moving_windows(analyzer(parallel), [1000], 500, centers=[(500, 500)])
    b, _, _ = analyze_moving_windows(analyzer(crossed), [1000], 500, centers=[(500, 500)])
    assert np.allclose(a.density_m_per_km2, b.density_m_per_km2)
    assert (a.junction_count == 0).all()
    assert (b.junction_count == 1).all()


def test_export_separates_candidates_and_labels_window_context(tmp_path):
    a = analyzer([LineString([(0, 500), (1000, 500)]), LineString([(500, 0), (500, 1000)])])
    paths = export_moving_windows(a, tmp_path, [1000], 500, centers=[(500, 500)])
    candidates = gpd.read_file(paths['moving_gis'], layer='structural_candidates')
    controls = gpd.read_file(paths['moving_gis'], layer='topology_controls')
    assert len(candidates) == 1
    assert candidates.iloc[0].kind == 'X'
    assert candidates.iloc[0].max_branch_angle_deg == pytest.approx(90)
    assert candidates.iloc[0].context_windows_q2 == 1
    assert len(controls) == 4
    assert controls.boundary_node.all()


def test_translation_preserves_spectra_and_topology():
    from shapely.affinity import translate
    lines = [LineString([(0, 500), (1000, 500)]), LineString([(500, 0), (500, 1000)])]
    a, _, _ = analyze_moving_windows(analyzer(lines), [1000], 500, centers=[(500, 500)])
    shifted = analyzer([translate(line, 127, 231) for line in lines], box(127, 231, 1127, 1231))
    b, _, _ = analyze_moving_windows(shifted, [1000], 500, centers=[(627, 731)])
    for field in ['dq', 'alpha', 'f_alpha', 'junction_count', 'coverage']:
        assert np.allclose(a[field], b[field])


def test_extreme_q_weights_remain_finite():
    p = np.array([1e-200, .25, .75])
    for q in [-100, 100]:
        weights = MUSA._mu_for_q(p, q)
        assert np.isfinite(weights).all()
        assert weights.sum() == pytest.approx(1)


def test_interface_reads_moving_configuration():
    from tkinter import Tk, TclError
    from musa.interface import MusaInterface
    try:
        root = Tk()
    except TclError as exc:
        pytest.skip(f"Tk runtime is unavailable: {exc}")
    root.withdraw()
    try:
        app = MusaInterface(root)
        assert not app._read_run_config()['moving_enabled']
        app.moving_enabled.set(True)
        app.moving_sizes.set('1000,2000')
        app.moving_step.set('250')
        app.proximity_enabled.set(True)
        app.proximity_radii.set('100,250,500')
        config = app._read_run_config()
        assert config['moving_sizes_m'] == [1000, 2000]
        assert config['moving_step_m'] == 250
        assert config['moving_divisors'] == [16,24,32,48,64,96,128]
        assert len(config['moving_origin_offsets']) == 16
        assert config['proximity_radii_m'] == [100, 250, 500]
    finally:
        root.destroy()
