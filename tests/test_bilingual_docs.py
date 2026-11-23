"""Bilingual chapters keep translated headings in order and corresponding images."""
import json
import hashlib
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAIRS = json.loads((ROOT / 'docs/bilingual_headings.json').read_text(encoding='utf-8'))


def test_user_guide_images_have_unique_content():
    seen = {}
    for path in sorted((ROOT / 'docs/images/user-guide').glob('*.png')):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest not in seen, f'Duplicate guide images: {seen.get(digest)} and {path.name}'
        seen[digest] = path.name
    assert len(seen) >= 19


def headings(text):
    return [(len(level), title) for level, title in re.findall(r'^(#{1,6}) (.+)$', text, re.M)]


@pytest.mark.parametrize('stem', ['USER_GUIDE', 'KNOWLEDGE_BASE', 'WORKFLOW'])
def test_translated_heading_lists_have_exact_parity(stem):
    english = (ROOT / f'docs/{stem}.md').read_text(encoding='utf-8-sig')
    spanish = (ROOT / f'docs/{stem}.es.md').read_text(encoding='utf-8-sig')
    pairs = PAIRS[stem]
    # The explicit translation dictionary makes reorder/renaming/addition fail.
    assert headings(english) == [(row['level'], row['en']) for row in pairs]
    assert headings(spanish) == [(row['level'], row['es']) for row in pairs]
    translated = {row['en']: row['es'] for row in pairs}
    assert [(level, translated[title]) for level, title in headings(english)] == headings(spanish)


@pytest.mark.parametrize('stem', ['USER_GUIDE', 'KNOWLEDGE_BASE', 'WORKFLOW'])
def test_bilingual_image_lists_match_including_order(stem):
    def images(suffix):
        source = (ROOT / f'docs/{stem}{suffix}.md').read_text(encoding='utf-8-sig')
        paths = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', source)
        assert paths
        assert all((ROOT / 'docs' / path).is_file() for path in paths)
        # Workflow has separately rendered English/Spanish labels on one diagram.
        return [re.sub(r'\.(en|es)\.', '.', path) for path in paths]
    assert images('') == images('.es')
