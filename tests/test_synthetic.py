import csv
import math
from pathlib import Path

from musa.synthetic import run_synthetic_validation


def _read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def test_run_synthetic_validation_writes_summary_for_core_scenarios(tmp_path):
    output = run_synthetic_validation(
        tmp_path,
        scenarios=["uniform_2d", "anisotropic_faults", "sparse_mothers"],
        q_values=[0, 1, 2],
        seed=7,
    )

    summary = Path(output["synthetic_validation_summary"])
    assert summary.is_file()
    rows = _read_rows(summary)
    scenarios = {row["scenario"] for row in rows}
    assert {"uniform_2d", "anisotropic_faults", "sparse_mothers"}.issubset(scenarios)

    uniform_q2 = next(row for row in rows if row["scenario"] == "uniform_2d" and row["q"] == "2")
    assert abs(float(uniform_q2["alpha"]) - 2.0) <= 0.15
    assert uniform_q2["pass_fail"] == "pass"

    anisotropic = [row for row in rows if row["scenario"] == "anisotropic_faults"]
    assert anisotropic
    assert all(row["pass_fail"] == "pass" for row in anisotropic)

    sparse = next(row for row in rows if row["scenario"] == "sparse_mothers" and row["q"] == "2")
    assert math.isfinite(float(sparse["reliable_fraction"]))
