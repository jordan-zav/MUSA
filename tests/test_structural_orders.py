import json
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, box

from musa import MUSA, analyze_moving_windows
from musa.candidates import candidate_seeds
from musa.structural_orders import attach_structural_orders


def setup(orders):
    lines = gpd.GeoDataFrame({'fault_id': ['A', 'B'], 'structural_orders': orders},
        geometry=[LineString([(0, 500), (1000, 500)]), LineString([(500, 0), (500, 1000)])], crs=26910)
    a = MUSA(lines, boundary=gpd.GeoDataFrame(geometry=[box(0, 0, 1000, 1000)], crs=26910), q_values=[0, 2])
    w, n, _ = analyze_moving_windows(a, [1000], 500, centers=[(500, 500)])
    candidates = candidate_seeds(n)
    candidates["score"] = 42.0
    return a, candidates


def test_cross_family_intersection_and_priority_do_not_modify_score():
    a, c = setup(['1', '2'])
    result = attach_structural_orders(c, a)
    assert result.iloc[0].interaction_orders == '1-2'
    assert result.iloc[0].order_priority == 1
    assert result.iloc[0].score == c.iloc[0].score
    assert len(json.loads(result.iloc[0].participant_faults_json)) == 2


def test_shared_classifications_not_arbitrarily_resolved():
    a, c = setup(['1', '2,3'])
    result = attach_structural_orders(c, a)
    assert result.iloc[0].interaction_orders == '1-2,1-3'
    assert result.iloc[0].order_status == 'ambiguous_classification'
    assert np.isnan(result.iloc[0].order_priority)


def test_unknown_order_not_inferred_from_angle():
    a, c = setup(['', '2'])
    result = attach_structural_orders(c, a)
    assert result.iloc[0].order_status == 'missing_order'
    assert np.isnan(result.iloc[0].order_priority)
