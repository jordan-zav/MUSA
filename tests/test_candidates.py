import json

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString, box

from musa import MUSA, analyze_moving_windows, export_moving_windows
from musa.candidates import candidate_seeds, classify_candidate_evidence
from musa.moving import fracture_nodes


def model():
    return MUSA(gpd.GeoDataFrame(geometry=[LineString([(0, 500), (1000, 500)]),
        LineString([(500, 0), (500, 1000)])], crs=32618),
        boundary=gpd.GeoDataFrame(geometry=[box(0, 0, 1000, 1000)], crs=32618), q_values=[0, 2])


def test_intersection_angles_exclude_opposite_duplicate_axes():
    nodes = fracture_nodes(model()._line_geometries, box(0, 0, 1000, 1000))
    cross = next(n for n in nodes if n['degree'] == 4)
    pairs = json.loads(cross['intersection_angles_json'])
    assert len(pairs) == 1
    assert pairs[0]['angle_deg'] == pytest.approx(90)
    assert cross['intersection_angle_min_deg'] == 90


def test_multiple_fault_axes_keep_pairwise_angles():
    lines = [LineString([(-10, 0), (10, 0)]), LineString([(0, -10), (0, 10)]),
             LineString([(-10, -10), (10, 10)])]
    node = next(n for n in fracture_nodes(lines, box(-20, -20, 20, 20)) if n['degree'] == 6)
    assert sorted(p['angle_deg'] for p in json.loads(node['intersection_angles_json'])) == [45, 45, 90]


def test_exact_cross_no_longer_gets_70_automatic_points(tmp_path):
    outputs = export_moving_windows(model(), tmp_path, [1000], 500, centers=[(500, 500)])
    saved = gpd.read_file(outputs['moving_gis'], layer='trap_candidates')
    assert len(saved) == 1
    assert pd.isna(saved.iloc[0].evidence_class)
    assert np.isnan(saved.iloc[0].score)
    assert saved.iloc[0].angle_kind == 'intersection'
    centered = gpd.read_file(outputs['moving_gis'], layer='candidate_centered_spectra')
    assert centered.center_x.eq(500).all()
    assert centered.center_y.eq(500).all()


def evidence_fixture(widths=(.3, .3, .3), ref_count=24, shifted_widths=None):
    a = model()
    w, n, _ = analyze_moving_windows(a, [1000], 500, centers=[(500, 500)])
    seeds = candidate_seeds(n)
    sizes = [1000, 2000, 4000]
    def rows(center_id, x, size, width):
        return [dict(center_id=center_id, window_m=size, center_x=x, center_y=500,
                     density_m_per_km2=1000., coverage=1., accepted=True, q=q,
                     alpha=1.5 if q==0 else 1.5-width,
                     geometry=box(x-size/2, 500-size/2, x+size/2, 500+size/2)) for q in [0,2]]
    background, centered, shifted = [], [], []
    for i,size in enumerate(sizes):
        centered.extend(rows(0, 500, size, widths[i]))
        shifted.extend(rows(0, 500, size, (shifted_widths or widths)[i]))
        for j in range(ref_count):
            background.extend(rows(j+1, 10000+j*5000, size, .02+j*.002))
    return seeds, *(gpd.GeoDataFrame(r, geometry='geometry', crs=32618) for r in [background, centered, shifted]), sizes


@pytest.mark.parametrize('widths,expected', [((.03,.03,.03),1),((.05,.05,.05),2),((.3,.3,.3),3),((.3,.03,.03),1)])
def test_three_classes_follow_evidence_not_forced_counts(widths, expected):
    result, detail, meta = classify_candidate_evidence(*evidence_fixture(widths))
    assert result.iloc[0].evidence_class == expected
    explanation=json.loads(result.iloc[0].explanation)
    assert result.iloc[0].score == pytest.approx(100*np.median(explanation['percentiles']))
    assert len(detail)==3
    assert 'p-values' not in meta['score']


def test_insufficient_background_stays_unscored():
    result, details, _ = classify_candidate_evidence(*evidence_fixture(ref_count=5))
    assert pd.isna(result.iloc[0].evidence_class)
    assert np.isnan(result.iloc[0].score)
    assert all(d['reason']=='insufficient_reference' for d in details)


def test_grid_instability_is_separate_from_relative_class():
    result, details, _ = classify_candidate_evidence(*evidence_fixture(shifted_widths=(.1,.1,.1)))
    assert result.iloc[0].relative_class == 3
    assert pd.isna(result.iloc[0].evidence_class)
    assert result.iloc[0].class_status == "grid_sensitive"
    assert result.iloc[0].quality_status == 'grid_sensitive'
    assert result.iloc[0].computational_quality == 0
    assert all(d['phase_status']=='sensitive' for d in details)


def test_background_density_must_match():
    seeds,bg,primary,shifted,sizes=evidence_fixture()
    bg['density_m_per_km2']=10000
    result, _, _=classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    assert pd.isna(result.iloc[0].evidence_class)
    assert np.isnan(result.iloc[0].score)


def test_rank_ties_do_not_become_positive_anomaly():
    seeds,bg,primary,shifted,sizes=evidence_fixture(widths=(.1,.1,.1))
    bg.loc[bg.q==2,'alpha']=1.4
    result,details,_=classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    assert result.iloc[0].score == pytest.approx(50)
    assert result.iloc[0].evidence_class == 1
    assert all(d['empirical_percentile']==.5 for d in details)


def test_uniform_synthetic_network_does_not_become_good_node():
    lines = [LineString([(x, 0), (x, 12000)]) for x in range(0,12001,500)]
    lines += [LineString([(0, y), (12000, y)]) for y in range(0,12001,500)]
    a = MUSA(gpd.GeoDataFrame(geometry=lines, crs=32618),
             boundary=gpd.GeoDataFrame(geometry=[box(0,0,12000,12000)], crs=32618), q_values=[0,2])
    bg, n, _ = analyze_moving_windows(a, [2000], 2000)
    center = n.loc[n.geometry.x.eq(5000) & n.geometry.y.eq(5000)]
    seeds = candidate_seeds(center)
    primary, _, _ = analyze_moving_windows(a, [2000], 2000, centers=[(5000,5000)])
    shifted, _, _ = analyze_moving_windows(a, [2000], 2000, centers=[(5000,5000)], grid_phase=(.5,.5))
    result, _, _ = classify_candidate_evidence(seeds,bg,primary,shifted,[2000])
    assert pd.isna(result.iloc[0].evidence_class) or result.iloc[0].evidence_class == 1


def test_missing_sizes_are_support_not_low_pattern_class():
    seeds,bg,primary,shifted,sizes=evidence_fixture()
    primary.loc[primary.window_m!=1000,'accepted']=False
    result, _, _=classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    row=result.iloc[0]
    assert row.relative_class == 3
    assert pd.isna(row.evidence_class)
    assert row.class_status == "insufficient_support"
    assert row.score == 100
    assert row.evaluated_sizes == 1
    assert row.support_fraction == pytest.approx(1/3)
    assert row.quality_status == 'partial_support'


def test_same_patterns_can_all_receive_same_class():
    seeds,bg,primary,shifted,sizes=evidence_fixture()
    copies=gpd.GeoDataFrame(pd.concat([seeds]*3,ignore_index=True),crs=seeds.crs)
    copies['candidate_id']=['a','b','c']
    primary=gpd.GeoDataFrame(pd.concat([primary.assign(center_id=i) for i in range(3)],ignore_index=True),crs=primary.crs)
    shifted=gpd.GeoDataFrame(pd.concat([shifted.assign(center_id=i) for i in range(3)],ignore_index=True),crs=shifted.crs)
    result, _, _=classify_candidate_evidence(copies,bg,primary,shifted,sizes)
    assert result.evidence_class.eq(3).all()
    assert result.score.eq(100).all()
