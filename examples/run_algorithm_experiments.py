from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from musa import MUSA


Q_VALUES = [-2, -1, 0, 1, 2, 3]
SCALES = [0.25, 0.125, 0.0625, 0.03125]


def main() -> None:
    out_dir = Path("outputs/algorithm_experiments")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, points in _scenarios(seed=20260614).items():
        scenario_dir = out_dir / name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        analyzer = MUSA(points, q_values=Q_VALUES, normalize=False)
        result = analyzer.run_analysis(
            min_scale=min(SCALES),
            max_scale=max(SCALES),
            num_scales=len(SCALES),
            min_r2=0.55,
            negative_q_floor_fraction=0.01,
        )
        analyzer.export_cell_outputs(
            output_dir=scenario_dir,
            resolutions_m=SCALES,
            aggregate_to_mother=True,
            q_values=result.q,
            reliable_min_zeta=0.15,
            reliable_min_r2=0.55,
            negative_q_floor_fraction=0.01,
            export_zeta_sensitivity=True,
            export_structural_stats=False,
            export_network_stats=False,
            export_gis_package=False,
        )
        rows.extend(_summarize(name, result, scenario_dir))

    summary_path = out_dir / "algorithm_experiment_summary.csv"
    _write_rows(summary_path, rows)
    _write_readme(out_dir)
    print(summary_path)


def _scenarios(seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        "uniform_2d": rng.random((2500, 2)),
        "clustered_corridor": _clustered_corridor(rng),
        "anisotropic_parallel": _anisotropic_parallel(rng),
        "powerlaw_clusters": _powerlaw_clusters(rng),
        "sparse_mothers": _sparse_mothers(rng),
        "crossing_network": _crossing_network(rng),
    }


def _clustered_corridor(rng: np.random.Generator) -> np.ndarray:
    x = rng.uniform(0.05, 0.95, 2200)
    y = 0.52 + 0.12 * np.sin(8 * x) + rng.normal(0, 0.035, x.size)
    background = rng.random((350, 2))
    pts = np.column_stack([x, y])
    return _clip01(np.vstack([pts, background]))


def _anisotropic_parallel(rng: np.random.Generator) -> np.ndarray:
    rows = []
    for y0 in np.linspace(0.18, 0.82, 7):
        x = rng.uniform(0.05, 0.95, 320)
        y = y0 + rng.normal(0, 0.012, x.size)
        rows.append(np.column_stack([x, y]))
    return _clip01(np.vstack(rows))


def _powerlaw_clusters(rng: np.random.Generator) -> np.ndarray:
    centers = rng.uniform(0.12, 0.88, (12, 2))
    ranks = np.arange(1, centers.shape[0] + 1)
    counts = np.maximum(30, (900 / ranks**1.15).astype(int))
    rows = []
    for center, count in zip(centers, counts):
        spread = 0.01 + 0.04 * rng.random()
        rows.append(center + rng.normal(0, spread, (int(count), 2)))
    return _clip01(np.vstack(rows))


def _sparse_mothers(rng: np.random.Generator) -> np.ndarray:
    centers = np.array([[0.18, 0.2], [0.75, 0.25], [0.25, 0.78], [0.82, 0.82]])
    rows = [center + rng.normal(0, 0.025, (120, 2)) for center in centers]
    return _clip01(np.vstack(rows))


def _crossing_network(rng: np.random.Generator) -> np.ndarray:
    t = rng.uniform(0.05, 0.95, 1400)
    diag_a = np.column_stack([t, t + rng.normal(0, 0.018, t.size)])
    diag_b = np.column_stack([t, 1.0 - t + rng.normal(0, 0.018, t.size)])
    background = rng.random((250, 2))
    return _clip01(np.vstack([diag_a, diag_b, background]))


def _clip01(points: np.ndarray) -> np.ndarray:
    return np.clip(points, 0.0, 1.0)


def _summarize(name: str, result, scenario_dir: Path) -> list[dict[str, object]]:
    rows = []
    mother_path = scenario_dir / "multifractal_mother_agg.csv"
    mother_rows = _read_rows(mother_path)
    for q, dq, alpha, f_alpha in zip(result.q, result.dq, result.alpha, result.f_alpha):
        local_rows = [row for row in mother_rows if float(row["q"]) == float(q)]
        alpha_w = _finite_column(local_rows, "alpha_w")
        zeta = _finite_column(local_rows, "zeta_mean")
        reliable = [int(float(row["reliable"])) for row in local_rows if row.get("reliable") not in ("", None)]
        rows.append(
            {
                "scenario": name,
                "q": float(q),
                "accepted_q_count": int(result.accepted_count),
                "rejected_q_count": int(result.rejected_count),
                "dq": float(dq),
                "alpha": float(alpha),
                "f_alpha": float(f_alpha),
                "mother_count": len(local_rows),
                "alpha_w_median": _median(alpha_w),
                "alpha_w_iqr": _iqr(alpha_w),
                "zeta_mean_median": _median(zeta),
                "reliable_fraction": float(np.mean(reliable)) if reliable else "",
            }
        )
    return rows


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def _finite_column(rows: list[dict[str, str]], column: str) -> np.ndarray:
    values = []
    for row in rows:
        raw = row.get(column, "")
        if raw == "":
            continue
        value = float(raw)
        if np.isfinite(value):
            values.append(value)
    return np.array(values, dtype=float)


def _median(values: np.ndarray) -> float | str:
    return float(np.median(values)) if values.size else ""


def _iqr(values: np.ndarray) -> float | str:
    return float(np.percentile(values, 75) - np.percentile(values, 25)) if values.size else ""


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(out_dir: Path) -> None:
    text = """# Experimentos algoritmicos MUSA

Esta carpeta contiene una corrida reproducible sobre casos sinteticos de puntos.

Casos incluidos:

- uniform_2d
- clustered_corridor
- anisotropic_parallel
- powerlaw_clusters
- sparse_mothers
- crossing_network

El resumen principal esta en algorithm_experiment_summary.csv.

Estos experimentos ejecutan el algoritmo real de MUSA sobre geometria sintetica de puntos. No sustituyen la corrida GIS de Broken Hill ni la validacion geologica con lineamientos reales.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
