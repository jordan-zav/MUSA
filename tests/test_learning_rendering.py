"""Chapter captions, proportional scaling and bilingual figure contracts."""
import importlib.util
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('learning_render_test', ROOT/'qgis_plugin/learning.py')
learning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learning)


def test_viewport_controls_width_with_a_760_pixel_ceiling():
    sizes = [learning.image_display_size(w, 1200, 720) for w in (220, 1000, 1400)]
    assert sizes[1][0] == 760
    assert sizes[2][0] == 760
    assert sizes[0][0] < sizes[1][0] == sizes[2][0]
    assert all(abs(h/w-.6) < 1e-12 for w,h in sizes)
    assert learning.image_display_size(20, 1200, 720)[0] > 0
    assert learning.image_display_size(1000, 0, 720) is None


def test_verified_doi_urls_keep_parenthesized_years_inside_the_link():
    for doi in ('10.1016/0191-8141(93)90010-8', '10.1016/S0309-1708(02)00042-8'):
        html = learning.learning_html(f'[Reference](https://doi.org/{doi}).')
        assert f'href="https://doi.org/{doi}">Reference</a>.' in html


def test_formula_blocks_keep_only_safe_indices_and_exponents():
    html = learning.learning_html('::math N(ε) = C ε<sup>−D</sup>\n\n'
                                  '::math p<sub>i</sub> = m<sub>i</sub> / Σ m<sub>j</sub>')
    assert html.count('class="formula" align="center"') == 2
    assert 'ε<sup>−D</sup>' in html and 'p<sub>i</sub>' in html
    assert '::math' not in html
    assert '&lt;script&gt;' in learning.learning_html('::math <script>alert(1)</script>')
    assert '&lt;sup onclick=' in learning.learning_html('::math <sup onclick="x">2</sup>')


def test_bilingual_editorial_contract_and_formula_coverage():
    for suffix, heading in [('', 'Sources'), ('.es', 'Fuentes')]:
        source = (ROOT/f'docs/KNOWLEDGE_BASE{suffix}.md').read_text(encoding='utf-8')
        assert len(re.findall(r'^## \d+\.', source, re.M)) == 8
        assert len(re.findall(r'^::math ', source, re.M)) == 11
        assert 'En pocas palabras:' not in source and 'In short:' not in source
        sources = source.split(f'## {heading}\n\n')[1]
        entries = re.findall(r'^- (.*https://doi.org/.*)$', sources, re.M)
        assert len(entries) == len(set(entries)) == 33
        # Alphabetical by first author; same-author entries keep APA order.
        assert entries == sorted(entries, key=lambda entry: entry.split(',')[0].casefold())
        assert not re.search('[ᴰᵢⱼⁿ⁻]', source)
        # Scientific examples stay frozen; only map sampling/display changes.
        assert '0.992364' in source or '0,992364' in source
        assert '12 periodic' not in source and '12 intervalos' not in source


def test_every_figure_has_a_prior_reference_and_a_numbered_centered_caption():
    for lang, suffix, prefix in [('en', '', 'Figure'), ('es', '.es', 'Figura')]:
        source = (ROOT/f'docs/KNOWLEDGE_BASE{suffix}.md').read_text(encoding='utf-8')
        matches = list(re.finditer(r'!\[[^]]*\]\(([^)]+)\)', source))
        assert len(matches) == 13
        for number, match in enumerate(matches, 1):
            assert f'{prefix} {number} ' in source[:match.start()]
            assert source[match.end():].lstrip().startswith(f'{prefix} {number}. ')
            assert match[1].endswith(f'.{lang}.png')
            with Image.open(ROOT/'docs'/match[1]) as im:
                assert im.width == 1200
                assert im.mode == "RGB"
        html = learning.learning_html(source)
        assert html.count('class="figure-caption" align="center"><small>') == 13
        assert 'width="600"' not in html
        assert 'h1,h2,h3{margin-top:' in html
        assert '.figure{line-height:100%;' in html


def test_shared_network_counts_conserve_length_and_binary_example_has_equal_counts():
    data = json.loads((ROOT/'docs/images/knowledge_narrative_measurements.json').read_text())
    assert data['network']['trace_count'] == 627
    np.testing.assert_allclose(sum(data['rose']['length_m']), data['network']['total_length_m'], rtol=1e-12)
    assert data['binary'] == dict(side_m=100, lengths_m=[10., 1000.], occupied_counts=[1, 1])
    for row in data['grids']:
        assert row['count'] == len(row['cells'])
        np.testing.assert_allclose(sum(c['length_m'] for c in row['cells']), data['network']['total_length_m'], rtol=1e-12)
    # Density and distance share sample centres, domain mask and physical units.
    assert len(data['maps']['density_per_m']) == len(data['maps']['nearest_m']) == 10000
    assert [x is None for x in data['maps']['density_per_m']] == [x is None for x in data['maps']['nearest_m']]
    approved = json.loads((ROOT/'docs/images/knowledge_measurements.json').read_text())
    for name in ('rods', 'cantor'):
        assert data[name]['classic'] == approved[name]['classic']
    np.testing.assert_allclose(data['raster']['total_geometric_length'], approved['raster']['total_geometric_length'])
