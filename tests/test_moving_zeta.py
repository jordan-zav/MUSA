import json

import numpy as np
import pytest

from musa import analyze_moving_windows, export_moving_windows
from test_moving import analyzer
from shapely.geometry import LineString


def network():
    return analyzer([LineString([(0, 500), (1000, 500)]),
                     LineString([(500, 0), (500, 1000)]),
                     LineString([(0, 50), (180, 120)])])


def test_scale_weights_match_core_and_reconstruct_weighted_slope():
    a = network()
    frame, _, _ = analyze_moving_windows(a, [1000], 500, centers=[(500,500)], q_values=[0,2])
    for row in frame.itertuples():
        details = json.loads(row.scale_diagnostics_json)
        assert len(details) == 4
        x = np.log([d['eps_m'] for d in details])
        w = np.array([d['zeta'] for d in details])
        y = np.array([d['alpha_feature'] for d in details])
        # Independent weighted least-squares reconstruction from the exported audit.
        design = np.column_stack([x, np.ones(len(x))])
        slope = np.linalg.lstsq(design*np.sqrt(w[:,None]), y*np.sqrt(w), rcond=None)[0][0]
        assert row.alpha_w == pytest.approx(slope)
        assert row.zeta_mean == pytest.approx(w.mean())
        for d in details:
            expected = a._zeta_mother_scale(1000,d['eps_m'],500,62.5,d['mass_m'],
                                            details[-1]['mass_m'],d['occupied_boxes'],d['entropy'])
            assert d['zeta'] == pytest.approx(expected)
            assert d['mass_ratio'] == pytest.approx(1)
    # Base entropy weights belong to support/scale, not to q escort probabilities.
    assert frame.zeta_mean.nunique() == 1


def test_equal_zeta_weights_recover_canonical_and_exponents_do_not_change_it():
    a = network()
    usual, _, _ = analyze_moving_windows(a,[1000],500,centers=[(500,500)])
    equal, _, _ = analyze_moving_windows(a,[1000],500,centers=[(500,500)],zeta_exponents=(0,0,0,0))
    for field in ['dq','alpha','f_alpha']:
        assert np.allclose(usual[field],equal[field])
        assert np.allclose(equal[field],equal[field+'_w'])
    assert equal.zeta_mean.eq(1).all()


def test_shifted_grid_uses_actual_nominal_box_count():
    frame, _, _ = analyze_moving_windows(network(),[1000],500,centers=[(500,500)],grid_phase=(.5,.5))
    details = json.loads(frame.iloc[0].scale_diagnostics_json)
    assert [d['possible_boxes'] for d in details] == [9,25,81,289]
    assert all(0 <= d['occupancy'] <= 1 for d in details)


def test_export_comparison_and_settings_reach_centered_windows(tmp_path):
    import geopandas as gpd
    outputs = export_moving_windows(network(),tmp_path,[1000],500,centers=[(500,500)],
                                    zeta_exponents=(0,0,0,0),zeta_scale_floor=.4,reliable_min_zeta=.8)
    frame = gpd.read_file(outputs['moving_gis'],layer='candidate_centered_spectra')
    assert frame.zeta_mean.eq(1).all()
    traps = gpd.read_file(outputs['moving_gis'],layer='trap_candidates')
    assert {'score_w','evidence_class_w','class_agreement','zeta_mean','quality_status_w'} <= set(traps.columns)
    assert traps.zeta_mean.eq(1).all()
    assert traps.class_agreement.eq('not_comparable').all()  # No matched reference.
    metadata = json.loads(open(outputs['candidate_scoring'], encoding='utf-8').read())
    assert metadata['zeta_settings']['zeta_exponents'] == [0,0,0,0]
    assert metadata['zeta_settings']['zeta_scale_floor'] == .4
    assert metadata['zeta_settings']['reliable_min_zeta'] == .8


@pytest.mark.parametrize('kwargs',[{'zeta_scale_floor':2},{'reliable_min_zeta':float('nan')},{'zeta_exponents':(-1,1,1,1)}])
def test_invalid_weights_are_rejected(kwargs):
    with pytest.raises(ValueError):
        analyze_moving_windows(network(),[1000],500,centers=[(500,500)],**kwargs)
