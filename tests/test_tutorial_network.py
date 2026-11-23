"""Teaching network must yield readable contrasts, supported curves and abstentions."""
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import box

from musa import MUSA, classic_box_counting
from musa.scaling import ScalingOptions, assess_lineament_scaling
from musa.spectrum_products import _assessment_series, spectrum_shape_reasons

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from tutorial_network import fracture_network  # noqa: E402


def test_fracture_teaching_network_has_usable_spectra_and_readable_counterexamples():
    lines, domain, families = fracture_network()
    assert len(lines) == 627 and set(families) == {1, 2, 3}
    assert len(domain.exterior.coords) == 8 and domain.area < domain.envelope.area
    # GEOS clipping may round an endpoint a few ulps outside a sloping edge.
    assert all(domain.buffer(1e-8).covers(line) for line in lines)
    qs = np.arange(0, 4.1, .5)
    scales = np.geomspace(125, 2500, 16)
    options = ScalingOptions(1, renyi_order_policy='inform_q0_q2')
    model = MUSA.from_line_geometries(lines, domain, 'EPSG:32718', q_values=qs)
    full = assess_lineament_scaling(model, scales, options)
    global_spectrum = next(_assessment_series([full]))
    assert spectrum_shape_reasons(global_spectrum) == [
        'Alpha increases between q=0.5 and q=1: alpha(0.5) = 1.571 < alpha(1) = 1.577.'
    ]
    # q=0 alpha is unsupported, so it stays outside the existing joint gate.
    assert global_spectrum['points'][0]['statuses']['alpha'] == 'not_supported'
    classic = classic_box_counting(model, scales)
    assert full['q_results'][0]['status'] == 'compatible_finite_range'
    assert abs(classic['dimension']-full['q_results'][0]['dimension']) > .02
    # Actual selected window 18 is centred at (7000,7000), side 6000.
    window = domain.intersection(box(4000, 4000, 10000, 10000))
    local = MUSA.from_line_geometries(lines, window, 'EPSG:32718', q_values=qs)
    report = assess_lineament_scaling(local, scales, options, nominal_area=6000**2)
    spectrum = next(_assessment_series([report]))
    assert report['coverage'] >= .8
    assert not spectrum_shape_reasons(spectrum)
    assert sum(point['accepted'] for point in spectrum['points']) >= 4
    # Window 11: good mapped area, curved D1, inadequate effective q4 support.
    window = domain.intersection(box(2000, 0, 8000, 6000))
    curved = assess_lineament_scaling(MUSA.from_line_geometries(lines, window, 'EPSG:32718', q_values=qs),
                                     scales, options, nominal_area=6000**2)
    d1 = next(row for row in curved['q_results'] if row['q'] == 1)
    assert curved['coverage'] > .97
    assert d1['status'] == 'not_supported' and 'quadratic_predicts_better' in d1['reasons']
    assert curved['q_results'][-1]['status'] == 'insufficient_information'
