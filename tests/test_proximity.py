import geopandas as gpd
import pytest
from shapely.geometry import LineString, box

from musa import MUSA, export_moving_windows
from musa.proximity import analyze_fault_proximity


def model(lines):
    return MUSA(gpd.GeoDataFrame(geometry=lines, crs=32618),
                boundary=gpd.GeoDataFrame(geometry=[box(0, 0, 1000, 1000)], crs=32618), q_values=[0, 2])


def test_gap_minimum_radius_and_originals_unchanged():
    a = model([LineString([(100, 500), (400, 500)]), LineString([(450, 500), (800, 500)])])
    before = [g.wkb for g in a._line_geometries]
    relations, zones = analyze_fault_proximity(a, [25, 50, 100])
    row = relations.iloc[0]
    assert len(relations) == 1
    assert row.relation_type == 'end_end'
    assert row.gap_m == pytest.approx(50)
    assert row.first_radius_m == 50
    assert row.tested_radii_count == 2
    assert row.axial_angle_deg == pytest.approx(0)
    assert len(zones) == 1
    assert [g.wkb for g in a._line_geometries] == before


def test_end_trace_angle_and_exact_cross_excluded():
    a = model([LineString([(100, 500), (400, 500)]), LineString([(450, 100), (450, 900)])])
    r, _ = analyze_fault_proximity(a, [100])
    assert r.iloc[0].relation_type == 'end_trace'
    assert r.iloc[0].axial_angle_deg == pytest.approx(90)
    a = model([LineString([(100, 500), (800, 500)]), LineString([(450, 100), (450, 900)])])
    assert analyze_fault_proximity(a, [100])[0].empty


def test_invalid_radii_and_clipped_endpoints():
    a = model([LineString([(-100, 200), (100, 200)]), LineString([(-100, 250), (100, 250)])])
    assert analyze_fault_proximity(a, [100])[0].empty
    for radii in ([], [0], [-10], [float('nan')]):
        with pytest.raises(ValueError):
            analyze_fault_proximity(a, radii)


def test_backend_exports_relations_zones_and_default_styles(tmp_path):
    import sqlite3
    a = model([LineString([(100, 500), (400, 500)]), LineString([(450, 500), (800, 500)])])
    result = export_moving_windows(a, tmp_path, [1000], 500,
                                  centers=[(500, 500)], proximity_radii_m=[25, 100])
    assert len(gpd.read_file(result['moving_gis'], layer='potential_relations')) == 1
    assert len(gpd.read_file(result['moving_gis'], layer='interaction_search_zones')) == 1
    with sqlite3.connect(result['moving_gis']) as db:
        assert db.execute('SELECT count(*) FROM layer_styles WHERE useAsDefault=1').fetchone()[0] == 10
