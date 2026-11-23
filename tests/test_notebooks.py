"""Notebook execution is mandatory; missing development dependencies fail collection."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_five_notebooks_execute_with_figures_and_no_errors(tmp_path):
    spec = importlib.util.spec_from_file_location('execute_musa_tutorials', ROOT / 'scripts/execute_notebooks.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    summary = runner.execute_all(tmp_path / 'executed')
    assert len(summary['notebooks']) == 5
    assert summary['errors'] == 0 and summary['wall_seconds'] < 600
