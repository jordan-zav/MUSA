import math

from shapely.geometry import LineString, box

from musa.structural import compute_lineament_mother_structural_stats


def test_orientation_axial_0_180_treats_reverse_lines_as_same_direction():
    rows = compute_lineament_mother_structural_stats(
        line_geometries=[
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (0, 0)]),
        ],
        boundary_geom=box(0, 0, 1000, 1000),
        mother_scale=1000,
        orientation_bin_degrees=10,
    )

    assert len(rows) == 1
    assert rows[0]["segment_count"] == 2
    assert math.isclose(rows[0]["dominant_azimuth_deg"], 0.0, abs_tol=1e-9)
    assert math.isclose(rows[0]["mean_azimuth_deg"], 0.0, abs_tol=1e-9)
    assert math.isclose(rows[0]["bin_000_010_m"], 200.0, abs_tol=1e-9)


def test_density_by_area_uses_mother_cell_area_km2():
    rows = compute_lineament_mother_structural_stats(
        line_geometries=[LineString([(0, 0), (1000, 0)])],
        boundary_geom=box(0, 0, 1000, 1000),
        mother_scale=1000,
        orientation_bin_degrees=10,
    )

    assert len(rows) == 1
    assert math.isclose(rows[0]["mother_area_km2"], 1.0, abs_tol=1e-9)
    assert math.isclose(rows[0]["measure_sum_m"], 1000.0, abs_tol=1e-9)
    assert math.isclose(rows[0]["density_m_per_km2"], 1000.0, abs_tol=1e-9)


def test_empty_mother_orientation_fields_are_blank():
    rows = compute_lineament_mother_structural_stats(
        line_geometries=[LineString([(100, 100), (200, 100)])],
        boundary_geom=box(0, 0, 2000, 1000),
        mother_scale=1000,
        orientation_bin_degrees=10,
    )

    empty_rows = [row for row in rows if row["segment_count"] == 0]
    assert empty_rows
    assert empty_rows[0]["dominant_azimuth_deg"] == ""
    assert empty_rows[0]["mean_azimuth_deg"] == ""
    assert empty_rows[0]["circular_variance"] == ""
