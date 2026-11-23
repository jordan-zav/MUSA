import importlib.util
from pathlib import Path
import zipfile
import re


ROOT = Path(__file__).resolve().parents[1]


def test_relocation_summary_keeps_test_resolution_and_absent_p_explicit():
    spec = importlib.util.spec_from_file_location('learning_null_test', ROOT / 'qgis_plugin/learning.py')
    learning = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(learning)
    assert learning.relocation_text({'status': 'not_requested'}) == ''
    assert 'no p value' in learning.relocation_text(dict(status='insufficient_information', replicates_requested=19))
    text = learning.relocation_text(dict(status='complete', replicates_requested=19, values=[0.] * 19,
                                        p_value=.7, p_holm=1., minimum_p=.1,
                                        resolution_sufficient_for_family_at_0_05=False))
    assert 'p=0.7' in text and '19/19' in text and 'minimum raw p=0.1' in text
    assert 'Too few replicates' in text


def test_packaged_learning_chapters_are_exact_sources_and_help_is_local(tmp_path):
    spec = importlib.util.spec_from_file_location("knowledge_builder", ROOT / "scripts/build_qgis_plugin.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    bundle = builder.build_plugin(ROOT, tmp_path)
    with zipfile.ZipFile(bundle) as archive:
        for name in ("KNOWLEDGE_BASE.md", "KNOWLEDGE_BASE.es.md"):
            source = (ROOT / "docs" / name).read_bytes()
            assert archive.read("musa_qgis/knowledge/" + name) == source
            html = archive.read("musa_qgis/knowledge/" + name.replace(".md", ".html")).decode("utf-8")
            language = 'es' if '.es.' in name else 'en'
            assert "<img " in html and f'src="images/knowledge_box_counting.{language}.png"' in html
            assert "1993" in html and "2007" in html and "D_BC" in html
            for image in re.findall(r'src="([^"]+)"', html):
                assert image.endswith(f'.{language}.png')
                assert archive.read('musa_qgis/knowledge/' + image) == (ROOT / 'docs' / image).read_bytes()
        assert bundle.stat().st_size <= 8_000_000
        assert "version=1.3.0" in archive.read("musa_qgis/metadata.txt").decode()


def test_spanish_results_comparison_uses_complete_spanish_sentences(tmp_path):
    import json
    spec = importlib.util.spec_from_file_location('learning_language_test', ROOT / 'qgis_plugin/learning.py')
    learning = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(learning)
    (tmp_path / 'classic_comparison.json').write_text(json.dumps(dict(comparison=dict(
        scales_m=[125, 2500], dimension=1.6, r2=.995))), encoding='utf-8')
    for status, label in [('compatible_finite_range', 'Compatible'),
                          ('not_supported', 'No respaldado'),
                          ('insufficient_information', 'Información insuficiente')]:
        (tmp_path / 'scaling_support.json').write_text(json.dumps(dict(supports=[dict(
            support_id='global', used_scales_m=[125, 2500],
            q_results=[dict(q=0, dimension=None, status=status)])])), encoding='utf-8')
        spanish = learning.comparison_text(tmp_path, 'es')
        assert label in spanish and 'Intervalo retenido' in spanish and 'escalas' in spanish
        assert not any(token in spanish for token in ['Not supported', 'Insufficient information',
                                                     'Retained interval', 'scales', 'Global MUSA',
                                                     'assessment', status])
        english = learning.comparison_text(tmp_path, 'en')
        assert 'Retained interval' in english and 'escala' not in english
