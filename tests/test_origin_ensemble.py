import itertools
import json
import math
import numpy as np
import pytest
from shapely.geometry import LineString
from shapely.affinity import translate

from musa import MUSA,analyze_moving_windows
from musa.mass_partition import primitive_arrays,primitive_masses
from musa.partition import line_cell_segments
from musa.moving import ENSEMBLE_OFFSETS,ENSEMBLE_DIVISORS
from test_moving import analyzer


def test_accelerated_and_python_partition_match_independent_reference():
    rng=np.random.default_rng(123)
    lines=[LineString(rng.uniform(0,1000,(10,2))) for _ in range(3)]
    for offset in ((0,0),(500000,6000000)):
        shifted=[translate(g,*offset) for g in lines]
        starts,ends=primitive_arrays(shifted)
        reference={}
        for key,length,_ in line_cell_segments(shifted,137,offset):
            reference[key]=reference.get(key,0.)+length
        for function in (primitive_masses,getattr(primitive_masses,'py_func',primitive_masses)):
            result=dict(function(starts,ends,137.,*map(float,offset)))
            assert result==pytest.approx(reference,abs=1e-7)
            assert sum(result.values())==pytest.approx(sum(g.length for g in lines))


def test_grid_corner_does_not_generate_roundoff_sliver():
    line=LineString([(0,150),(1000,850)])
    for offset in ((0,0),(500000,6000000)):
        masses=MUSA._line_length_cells([translate(line,*offset)],1000/128,np.array(offset))
        assert min(masses.values()) > 1e-6
        assert sum(masses.values())==pytest.approx(line.length)


def ensemble(lines,phase=(0,0)):
    w,_,_=analyze_moving_windows(analyzer(lines),[1000],500,centers=[(500,500)],
        q_values=[0,1,2],divisors=ENSEMBLE_DIVISORS,origin_offsets=ENSEMBLE_OFFSETS,grid_phase=phase)
    return w.set_index('q')


def test_uniform_line_dimension_improves_without_clamping_spectrum():
    line=LineString([(0,500),(1000,500)])
    a,b=ensemble([line]),ensemble([line],(.125,.125))
    for w in (a,b):
        assert np.all(np.abs(w.dq-1)<.03)
        assert abs(w.loc[0,'alpha']-w.loc[2,'alpha'])<.05
        assert w.loc[0,'alpha'] < w.loc[2,'alpha']  # Residual edge bias is retained.
        for row in w.itertuples():
            assert np.mean(json.loads(row.origin_alpha_json))==pytest.approx(row.alpha)
            assert np.mean(json.loads(row.origin_alpha_w_json))==pytest.approx(row.alpha_w)
            for d in json.loads(row.scale_diagnostics_json):
                assert len(d['origin_details'])==16
                assert all(v['mass_m']==pytest.approx(1000) for v in d['origin_details'])
    assert abs(a.loc[0,'alpha']-a.loc[2,'alpha']-b.loc[0,'alpha']+b.loc[2,'alpha'])<.02


def test_known_binomial_cantor_spectrum_is_not_flattened():
    p=.7; levels=7; lines=[]
    for bits in itertools.product((0,1),repeat=levels):
        start=1000*sum(2*b*3.**(-k-1) for k,b in enumerate(bits))
        length=1000*3.**(-levels)*np.prod([p if b==0 else 1-p for b in bits])/p**levels
        center=start+500*3.**(-levels)
        lines.append(LineString([(center-length/2,500),(center+length/2,500)]))
    for phase in ((0,0),(.125,.125)):
        w=ensemble(lines,phase)
        for q in (0,2):
            weights=np.array([p,1-p])**q; weights/=weights.sum()
            expected_alpha=-float(weights@np.log([p,1-p]))/math.log(3)
            expected_d=math.log(p**q+(1-p)**q)/((1-q)*math.log(3))
            assert w.loc[q,'alpha']==pytest.approx(expected_alpha,abs=.05)
            assert w.loc[q,'dq']==pytest.approx(expected_d,abs=.025)
        assert w.loc[0,'alpha']-w.loc[2,'alpha']>.2


@pytest.mark.parametrize('offsets',[[],[(0,0),(0,0)],[(1,0)],[(float('nan'),0)]])
def test_invalid_origin_banks_rejected(offsets):
    with pytest.raises(ValueError,match='[Oo]rigin'):
        analyze_moving_windows(analyzer([LineString([(0,500),(1000,500)])]),
            [1000],500,centers=[(500,500)],origin_offsets=offsets)


def test_background_bank_sensitivity_prevents_supported_class():
    import pandas as pd
    from test_candidates import evidence_fixture
    from musa.candidates import classify_candidate_evidence
    seeds,bg,primary,shifted,sizes=evidence_fixture()
    alternate_bg=bg.copy()
    alternate_bg.loc[alternate_bg.q==2,'alpha']-=.3
    result,details,_=classify_candidate_evidence(seeds,bg,primary,shifted,sizes,
                                               shifted_background=alternate_bg)
    assert result.iloc[0].relative_class==3
    assert pd.isna(result.iloc[0].evidence_class)
    assert all(d['phase_status']=='sensitive' for d in details)
    assert all(d['alternate_size_class']==1 for d in details)
    assert all(d['background_phase_difference']==pytest.approx(.3) for d in details)


def test_negative_width_is_distinguished_from_missing_coverage():
    from test_candidates import evidence_fixture
    from musa.candidates import classify_candidate_evidence
    seeds,bg,primary,shifted,sizes=evidence_fixture(widths=(-.02,-.02,-.02))
    _,details,_=classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    assert all(d['reason']=='negative_spectral_width' for d in details)
    primary['reason']='low_coverage'; primary['accepted']=False
    shifted['reason']='low_coverage'; shifted['accepted']=False
    _,details,_=classify_candidate_evidence(seeds,bg,primary,shifted,sizes)
    assert all(d['reason']=='low_coverage' for d in details)


def test_export_ensemble_includes_alternate_background_and_styles(tmp_path):
    import geopandas as gpd
    import sqlite3
    from musa import export_moving_windows
    a=analyzer([LineString([(0,500),(1000,500)]),LineString([(500,0),(500,1000)])])
    output=export_moving_windows(a,tmp_path,[1000],500,centers=[(500,500)],q_values=[0,2],
        divisors=ENSEMBLE_DIVISORS,origin_offsets=ENSEMBLE_OFFSETS)
    bg=gpd.read_file(output['moving_gis'],layer='window_shifted_spectra')
    assert bg.origin_count.eq(16).all()
    with sqlite3.connect(output['moving_gis']) as db:
        assert db.execute("SELECT count(*) FROM layer_styles WHERE f_table_name='window_shifted_spectra'").fetchone()[0]==1
        metadata=json.loads(db.execute('SELECT configuration_json FROM candidate_scoring').fetchone()[0])
    assert metadata['version']=='relative_multifractal_ensemble_v7'
    assert metadata['grid_phases']==[[0,0],[.125,.125]]


def test_parallel_windows_match_sequential_ids_and_estimates():
    import pandas as pd
    a=analyzer([LineString([(0,500),(1000,500)])])
    options=dict(window_sizes_m=[200],step_m=200,centers=[(100,500),(300,500),(700,500),(900,500)],
                 q_values=[0,2],origin_offsets=ENSEMBLE_OFFSETS,divisors=ENSEMBLE_DIVISORS)
    sequential,_,_=analyze_moving_windows(a,**options)
    parallel,_,cfg=analyze_moving_windows(a,workers=2,**options)
    pd.testing.assert_frame_equal(sequential,parallel)
    assert cfg['centers']==[[100,500],[300,500],[700,500],[900,500]]
    assert cfg['workers']==2
