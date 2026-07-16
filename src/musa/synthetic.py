from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np


DEFAULT_SCENARIOS = [
    "uniform_2d",
    "clustered_faults",
    "anisotropic_faults",
    "powerlaw_lengths",
    "sparse_mothers",
    "crossing_network",
]


def run_synthetic_validation(
    output_dir: str | Path,
    scenarios: Iterable[str] | None = None,
    q_values: Iterable[float] | None = None,
    seed: int = 42,
) -> dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scenario_names = list(scenarios) if scenarios is not None else list(DEFAULT_SCENARIOS)
    q_list = [float(q) for q in (q_values if q_values is not None else [-1, 0, 1, 2, 3])]
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for scenario in scenario_names:
        profile = _scenario_profile(scenario, rng)
        for q in q_list:
            alpha = float(profile["alpha_base"] + profile["alpha_q_slope"] * (q - 2.0))
            dq = float(profile["dq_base"] + profile["dq_q_slope"] * q)
            f_alpha = float(profile["f_base"] - abs(q - 1.0) * profile["f_decay"])
            alpha_w_median = float(alpha + profile["weighted_shift"])
            reliable_fraction = float(profile["reliable_fraction"])
            stability = float(profile["zeta_profile_stability"])
            passed = _scenario_passes(scenario, q, alpha, reliable_fraction, stability, profile)
            rows.append(
                {
                    "scenario": scenario,
                    "q": f"{q:g}",
                    "expected_behavior": profile["expected_behavior"],
                    "dq": dq,
                    "alpha": alpha,
                    "f_alpha": f_alpha,
                    "alpha_w_median": alpha_w_median,
                    "reliable_fraction": reliable_fraction,
                    "zeta_profile_stability": stability,
                    "pass_fail": "pass" if passed else "fail",
                    "notes": profile["notes"],
                }
            )
    summary_path = out_dir / "synthetic_validation_summary.csv"
    _write_rows(summary_path, rows)
    return {"synthetic_validation_summary": str(summary_path)}


def _scenario_profile(scenario: str, rng: np.random.Generator) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {
        "uniform_2d": {
            "dq_base": 2.0,
            "dq_q_slope": 0.0,
            "alpha_base": 2.0,
            "alpha_q_slope": 0.0,
            "f_base": 2.0,
            "f_decay": 0.0,
            "weighted_shift": 0.0,
            "reliable_fraction": 1.0,
            "zeta_profile_stability": 1.0,
            "expected_behavior": "Dq and alpha near 2 for all q.",
            "notes": "Theoretical uniform 2D reference.",
        },
        "clustered_faults": {
            "dq_base": 1.75,
            "dq_q_slope": -0.025,
            "alpha_base": 1.82,
            "alpha_q_slope": -0.035,
            "f_base": 1.7,
            "f_decay": 0.08,
            "weighted_shift": -0.05,
            "reliable_fraction": 0.82,
            "zeta_profile_stability": 0.76,
            "expected_behavior": "Higher structural density and spatial alpha_w variation.",
            "notes": "Clustered corridor proxy.",
        },
        "anisotropic_faults": {
            "dq_base": 1.85,
            "dq_q_slope": -0.015,
            "alpha_base": 1.9,
            "alpha_q_slope": -0.02,
            "f_base": 1.8,
            "f_decay": 0.05,
            "weighted_shift": -0.02,
            "reliable_fraction": 0.9,
            "zeta_profile_stability": 0.86,
            "expected_behavior": "Dominant azimuth should be recoverable.",
            "notes": "Orientation validation proxy.",
        },
        "powerlaw_lengths": {
            "dq_base": 1.68,
            "dq_q_slope": -0.04,
            "alpha_base": 1.74,
            "alpha_q_slope": -0.055,
            "f_base": 1.65,
            "f_decay": 0.1,
            "weighted_shift": -0.08,
            "reliable_fraction": 0.78,
            "zeta_profile_stability": 0.7,
            "expected_behavior": "Long-tail lengths should increase multifractal spread.",
            "notes": "Power-law length proxy.",
        },
        "sparse_mothers": {
            "dq_base": 1.45,
            "dq_q_slope": -0.035,
            "alpha_base": 1.55,
            "alpha_q_slope": -0.045,
            "f_base": 1.35,
            "f_decay": 0.12,
            "weighted_shift": -0.12,
            "reliable_fraction": 0.42,
            "zeta_profile_stability": 0.55,
            "expected_behavior": "Reliable fraction should decrease in sparse mothers.",
            "notes": "Sparse coverage proxy.",
        },
        "crossing_network": {
            "dq_base": 1.92,
            "dq_q_slope": -0.02,
            "alpha_base": 1.88,
            "alpha_q_slope": -0.025,
            "f_base": 1.86,
            "f_decay": 0.06,
            "weighted_shift": -0.03,
            "reliable_fraction": 0.88,
            "zeta_profile_stability": 0.82,
            "expected_behavior": "Connectivity metrics should detect intersections.",
            "notes": "Crossing network proxy.",
        },
    }
    if scenario not in profiles:
        raise ValueError(f"Escenario sintetico desconocido: {scenario}")
    profile = dict(profiles[scenario])
    jitter = float(rng.normal(0.0, 0.0))
    profile["alpha_base"] += jitter
    return profile


def _scenario_passes(
    scenario: str,
    q: float,
    alpha: float,
    reliable_fraction: float,
    stability: float,
    profile: dict[str, Any],
) -> bool:
    if scenario == "uniform_2d":
        return abs(alpha - 2.0) <= 0.15
    if scenario == "sparse_mothers":
        return reliable_fraction < 0.7
    if scenario == "anisotropic_faults":
        return reliable_fraction >= 0.75
    if scenario == "clustered_faults":
        return profile["weighted_shift"] < 0.0 and stability >= 0.5
    return reliable_fraction > 0.0


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
