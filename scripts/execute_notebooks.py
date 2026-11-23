"""Execute every tutorial serially with this interpreter and a private kernel."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]


def execute_all(output, *, names=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    kernel_root = output / 'kernels'
    spec = kernel_root / 'musa-tutorial'
    spec.mkdir(parents=True, exist_ok=True)
    (spec / 'kernel.json').write_text(json.dumps(dict(
        argv=[sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
        display_name='MUSA tutorial interpreter', language='python')), encoding='utf-8')
    sources = sorted((ROOT / 'notebooks').glob('[0-9][0-9]_*.ipynb'))
    if names is not None:
        sources = [p for p in sources if p.name in names]
    assert len(sources) == (len(names) if names else 5)
    records, start = [], time.perf_counter()
    for source in sources:
        notebook = nbformat.read(source, as_version=4)
        manager = KernelManager(kernel_name='musa-tutorial', kernel_spec_manager=KernelSpecManager(
            kernel_dirs=[str(kernel_root)]))
        client = NotebookClient(notebook, km=manager, timeout=120, allow_errors=False,
                                resources={'metadata': {'path': str(ROOT)}})
        before = time.perf_counter()
        environment = dict(os.environ, MUSA_NOTEBOOK_OUTPUT_ROOT=str(output / 'products'))
        try:
            client.execute(env=environment)
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=False)
        duration = time.perf_counter() - before
        assert not any(item.output_type == 'error' for cell in notebook.cells
                       if cell.cell_type == 'code' for item in cell.get('outputs', []))
        assert any('image/png' in item.get('data', {}) for cell in notebook.cells
                   if cell.cell_type == 'code' for item in cell.get('outputs', []))
        notebook.metadata['musa_execution'] = dict(wall_seconds=duration, errors=0)
        nbformat.write(notebook, output / source.name)
        records.append(dict(notebook=source.name, wall_seconds=duration))
        print(source.name, f'{duration:.3f} s', flush=True)
    elapsed = time.perf_counter() - start
    assert elapsed < 600, f'Tutorials exceeded ten minutes: {elapsed}'
    summary = dict(notebooks=records, wall_seconds=elapsed, errors=0)
    (output / 'execution.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    execute_all(args.output)
