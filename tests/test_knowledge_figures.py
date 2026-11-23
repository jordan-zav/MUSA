"""Check the numerical contracts behind the teaching figures and local reader."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from knowledge_examples import finite_cantor, random_rods, raster_comparison  # noqa: E402


def test_raster_figure_preserves_exact_length_and_measures_a_different_raster_mass():
    result = raster_comparison()
    committed = json.loads((ROOT / 'docs/images/knowledge_measurements.json').read_text())['raster']
    np.testing.assert_allclose(result['rows'][0]['total_lengths'], result['total_geometric_length'], rtol=1e-12)
    for actual, saved in zip(result['rows'], committed['rows']):
        np.testing.assert_allclose(actual['dimensions'], saved['dimensions'], atol=1e-12)
    assert len(result['rows']) == 7
    assert result['rows'][-1]['dimensions'][0] - result['rows'][0]['dimensions'][0] > .2


def test_worked_cantor_state_and_plain_language_summaries():
    result = finite_cantor()
    assert result['classic']['r2'] > .99
    assert len(result['assessment']['used_scales_m']) == 4
    assert all(row['status'] == 'insufficient_information' for row in result['assessment']['q_results'])
    for suffix in ('', '.es'):
        text = (ROOT / f'docs/KNOWLEDGE_BASE{suffix}.md').read_text(encoding='utf-8')
        # Sections open with connected prose, not a formulaic summary label.
        assert 'In short:' not in text and 'En pocas palabras:' not in text
        spec = importlib.util.spec_from_file_location('learning_figure_test', ROOT / 'qgis_plugin/learning.py')
        learning = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(learning)
        html = learning.learning_html(text)
        language = 'es' if suffix else 'en'
        for image in (f'knowledge_{name}.{language}.png' for name in ('box_counting', 'raster', 'cantor', 'rods')):
            assert f'src="images/{image}"' in html


def test_many_scale_classic_fit_conceals_predictive_curvature():
    actual = random_rods()
    saved = json.loads((ROOT / 'docs/images/knowledge_measurements.json').read_text())['rods']
    assert actual['classic']['r2'] > .99
    np.testing.assert_allclose(actual['classic']['dimension'], saved['classic']['dimension'], atol=1e-12)
    row = actual['assessment']['q_results'][0]
    assert len(actual['assessment']['used_scales_m']) == 24
    assert row['status'] == 'not_supported'
    assert {'quadratic_predicts_better', 'segmented_predicts_better'} <= set(row['reasons'])
    assert row['margins']['scale_count'] >= 0
    assert row['margins']['span_decades'] > 0
    for model in ('quadratic', 'segmented'):
        assert row['margins']['curvature'][model]['gain_effect'] > .03
        assert row['margins']['curvature'][model]['cv_ratio'] < .75
