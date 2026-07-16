import math

from shapely.geometry import LineString, box

from musa.network import compute_lineament_network_stats


def test_exact_intersection_network_stats_for_crossing_lines():
    stats = compute_lineament_network_stats(
        line_geometries=[
            LineString([(0, 500), (1000, 500)]),
            LineString([(500, 0), (500, 1000)]),
            LineString([(1200, 0), (1200, 1000)]),
        ],
        boundary_geom=box(0, 0, 2000, 1000),
    )

    assert stats["node_count"] == 3
    assert stats["edge_count"] == 1
    assert stats["component_count"] == 2
    assert math.isclose(stats["largest_component_fraction"], 2 / 3, rel_tol=1e-9)
    assert math.isclose(stats["mean_degree"], 2 / 3, rel_tol=1e-9)
    assert math.isclose(stats["intersection_density_per_km2"], 0.5, rel_tol=1e-9)
    assert math.isclose(stats["connected_length_fraction"], 2 / 3, rel_tol=1e-9)
