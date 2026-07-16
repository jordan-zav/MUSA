from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from musa import MUSA


Q_VALUES = [-2, -1, 0, 1, 2, 3]
RESOLUTIONS_M = [4000, 2000, 1000, 500, 250]
EXTENT_M = 16000.0


def main() -> None:
    out_dir = Path("outputs/structural_trap_experiments")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for name, payload in _scenarios(seed=20260614).items():
        scenario_dir = out_dir / name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        analyzer = MUSA(
            payload["lineaments"],
            boundary=payload["boundary"],
            q_values=Q_VALUES,
            gis_reproject_to="auto",
        )
        result = analyzer.run_analysis(
            resolutions_m=RESOLUTIONS_M,
            min_r2=0.55,
            cell_length_threshold_m=0.01,
            negative_q_floor_fraction=0.01,
        )
        analyzer.export_cell_outputs(
            output_dir=scenario_dir,
            resolutions_m=RESOLUTIONS_M,
            cell_length_threshold_m=0.01,
            aggregate_to_mother=True,
            q_values=result.q,
            reliable_min_zeta=0.15,
            reliable_min_r2=0.55,
            negative_q_floor_fraction=0.01,
            export_zeta_sensitivity=True,
            export_structural_stats=True,
            export_network_stats=True,
            export_gis_package=False,
        )
        rows.append(_summarize_scenario(name, payload, result, scenario_dir))

    summary_path = out_dir / "structural_trap_experiment_summary.csv"
    _write_rows(summary_path, rows)
    _write_readme(out_dir)
    print(summary_path)


def _scenarios(seed: int) -> dict[str, dict[str, object]]:
    import geopandas as gpd
    from shapely.geometry import box

    rng = np.random.default_rng(seed)
    boundary = gpd.GeoDataFrame(geometry=[box(0, 0, EXTENT_M, EXTENT_M)], crs="EPSG:3857")
    return {
        "regional_fault_aligned_no_mine_match": {
            "boundary": boundary,
            "lineaments": _as_gdf(_regional_fault_aligned(rng), "EPSG:3857"),
            "mine_points": np.array([[14500, 1500], [13500, 2500], [1500, 14500]], dtype=float),
            "expected": "Orientacion compatible con fallas regionales, sin coincidencia directa con minas sinteticas.",
        },
        "relay_trap_candidates": {
            "boundary": boundary,
            "lineaments": _as_gdf(_relay_trap(rng), "EPSG:3857"),
            "mine_points": np.array([[9000, 8200], [7600, 7200], [13200, 2400]], dtype=float),
            "expected": "Candidatos en zona de relevo e interseccion, no necesariamente sobre la falla principal.",
        },
        "dense_simple_fault": {
            "boundary": boundary,
            "lineaments": _as_gdf(_dense_simple_fault(rng), "EPSG:3857"),
            "mine_points": np.array([[2500, 2500], [14000, 14000]], dtype=float),
            "expected": "Alta densidad y orientacion coherente, pero complejidad estructural limitada.",
        },
        "cover_mask_sparse": {
            "boundary": boundary,
            "lineaments": _as_gdf(_cover_mask_sparse(rng), "EPSG:3857"),
            "mine_points": np.array([[8200, 8200], [11000, 3500]], dtype=float),
            "expected": "Lineamientos dispersos por cobertura superficial; reliable debe bajar.",
        },
    }


def _as_gdf(lines, crs: str):
    import geopandas as gpd

    return gpd.GeoDataFrame(geometry=lines, crs=crs)


def _regional_fault_aligned(rng: np.random.Generator):
    lines = []
    for offset in np.linspace(-5000, 13000, 12):
        center = np.array([8000 + offset * 0.15, 8000 + offset * 0.45])
        lines.append(_line(center, 4200, 45 + rng.normal(0, 3)))
    for _ in range(55):
        center = rng.uniform(1500, 14500, 2)
        angle = 45 + rng.normal(0, 8)
        lines.append(_line(center, rng.uniform(500, 1800), angle))
    return lines


def _relay_trap(rng: np.random.Generator):
    lines = []
    for x0, y0, angle in [(6000, 7600, 35), (9800, 8900, 35), (8200, 8200, 115)]:
        for _ in range(24):
            center = np.array([x0, y0]) + rng.normal(0, 1100, 2)
            lines.append(_line(center, rng.uniform(700, 2200), angle + rng.normal(0, 18)))
    for _ in range(35):
        center = rng.uniform(1000, 15000, 2)
        lines.append(_line(center, rng.uniform(400, 1200), rng.choice([35, 115]) + rng.normal(0, 10)))
    return lines


def _dense_simple_fault(rng: np.random.Generator):
    lines = []
    for y in np.linspace(3000, 13000, 15):
        center = np.array([8000, y]) + rng.normal(0, 350, 2)
        lines.append(_line(center, rng.uniform(7000, 10500), 25 + rng.normal(0, 3)))
    for _ in range(20):
        center = rng.uniform(2000, 14000, 2)
        lines.append(_line(center, rng.uniform(500, 1000), 25 + rng.normal(0, 5)))
    return lines


def _cover_mask_sparse(rng: np.random.Generator):
    lines = []
    for center0 in [np.array([3500, 12500]), np.array([12200, 3600]), np.array([9000, 9000])]:
        for _ in range(10):
            center = center0 + rng.normal(0, 900, 2)
            lines.append(_line(center, rng.uniform(350, 1200), rng.uniform(0, 180)))
    return lines


def _line(center: np.ndarray, length: float, angle_deg: float):
    from shapely.geometry import LineString

    angle = np.deg2rad(angle_deg)
    dx = 0.5 * length * np.cos(angle)
    dy = 0.5 * length * np.sin(angle)
    return LineString([(center[0] - dx, center[1] - dy), (center[0] + dx, center[1] + dy)])


def _summarize_scenario(name: str, payload: dict[str, object], result, scenario_dir: Path) -> dict[str, object]:
    mother_rows = _read_rows(scenario_dir / "multifractal_mother_agg.csv")
    structural_rows = _read_rows(scenario_dir / "lineament_mother_structural_stats.csv")
    network_rows = _read_rows(scenario_dir / "lineament_network_stats.csv")
    q2_rows = [row for row in mother_rows if float(row["q"]) == 2.0]

    alpha_w = _finite_column(q2_rows, "alpha_w")
    zeta = _finite_column(q2_rows, "zeta_mean")
    reliable = np.array([int(float(row["reliable"])) for row in q2_rows], dtype=int)
    density_by_key = {
        (int(float(row["mother_ix"])), int(float(row["mother_iy"]))): float(row["density_m_per_km2"])
        for row in structural_rows
        if row.get("density_m_per_km2", "") != ""
    }
    candidates = _candidate_rows(q2_rows)
    candidate_keys = {(int(float(row["mother_ix"])), int(float(row["mother_iy"]))) for row in candidates}
    mine_points = np.asarray(payload["mine_points"], dtype=float)
    mine_overlap = _mine_candidate_fraction(mine_points, candidate_keys)
    candidate_density = [
        density_by_key[(int(float(row["mother_ix"])), int(float(row["mother_iy"])))]
        for row in candidates
        if (int(float(row["mother_ix"])), int(float(row["mother_iy"]))) in density_by_key
    ]
    return {
        "scenario": name,
        "expected_behavior": payload["expected"],
        "accepted_q_count": result.accepted_count,
        "q2_mother_count": len(q2_rows),
        "q2_reliable_fraction": float(np.mean(reliable)) if reliable.size else "",
        "q2_alpha_w_median": _median(alpha_w),
        "q2_zeta_median": _median(zeta),
        "candidate_cell_count": len(candidates),
        "candidate_density_median": _median(np.array(candidate_density, dtype=float)),
        "mine_candidate_overlap_fraction": mine_overlap,
        "dominant_azimuth_mode": _dominant_mode(structural_rows),
        "network_intersections": _network_value(network_rows, "edge_count"),
        "largest_component_fraction": _network_value(network_rows, "largest_component_fraction"),
    }


def _candidate_rows(q_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    reliable_rows = [row for row in q_rows if int(float(row["reliable"])) == 1 and row.get("alpha_w", "") != ""]
    if not reliable_rows:
        return []
    values = np.array([float(row["alpha_w"]) for row in reliable_rows], dtype=float)
    threshold = float(np.percentile(values, 75))
    return [row for row in reliable_rows if float(row["alpha_w"]) >= threshold]


def _mine_candidate_fraction(mine_points: np.ndarray, candidate_keys: set[tuple[int, int]]) -> float:
    if mine_points.size == 0:
        return 0.0
    count = 0
    for x, y in mine_points:
        key = (int(np.floor(x / RESOLUTIONS_M[0])), int(np.floor(y / RESOLUTIONS_M[0])))
        if key in candidate_keys:
            count += 1
    return float(count / mine_points.shape[0])


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


def _dominant_mode(rows: list[dict[str, str]]) -> float | str:
    values = [float(row["dominant_azimuth_deg"]) for row in rows if row.get("dominant_azimuth_deg", "") != ""]
    if not values:
        return ""
    rounded = [round(v / 10.0) * 10.0 for v in values]
    return max(set(rounded), key=rounded.count)


def _network_value(rows: list[dict[str, str]], key: str) -> float | str:
    if not rows or key not in rows[0] or rows[0][key] == "":
        return ""
    return float(rows[0][key])


def _write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_readme(out_dir: Path) -> None:
    text = """# Experimentos de trampas estructurales

Esta carpeta contiene casos sinteticos con lineamientos reales en geometria GIS.

El objetivo no es predecir minas de forma directa. El objetivo es probar si MUSA separa dominios superficiales compatibles con trampas estructurales, zonas de relevo, intersecciones o baja confiabilidad por cobertura.

El resumen principal esta en structural_trap_experiment_summary.csv.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
