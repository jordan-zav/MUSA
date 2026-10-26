from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy import stats
from scipy.special import logsumexp


@dataclass
class MUSAResult:
    q: np.ndarray
    scales: np.ndarray
    dq: np.ndarray
    tau: np.ndarray
    alpha: np.ndarray
    f_alpha: np.ndarray
    r2: np.ndarray
    p_values: np.ndarray
    alpha_r2: np.ndarray
    f_alpha_r2: np.ndarray
    min_r2: float
    rejected_q: np.ndarray
    rejected_r2: np.ndarray
    rejected_alpha_r2: np.ndarray
    rejected_f_alpha_r2: np.ndarray
    dq_ci_low: np.ndarray | None = None
    dq_ci_high: np.ndarray | None = None
    alpha_ci_low: np.ndarray | None = None
    alpha_ci_high: np.ndarray | None = None
    f_alpha_ci_low: np.ndarray | None = None
    f_alpha_ci_high: np.ndarray | None = None
    bootstrap_iterations: int = 0
    bootstrap_ci: float = 0.95
    dq_ts: np.ndarray | None = None
    alpha_ts: np.ndarray | None = None
    f_alpha_ts: np.ndarray | None = None
    dq_jackknife_std: np.ndarray | None = None
    alpha_jackknife_std: np.ndarray | None = None
    f_alpha_jackknife_std: np.ndarray | None = None
    scale_diagnostics: list[dict[str, Any]] | None = None

    @property
    def accepted_count(self) -> int:
        return int(self.q.size)

    @property
    def rejected_count(self) -> int:
        return int(self.rejected_q.size)


class MUSA:
    """
    Multifractal Spectrum Analyzer.

    Supports:
    - Plain spatial coordinates (numpy/pandas-like arrays)
    - GIS inputs via GeoDataFrame or vector file path (optional dependencies)
    """

    def __init__(
        self,
        data: Any,
        boundary: Any | None = None,
        q_values: Iterable[float] | None = None,
        normalize: bool = True,
        gis_reproject_to: str = "auto",
    ) -> None:
        self.q_values = (
            np.linspace(-10.0, 10.0, 41) if q_values is None else np.array(q_values, dtype=float)
        )
        prepared = self._prepare_input(
            data=data,
            boundary=boundary,
            normalize=normalize,
            gis_reproject_to=gis_reproject_to,
        )
        self._kind = prepared["kind"]
        self.points = prepared.get("points")
        self._origin = prepared.get("origin")
        self._line_geometries = prepared.get("line_geometries")
        self._boundary_geom = prepared.get("boundary_geom")
        self._active_crs = prepared.get("crs")
        self._source_gdf = prepared.get("source_gdf")

    def run_analysis(
        self,
        min_scale: float = 0.01,
        max_scale: float = 0.5,
        num_scales: int = 20,
        resolutions_m: Iterable[float] | None = None,
        cell_length_threshold_m: float = 0.0,
        min_r2: float = 0.9,
        bootstrap_iterations: int = 0,
        bootstrap_ci: float = 0.95,
        bootstrap_seed: int | None = None,
        negative_q_floor_fraction: float = 0.0,
    ) -> MUSAResult:
        if cell_length_threshold_m < 0:
            raise ValueError("cell_length_threshold_m debe ser >= 0.")
        if not np.isfinite(min_r2) or min_r2 < 0.0 or min_r2 >= 1.0:
            raise ValueError("min_r2 debe ser finito, >= 0 y < 1.")
        if bootstrap_iterations < 0:
            raise ValueError("bootstrap_iterations debe ser >= 0.")
        if not np.isfinite(bootstrap_ci) or bootstrap_ci <= 0.0 or bootstrap_ci >= 1.0:
            raise ValueError("bootstrap_ci debe ser finito, > 0 y < 1.")
        if not np.isfinite(negative_q_floor_fraction) or negative_q_floor_fraction < 0.0:
            raise ValueError("negative_q_floor_fraction debe ser finito y >= 0.")
        if resolutions_m is not None:
            scales = self._validate_resolutions(resolutions_m)
        else:
            if self._kind == "lines":
                raise ValueError(
                    "Para lineamientos GIS debes pasar resoluciones_m en metros, "
                    "por ejemplo: [2000, 1000, 500, 250]."
                )
            scales = np.logspace(np.log10(min_scale), np.log10(max_scale), num_scales)
            scales = np.array(scales, dtype=float)

        features_by_q = np.zeros((len(self.q_values), len(scales)), dtype=float)
        alpha_features_by_q = np.zeros((len(self.q_values), len(scales)), dtype=float)
        f_features_by_q = np.zeros((len(self.q_values), len(scales)), dtype=float)

        for i, eps in enumerate(scales):
            probs = self._probabilities_for_scale(
                eps,
                cell_length_threshold_m=cell_length_threshold_m,
            )
            if probs.size == 0:
                raise ValueError("No se pudo calcular probabilidades por caja; revisa los datos.")

            for j, q in enumerate(self.q_values):
                probs_q = self._stabilize_probs_for_q(
                    probs,
                    q,
                    floor_fraction=negative_q_floor_fraction,
                )
                if np.isclose(q, 1.0):
                    # Information dimension uses Shannon entropy scaling.
                    features_by_q[j, i] = -np.sum(probs_q * np.log(probs_q + 1e-15))
                elif np.isclose(q, 0.0):
                    # Capacity dimension scales with log(N_boxes).
                    features_by_q[j, i] = np.log(np.count_nonzero(probs_q > 0))
                else:
                    log_z = logsumexp(q * np.log(probs_q))
                    # sum(p_i ** q) scales as epsilon ** tau(q). Because the
                    # regression x-axis is log(1 / epsilon), the sign is
                    # inverted to recover positive generalized dimensions.
                    features_by_q[j, i] = -log_z / (q - 1.0)

                mu = self._mu_for_q(probs_q, q)
                alpha_features_by_q[j, i] = np.sum(mu * np.log(probs_q + 1e-300))
                f_features_by_q[j, i] = np.sum(mu * np.log(mu + 1e-300))

        x = np.log(1.0 / scales)
        x_eps = np.log(scales)
        x_fit = x
        feats_fit = features_by_q

        dq = np.zeros(len(self.q_values), dtype=float)
        r2 = np.zeros(len(self.q_values), dtype=float)
        p_values = np.zeros(len(self.q_values), dtype=float)
        alpha = np.zeros(len(self.q_values), dtype=float)
        f_alpha = np.zeros(len(self.q_values), dtype=float)
        alpha_r2 = np.zeros(len(self.q_values), dtype=float)
        f_alpha_r2 = np.zeros(len(self.q_values), dtype=float)

        for j in range(len(self.q_values)):
            slope, _intercept, r_value, p_value, _std_err = stats.linregress(x_fit, feats_fit[j])
            dq[j] = slope
            r2[j] = r_value**2
            p_values[j] = p_value
            alpha_slope, _alpha_intercept, alpha_r_value, _alpha_p_value, _alpha_std_err = stats.linregress(
                x_eps, alpha_features_by_q[j]
            )
            f_slope, _f_intercept, f_r_value, _f_p_value, _f_std_err = stats.linregress(
                x_eps, f_features_by_q[j]
            )
            alpha[j] = alpha_slope
            f_alpha[j] = f_slope
            alpha_r2[j] = alpha_r_value**2
            f_alpha_r2[j] = f_r_value**2

        accepted = (r2 > min_r2) & (alpha_r2 > min_r2) & (f_alpha_r2 > min_r2)
        rejected_q = self.q_values[~accepted].copy()
        rejected_r2 = r2[~accepted].copy()
        rejected_alpha_r2 = alpha_r2[~accepted].copy()
        rejected_f_alpha_r2 = f_alpha_r2[~accepted].copy()
        if np.count_nonzero(accepted) < 2:
            threshold_label = str(float(min_r2))
            failed_pairs = ", ".join(
                f"q={float(q):g}: Dq_R2={float(dq_score):.6f}, "
                f"alpha_R2={float(alpha_score):.6f}, f_alpha_R2={float(f_score):.6f}"
                for q, dq_score, alpha_score, f_score in zip(
                    rejected_q, rejected_r2, rejected_alpha_r2, rejected_f_alpha_r2
                )
            )
            raise ValueError(
                f"Precision insuficiente: solo se aceptan ajustes Dq, alpha y f(alpha) con R2 > {threshold_label}. "
                f"Eliminados: {len(rejected_q)}. Valores rechazados: {failed_pairs}"
            )

        accepted_q = self.q_values[accepted].copy()
        accepted_dq = dq[accepted]
        accepted_r2 = r2[accepted]
        accepted_p_values = p_values[accepted]
        accepted_alpha = alpha[accepted]
        accepted_f_alpha = f_alpha[accepted]
        accepted_alpha_r2 = alpha_r2[accepted]
        accepted_f_alpha_r2 = f_alpha_r2[accepted]
        bootstrap = self._bootstrap_global_confidence_intervals(
            x_dq=x_fit,
            dq_features=feats_fit,
            x_chhabra=x_eps,
            alpha_features=alpha_features_by_q,
            f_features=f_features_by_q,
            accepted_mask=accepted,
            iterations=int(bootstrap_iterations),
            ci=float(bootstrap_ci),
            seed=bootstrap_seed,
        )
        dq_ts = np.full(len(self.q_values), np.nan, dtype=float)
        alpha_ts = np.full(len(self.q_values), np.nan, dtype=float)
        f_alpha_ts = np.full(len(self.q_values), np.nan, dtype=float)
        global_scale_diagnostics: list[dict[str, Any]] = []
        for j, q in enumerate(self.q_values):
            dq_ts[j], _dq_ts_r2 = self._theil_sen_metrics(x_fit.tolist(), feats_fit[j].tolist())
            alpha_ts[j], _alpha_ts_r2 = self._theil_sen_metrics(
                x_eps.tolist(), alpha_features_by_q[j].tolist()
            )
            f_alpha_ts[j], _f_ts_r2 = self._theil_sen_metrics(
                x_eps.tolist(), f_features_by_q[j].tolist()
            )
            global_scale_diagnostics.extend(
                self._scale_diagnostics_rows(
                    q=float(q),
                    scales=scales,
                    x_dq=x_fit.tolist(),
                    y_dq=feats_fit[j].tolist(),
                    x_alpha=x_eps.tolist(),
                    y_alpha=alpha_features_by_q[j].tolist(),
                    y_f=f_features_by_q[j].tolist(),
                )
            )
            for row in global_scale_diagnostics[-len(scales):]:
                row["accepted_q"] = bool(accepted[j])
        dq_jackknife_std = self._jackknife_std_by_q(global_scale_diagnostics, "q", "dq_loo")
        alpha_jackknife_std = self._jackknife_std_by_q(global_scale_diagnostics, "q", "alpha_loo")
        f_alpha_jackknife_std = self._jackknife_std_by_q(global_scale_diagnostics, "q", "f_alpha_loo")

        tau = (accepted_q - 1.0) * accepted_dq
        accepted_indices = np.where(accepted)[0]

        return MUSAResult(
            q=accepted_q,
            scales=scales,
            dq=accepted_dq,
            tau=tau,
            alpha=accepted_alpha,
            f_alpha=accepted_f_alpha,
            r2=accepted_r2,
            p_values=accepted_p_values,
            alpha_r2=accepted_alpha_r2,
            f_alpha_r2=accepted_f_alpha_r2,
            min_r2=float(min_r2),
            rejected_q=rejected_q,
            rejected_r2=rejected_r2,
            rejected_alpha_r2=rejected_alpha_r2,
            rejected_f_alpha_r2=rejected_f_alpha_r2,
            dq_ci_low=bootstrap.get("dq_ci_low"),
            dq_ci_high=bootstrap.get("dq_ci_high"),
            alpha_ci_low=bootstrap.get("alpha_ci_low"),
            alpha_ci_high=bootstrap.get("alpha_ci_high"),
            f_alpha_ci_low=bootstrap.get("f_alpha_ci_low"),
            f_alpha_ci_high=bootstrap.get("f_alpha_ci_high"),
            bootstrap_iterations=int(bootstrap_iterations),
            bootstrap_ci=float(bootstrap_ci),
            dq_ts=dq_ts[accepted_indices],
            alpha_ts=alpha_ts[accepted_indices],
            f_alpha_ts=f_alpha_ts[accepted_indices],
            dq_jackknife_std=dq_jackknife_std[accepted_indices],
            alpha_jackknife_std=alpha_jackknife_std[accepted_indices],
            f_alpha_jackknife_std=f_alpha_jackknife_std[accepted_indices],
            scale_diagnostics=[
                row for row in global_scale_diagnostics if bool(row.get("accepted_q", False))
            ],
        )

    def export_cell_outputs(
        self,
        output_dir: str | Path,
        resolutions_m: Iterable[float],
        cell_length_threshold_m: float = 0.0,
        aggregate_to_mother: bool = True,
        q_values: Iterable[float] | None = None,
        reliable_min_zeta: float = 0.15,
        reliable_min_r2: float = 0.9,
        local_bootstrap_iterations: int = 0,
        local_bootstrap_ci: float = 0.95,
        local_bootstrap_seed: int | None = None,
        negative_q_floor_fraction: float = 0.0,
        zeta_exponents: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0),
        zeta_scale_floor: float = 0.25,
        export_zeta_sensitivity: bool = False,
        export_structural_stats: bool = True,
        orientation_bin_degrees: int = 10,
        export_network_stats: bool = False,
        export_gis_package: bool = True,
    ) -> dict[str, str]:
        """
        Export cell-level spatial outputs for monofractal and multifractal workflows.

        Local probabilities and Chhabra-Jensen integrands are computed within each
        mother cell (not over the full study extent). Mother-level alpha and f(alpha)
        come from linear regression across child scales, matching the global method.

        A reliability weight zeta (ζ) combines coverage, relative mass and scale
        position for a weighted regression (alpha_w, f_alpha_w) alongside the
        canonical unweighted estimates.

        Files generated:
        - monofractal_cells.csv
        - multifractal_cells.csv
        - monofractal_mother_agg.csv (optional)
        - multifractal_mother_agg.csv (optional)
        - musa_mother_cells.gpkg (GIS inputs only, optional)
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        scales = self._validate_resolutions(resolutions_m)
        mother_scale = float(np.max(scales))
        finest_scale = float(np.min(scales))
        regression_scales = scales[scales < mother_scale - 1e-9 * max(mother_scale, 1.0)]
        export_q_values = self.q_values if q_values is None else np.array(list(q_values), dtype=float)
        if cell_length_threshold_m < 0:
            raise ValueError("cell_length_threshold_m debe ser >= 0.")
        if not np.isfinite(reliable_min_zeta) or reliable_min_zeta < 0:
            raise ValueError("reliable_min_zeta debe ser finito y >= 0.")
        if not np.isfinite(reliable_min_r2) or reliable_min_r2 < 0.0 or reliable_min_r2 > 1.0:
            raise ValueError("reliable_min_r2 debe ser finito, >= 0 y <= 1.")
        if local_bootstrap_iterations < 0:
            raise ValueError("local_bootstrap_iterations debe ser >= 0.")
        if not np.isfinite(local_bootstrap_ci) or local_bootstrap_ci <= 0.0 or local_bootstrap_ci >= 1.0:
            raise ValueError("local_bootstrap_ci debe ser finito, > 0 y < 1.")
        if not np.isfinite(negative_q_floor_fraction) or negative_q_floor_fraction < 0.0:
            raise ValueError("negative_q_floor_fraction debe ser finito y >= 0.")
        zeta_exponents = self._normalize_zeta_exponents(zeta_exponents)
        if not np.isfinite(zeta_scale_floor) or zeta_scale_floor < 0.0 or zeta_scale_floor > 1.0:
            raise ValueError("zeta_scale_floor debe ser finito, >= 0 y <= 1.")
        if export_q_values.size == 0:
            raise ValueError("Debes exportar al menos un valor de q.")

        mono_rows: list[dict[str, float | int]] = []
        multi_rows: list[dict[str, float | int]] = []
        mono_mother_integrands: dict[tuple[int, int], dict[str, list[float]]] = defaultdict(
            lambda: {"ln_inv_eps": [], "ln_n": [], "entropy": []}
        )
        multi_mother_integrands: dict[tuple[int, int], dict[float, dict[str, list[float]]]] = defaultdict(
            lambda: defaultdict(lambda: {"ln_eps": [], "alpha_f": [], "f_f": [], "zeta": []})
        )
        mother_meta: dict[tuple[int, int], dict[str, float | int]] = {}
        mother_regression_stats: dict[tuple[int, int], list[dict[str, float | int]]] = defaultdict(list)
        mother_scale_diagnostics_rows: list[dict[str, Any]] = []
        zeta_sensitivity_rows: list[dict[str, Any]] = []
        zeta_profiles = self._zeta_profiles(
            base_exponents=zeta_exponents,
            enabled=export_zeta_sensitivity,
        )

        for eps in scales:
            cell_measures = self._cell_measure_for_scale(
                eps=eps,
                cell_length_threshold_m=cell_length_threshold_m,
            )
            if not cell_measures:
                continue

            keys = list(cell_measures.keys())
            measures = np.array([cell_measures[k] for k in keys], dtype=float)
            centroids = [self._cell_centroid(k[0], k[1], eps) for k in keys]
            mother_keys = [self._mother_key_from_centroid(cx, cy, mother_scale) for cx, cy in centroids]
            groups: dict[tuple[int, int], list[int]] = defaultdict(list)
            for idx, mother_key in enumerate(mother_keys):
                groups[(int(mother_key[0]), int(mother_key[1]))].append(idx)

            use_for_regression = bool(np.any(np.isclose(regression_scales, eps)))
            local_denom = np.log(mother_scale / eps) if eps < mother_scale - 1e-9 * max(mother_scale, 1.0) else np.nan

            for mother_key, indices in groups.items():
                mkx, mky = mother_key
                m_measures = measures[indices]
                m_total = float(np.sum(m_measures))
                if m_total <= 0:
                    continue

                m_probs = m_measures / m_total
                if use_for_regression:
                    n_boxes = int(np.count_nonzero(m_measures > 0))
                    entropy = float(-np.sum(m_probs * np.log(m_probs + 1e-300)))
                    ln_inv_eps = float(np.log(1.0 / eps))
                    ln_eps = float(np.log(eps))
                    mono_mother_integrands[mother_key]["ln_inv_eps"].append(ln_inv_eps)
                    mono_mother_integrands[mother_key]["ln_n"].append(float(np.log(n_boxes)))
                    mono_mother_integrands[mother_key]["entropy"].append(entropy)
                    mother_regression_stats[mother_key].append(
                        {
                            "eps": float(eps),
                            "m_total": m_total,
                            "n_occupied": len(indices),
                            "entropy": entropy,
                            "ln_inv_eps": ln_inv_eps,
                            "ln_eps": ln_eps,
                        }
                    )

                if aggregate_to_mother and np.isclose(eps, finest_scale):
                    if mother_key not in mother_meta:
                        mcx, mcy = self._cell_centroid(mkx, mky, mother_scale)
                        mother_meta[mother_key] = {
                            "mother_scale_m": mother_scale,
                            "mother_ix": int(mkx),
                            "mother_iy": int(mky),
                            "mother_centroid_x": float(mcx),
                            "mother_centroid_y": float(mcy),
                            "measure_sum_m": 0.0,
                            "cells_count": 0,
                        }
                    mother_meta[mother_key]["measure_sum_m"] = float(
                        mother_meta[mother_key]["measure_sum_m"]
                    ) + m_total
                    mother_meta[mother_key]["cells_count"] = int(
                        mother_meta[mother_key]["cells_count"]
                    ) + len(indices)

                if np.isfinite(local_denom):
                    d_local = -np.log(m_probs + 1e-300) / local_denom
                else:
                    d_local = np.full_like(m_probs, np.nan, dtype=float)

                for local_idx, global_idx in enumerate(indices):
                    key = keys[global_idx]
                    cx, cy = centroids[global_idx]
                    mono_rows.append(
                        {
                            "scale_m": float(eps),
                            "cell_ix": int(key[0]),
                            "cell_iy": int(key[1]),
                            "centroid_x": float(cx),
                            "centroid_y": float(cy),
                            "measure_m": float(m_measures[local_idx]),
                            "p_i": float(m_probs[local_idx]),
                            "d_local_index": float(d_local[local_idx]),
                            "mother_ix": int(mkx),
                            "mother_iy": int(mky),
                        }
                    )

                for q in export_q_values:
                    probs_q = self._stabilize_probs_for_q(
                        m_probs,
                        q,
                        floor_fraction=negative_q_floor_fraction,
                    )
                    mu = self._mu_for_q(probs_q, q)
                    alpha_integrand = mu * np.log(probs_q + 1e-300)
                    f_integrand = mu * np.log(mu + 1e-300)
                    if use_for_regression:
                        q_key = float(q)
                        multi_mother_integrands[mother_key][q_key]["ln_eps"].append(float(np.log(eps)))
                        multi_mother_integrands[mother_key][q_key]["alpha_f"].append(float(np.sum(alpha_integrand)))
                        multi_mother_integrands[mother_key][q_key]["f_f"].append(float(np.sum(f_integrand)))

                    for local_idx, global_idx in enumerate(indices):
                        key = keys[global_idx]
                        cx, cy = centroids[global_idx]
                        multi_rows.append(
                            {
                                "scale_m": float(eps),
                                "q": float(q),
                                "cell_ix": int(key[0]),
                                "cell_iy": int(key[1]),
                                "centroid_x": float(cx),
                                "centroid_y": float(cy),
                                "measure_m": float(m_measures[local_idx]),
                                "p_i": float(probs_q[local_idx]),
                                "mu_i_q": float(mu[local_idx]),
                                "alpha_integrand_contrib": float(alpha_integrand[local_idx]),
                                "f_integrand_contrib": float(f_integrand[local_idx]),
                                "zeta": "",
                                "mother_ix": int(mkx),
                                "mother_iy": int(mky),
                            }
                        )

        zeta_by_mother_eps = self._zeta_lookup_by_mother(
            mother_scale=mother_scale,
            regression_scales=regression_scales,
            mother_meta=mother_meta,
            mother_regression_stats=mother_regression_stats,
            exponents=zeta_exponents,
            scale_floor=zeta_scale_floor,
        )
        zeta_by_profile: dict[str, dict[tuple[int, int, float], float]] = {}
        for profile_name, profile_exponents in zeta_profiles.items():
            zeta_by_profile[profile_name] = self._zeta_lookup_by_mother(
                mother_scale=mother_scale,
                regression_scales=regression_scales,
                mother_meta=mother_meta,
                mother_regression_stats=mother_regression_stats,
                exponents=profile_exponents,
                scale_floor=zeta_scale_floor,
            )
        for row in mono_rows:
            zeta = zeta_by_mother_eps.get(
                (int(row["mother_ix"]), int(row["mother_iy"]), float(row["scale_m"])),
                float("nan"),
            )
            row["zeta"] = float(zeta) if np.isfinite(zeta) else ""
        for row in multi_rows:
            zeta = zeta_by_mother_eps.get(
                (int(row["mother_ix"]), int(row["mother_iy"]), float(row["scale_m"])),
                float("nan"),
            )
            row["zeta"] = float(zeta) if np.isfinite(zeta) else ""

        for mother_key, q_map in multi_mother_integrands.items():
            zeta_list = self._zeta_list_for_mother(
                mother_key=mother_key,
                regression_scales=regression_scales,
                zeta_by_mother_eps=zeta_by_mother_eps,
            )
            for integrands in q_map.values():
                integrands["zeta"] = list(zeta_list)

        written: dict[str, str] = {}
        mono_path = out_dir / "monofractal_cells.csv"
        self._write_rows_csv(mono_path, mono_rows)
        written["monofractal_cells"] = str(mono_path)

        multi_path = out_dir / "multifractal_cells.csv"
        self._write_rows_csv(multi_path, multi_rows)
        written["multifractal_cells"] = str(multi_path)

        if aggregate_to_mother:
            mono_mother_rows: list[dict[str, float | int]] = []
            for mother_key, integrands in mono_mother_integrands.items():
                meta = mother_meta.get(mother_key)
                if meta is None:
                    continue
                d0_local, d0_r2 = self._linear_regression_metrics(
                    integrands["ln_inv_eps"], integrands["ln_n"]
                )
                d1_local, d1_r2 = self._linear_regression_metrics(
                    integrands["ln_inv_eps"], integrands["entropy"]
                )
                zeta_list = self._zeta_list_for_mother(
                    mother_key=mother_key,
                    regression_scales=regression_scales,
                    zeta_by_mother_eps=zeta_by_mother_eps,
                )
                d0_w, d0_w_r2 = self._linear_regression_metrics(
                    integrands["ln_inv_eps"], integrands["ln_n"], weights=zeta_list
                )
                d1_w, d1_w_r2 = self._linear_regression_metrics(
                    integrands["ln_inv_eps"], integrands["entropy"], weights=zeta_list
                )
                d0_ts, d0_ts_r2 = self._theil_sen_metrics(
                    integrands["ln_inv_eps"], integrands["ln_n"]
                )
                d1_ts, d1_ts_r2 = self._theil_sen_metrics(
                    integrands["ln_inv_eps"], integrands["entropy"]
                )
                d0_ci_low, d0_ci_high = self._bootstrap_regression_ci(
                    integrands["ln_inv_eps"],
                    integrands["ln_n"],
                    iterations=local_bootstrap_iterations,
                    ci=local_bootstrap_ci,
                    seed=self._seed_with_key(local_bootstrap_seed, mother_key, "d0"),
                )
                d1_ci_low, d1_ci_high = self._bootstrap_regression_ci(
                    integrands["ln_inv_eps"],
                    integrands["entropy"],
                    iterations=local_bootstrap_iterations,
                    ci=local_bootstrap_ci,
                    seed=self._seed_with_key(local_bootstrap_seed, mother_key, "d1"),
                )
                d0_w_ci_low, d0_w_ci_high = self._bootstrap_regression_ci(
                    integrands["ln_inv_eps"],
                    integrands["ln_n"],
                    weights=zeta_list,
                    iterations=local_bootstrap_iterations,
                    ci=local_bootstrap_ci,
                    seed=self._seed_with_key(local_bootstrap_seed, mother_key, "d0w"),
                )
                d1_w_ci_low, d1_w_ci_high = self._bootstrap_regression_ci(
                    integrands["ln_inv_eps"],
                    integrands["entropy"],
                    weights=zeta_list,
                    iterations=local_bootstrap_iterations,
                    ci=local_bootstrap_ci,
                    seed=self._seed_with_key(local_bootstrap_seed, mother_key, "d1w"),
                )
                d0_jackknife_std = self._jackknife_std(
                    integrands["ln_inv_eps"], integrands["ln_n"]
                )
                d1_jackknife_std = self._jackknife_std(
                    integrands["ln_inv_eps"], integrands["entropy"]
                )
                zeta_mean, zeta_min = self._zeta_summary(zeta_list)
                d0_reliable = self._is_reliable(
                    zeta_mean=zeta_mean,
                    r2_values=[d0_w_r2],
                    min_zeta=reliable_min_zeta,
                    min_r2=reliable_min_r2,
                )
                d1_reliable = self._is_reliable(
                    zeta_mean=zeta_mean,
                    r2_values=[d1_w_r2],
                    min_zeta=reliable_min_zeta,
                    min_r2=reliable_min_r2,
                )
                mono_mother_rows.append(
                    {
                        **meta,
                        "scales_count": len(integrands["ln_inv_eps"]),
                        "d0_local": float(d0_local),
                        "d0_r2": float(d0_r2),
                        "d1_local": float(d1_local),
                        "d1_r2": float(d1_r2),
                        "d0_ts": float(d0_ts),
                        "d0_ts_r2": float(d0_ts_r2),
                        "d1_ts": float(d1_ts),
                        "d1_ts_r2": float(d1_ts_r2),
                        "d0_w": float(d0_w),
                        "d0_w_r2": float(d0_w_r2),
                        "d1_w": float(d1_w),
                        "d1_w_r2": float(d1_w_r2),
                        "d0_ci_low": self._scalar_or_blank(d0_ci_low),
                        "d0_ci_high": self._scalar_or_blank(d0_ci_high),
                        "d1_ci_low": self._scalar_or_blank(d1_ci_low),
                        "d1_ci_high": self._scalar_or_blank(d1_ci_high),
                        "d0_w_ci_low": self._scalar_or_blank(d0_w_ci_low),
                        "d0_w_ci_high": self._scalar_or_blank(d0_w_ci_high),
                        "d1_w_ci_low": self._scalar_or_blank(d1_w_ci_low),
                        "d1_w_ci_high": self._scalar_or_blank(d1_w_ci_high),
                        "d0_jackknife_std": self._scalar_or_blank(d0_jackknife_std),
                        "d1_jackknife_std": self._scalar_or_blank(d1_jackknife_std),
                        "zeta_mean": float(zeta_mean),
                        "zeta_min": float(zeta_min),
                        "d0_reliable": int(d0_reliable),
                        "d1_reliable": int(d1_reliable),
                        "local_bootstrap_iterations": int(local_bootstrap_iterations),
                        "local_bootstrap_ci": float(local_bootstrap_ci),
                    }
                )

            multi_mother_rows: list[dict[str, float | int]] = []
            for mother_key, q_map in multi_mother_integrands.items():
                meta = mother_meta.get(mother_key)
                if meta is None:
                    continue
                for q, integrands in q_map.items():
                    alpha, f_alpha, alpha_r2, f_alpha_r2 = self._chhabra_regression_metrics(
                        integrands["ln_eps"], integrands["alpha_f"], integrands["f_f"]
                    )
                    alpha_w, f_alpha_w, alpha_w_r2, f_alpha_w_r2 = self._chhabra_regression_metrics(
                        integrands["ln_eps"],
                        integrands["alpha_f"],
                        integrands["f_f"],
                        weights=integrands["zeta"],
                    )
                    alpha_ts, alpha_ts_r2 = self._theil_sen_metrics(
                        integrands["ln_eps"], integrands["alpha_f"]
                    )
                    f_alpha_ts, f_alpha_ts_r2 = self._theil_sen_metrics(
                        integrands["ln_eps"], integrands["f_f"]
                    )
                    alpha_ci_low, alpha_ci_high = self._bootstrap_regression_ci(
                        integrands["ln_eps"],
                        integrands["alpha_f"],
                        iterations=local_bootstrap_iterations,
                        ci=local_bootstrap_ci,
                        seed=self._seed_with_key(local_bootstrap_seed, mother_key, q, "alpha"),
                    )
                    f_ci_low, f_ci_high = self._bootstrap_regression_ci(
                        integrands["ln_eps"],
                        integrands["f_f"],
                        iterations=local_bootstrap_iterations,
                        ci=local_bootstrap_ci,
                        seed=self._seed_with_key(local_bootstrap_seed, mother_key, q, "falpha"),
                    )
                    alpha_w_ci_low, alpha_w_ci_high = self._bootstrap_regression_ci(
                        integrands["ln_eps"],
                        integrands["alpha_f"],
                        weights=integrands["zeta"],
                        iterations=local_bootstrap_iterations,
                        ci=local_bootstrap_ci,
                        seed=self._seed_with_key(local_bootstrap_seed, mother_key, q, "alphaw"),
                    )
                    f_w_ci_low, f_w_ci_high = self._bootstrap_regression_ci(
                        integrands["ln_eps"],
                        integrands["f_f"],
                        weights=integrands["zeta"],
                        iterations=local_bootstrap_iterations,
                        ci=local_bootstrap_ci,
                        seed=self._seed_with_key(local_bootstrap_seed, mother_key, q, "falphaw"),
                    )
                    alpha_jackknife_std = self._jackknife_std(
                        integrands["ln_eps"], integrands["alpha_f"]
                    )
                    f_jackknife_std = self._jackknife_std(
                        integrands["ln_eps"], integrands["f_f"]
                    )
                    alpha_w_jackknife_std = self._jackknife_std(
                        integrands["ln_eps"], integrands["alpha_f"], weights=integrands["zeta"]
                    )
                    f_w_jackknife_std = self._jackknife_std(
                        integrands["ln_eps"], integrands["f_f"], weights=integrands["zeta"]
                    )
                    mother_scale_diagnostics_rows.extend(
                        self._scale_diagnostics_rows(
                            q=float(q),
                            scales=regression_scales,
                            x_alpha=integrands["ln_eps"],
                            y_alpha=integrands["alpha_f"],
                            y_f=integrands["f_f"],
                            mother_key=mother_key,
                            weights=integrands["zeta"],
                        )
                    )
                    zeta_mean, zeta_min = self._zeta_summary(integrands["zeta"])
                    reliable = self._is_reliable(
                        zeta_mean=zeta_mean,
                        r2_values=[alpha_w_r2, f_alpha_w_r2],
                        min_zeta=reliable_min_zeta,
                        min_r2=reliable_min_r2,
                    )
                    multi_mother_rows.append(
                        {
                            "mother_scale_m": meta["mother_scale_m"],
                            "mother_ix": meta["mother_ix"],
                            "mother_iy": meta["mother_iy"],
                            "mother_centroid_x": meta["mother_centroid_x"],
                            "mother_centroid_y": meta["mother_centroid_y"],
                            "measure_sum_m": meta["measure_sum_m"],
                            "cells_count": meta["cells_count"],
                            "q": float(q),
                            "scales_count": len(integrands["ln_eps"]),
                            "alpha": float(alpha),
                            "f_alpha": float(f_alpha),
                            "alpha_r2": float(alpha_r2),
                            "f_alpha_r2": float(f_alpha_r2),
                            "alpha_ts": float(alpha_ts),
                            "alpha_ts_r2": float(alpha_ts_r2),
                            "f_alpha_ts": float(f_alpha_ts),
                            "f_alpha_ts_r2": float(f_alpha_ts_r2),
                            "alpha_w": float(alpha_w),
                            "f_alpha_w": float(f_alpha_w),
                            "alpha_w_r2": float(alpha_w_r2),
                            "f_alpha_w_r2": float(f_alpha_w_r2),
                            "alpha_ci_low": self._scalar_or_blank(alpha_ci_low),
                            "alpha_ci_high": self._scalar_or_blank(alpha_ci_high),
                            "f_alpha_ci_low": self._scalar_or_blank(f_ci_low),
                            "f_alpha_ci_high": self._scalar_or_blank(f_ci_high),
                            "alpha_w_ci_low": self._scalar_or_blank(alpha_w_ci_low),
                            "alpha_w_ci_high": self._scalar_or_blank(alpha_w_ci_high),
                            "f_alpha_w_ci_low": self._scalar_or_blank(f_w_ci_low),
                            "f_alpha_w_ci_high": self._scalar_or_blank(f_w_ci_high),
                            "alpha_jackknife_std": self._scalar_or_blank(alpha_jackknife_std),
                            "f_alpha_jackknife_std": self._scalar_or_blank(f_jackknife_std),
                            "alpha_w_jackknife_std": self._scalar_or_blank(alpha_w_jackknife_std),
                            "f_alpha_w_jackknife_std": self._scalar_or_blank(f_w_jackknife_std),
                            "zeta_mean": float(zeta_mean),
                            "zeta_min": float(zeta_min),
                            "zeta_cov_exp": float(zeta_exponents[0]),
                            "zeta_mass_exp": float(zeta_exponents[1]),
                            "zeta_scale_exp": float(zeta_exponents[2]),
                            "zeta_neff_exp": float(zeta_exponents[3]),
                            "zeta_scale_floor": float(zeta_scale_floor),
                            "reliable": int(reliable),
                            "reliable_min_zeta": float(reliable_min_zeta),
                            "reliable_min_r2": float(reliable_min_r2),
                            "local_bootstrap_iterations": int(local_bootstrap_iterations),
                            "local_bootstrap_ci": float(local_bootstrap_ci),
                        }
                    )
                    if zeta_profiles:
                        for profile_name, profile_exponents in zeta_profiles.items():
                            sensitivity_zeta = self._zeta_list_for_mother(
                                mother_key=mother_key,
                                regression_scales=regression_scales,
                                zeta_by_mother_eps=zeta_by_profile[profile_name],
                            )
                            alpha_profile, f_profile, alpha_profile_r2, f_profile_r2 = self._chhabra_regression_metrics(
                                integrands["ln_eps"],
                                integrands["alpha_f"],
                                integrands["f_f"],
                                weights=sensitivity_zeta,
                            )
                            zeta_sensitivity_rows.append(
                                {
                                    "profile": profile_name,
                                    "mother_ix": int(meta["mother_ix"]),
                                    "mother_iy": int(meta["mother_iy"]),
                                    "q": float(q),
                                    "alpha_w": float(alpha_profile),
                                    "f_alpha_w": float(f_profile),
                                    "alpha_w_r2": float(alpha_profile_r2),
                                    "f_alpha_w_r2": float(f_profile_r2),
                                    "zeta_cov_exp": float(profile_exponents[0]),
                                    "zeta_mass_exp": float(profile_exponents[1]),
                                    "zeta_scale_exp": float(profile_exponents[2]),
                                    "zeta_neff_exp": float(profile_exponents[3]),
                                    "zeta_scale_floor": float(zeta_scale_floor),
                                }
                            )

            mono_agg_path = out_dir / "monofractal_mother_agg.csv"
            self._write_rows_csv(mono_agg_path, mono_mother_rows)
            written["monofractal_mother_agg"] = str(mono_agg_path)

            multi_agg_path = out_dir / "multifractal_mother_agg.csv"
            self._write_rows_csv(multi_agg_path, multi_mother_rows)
            written["multifractal_mother_agg"] = str(multi_agg_path)
            mother_diag_path = out_dir / "multifractal_mother_scale_diagnostics.csv"
            self._write_rows_csv(mother_diag_path, mother_scale_diagnostics_rows)
            written["multifractal_mother_scale_diagnostics"] = str(mother_diag_path)
            if zeta_sensitivity_rows:
                zeta_sensitivity_path = out_dir / "multifractal_mother_zeta_sensitivity.csv"
                self._write_rows_csv(zeta_sensitivity_path, zeta_sensitivity_rows)
                written["multifractal_mother_zeta_sensitivity"] = str(zeta_sensitivity_path)
                written["zeta_sensitivity_summary"] = self.export_zeta_sensitivity_summary(out_dir)

            if export_structural_stats and self._kind == "lines" and self._boundary_geom is not None:
                from .structural import compute_lineament_mother_structural_stats

                structural_rows = compute_lineament_mother_structural_stats(
                    line_geometries=self._line_geometries,
                    boundary_geom=self._boundary_geom,
                    mother_scale=mother_scale,
                    orientation_bin_degrees=orientation_bin_degrees,
                    origin=self._origin,
                )
                structural_path = out_dir / "lineament_mother_structural_stats.csv"
                self._write_rows_csv(structural_path, structural_rows)
                written["lineament_mother_structural_stats"] = str(structural_path)

            if export_network_stats and self._kind == "lines":
                from .network import compute_lineament_network_stats

                network_rows = [
                    compute_lineament_network_stats(
                        line_geometries=self._line_geometries,
                        boundary_geom=self._boundary_geom,
                    )
                ]
                network_path = out_dir / "lineament_network_stats.csv"
                self._write_rows_csv(network_path, network_rows)
                written["lineament_network_stats"] = str(network_path)

            if export_gis_package and self._active_crs is not None:
                from .geomatics import export_mother_geopackage

                gis_outputs = export_mother_geopackage(
                    out_dir,
                    crs=self._active_crs,
                    highlight_q=2.0,
                    reliable_min_zeta=reliable_min_zeta,
                    reliable_min_r2=reliable_min_r2,
                )
                written["mother_geopackage"] = str(gis_outputs["geopackage"])

        return written

    @staticmethod
    def export_analysis_report(output_dir: str | Path, result: MUSAResult) -> str:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        report_path = out_dir / "analysis_report.csv"

        rows: list[dict[str, Any]] = [
            {
                "row_type": "summary",
                "status": "accepted",
                "count": result.accepted_count,
                "min_r2": result.min_r2,
                "q": "",
                "dq": "",
                "tau": "",
                "alpha": "",
                "f_alpha": "",
                "r2": "",
                "alpha_r2": "",
                "f_alpha_r2": "",
                "p_value": "",
                "dq_ci_low": "",
                "dq_ci_high": "",
                "alpha_ci_low": "",
                "alpha_ci_high": "",
                "f_alpha_ci_low": "",
                "f_alpha_ci_high": "",
                "bootstrap_iterations": result.bootstrap_iterations,
                "bootstrap_ci": result.bootstrap_ci,
                "dq_ts": "",
                "alpha_ts": "",
                "f_alpha_ts": "",
                "dq_jackknife_std": "",
                "alpha_jackknife_std": "",
                "f_alpha_jackknife_std": "",
            },
            {
                "row_type": "summary",
                "status": "eliminated",
                "count": result.rejected_count,
                "min_r2": result.min_r2,
                "q": "",
                "dq": "",
                "tau": "",
                "alpha": "",
                "f_alpha": "",
                "r2": "",
                "alpha_r2": "",
                "f_alpha_r2": "",
                "p_value": "",
                "dq_ci_low": "",
                "dq_ci_high": "",
                "alpha_ci_low": "",
                "alpha_ci_high": "",
                "f_alpha_ci_low": "",
                "f_alpha_ci_high": "",
                "bootstrap_iterations": result.bootstrap_iterations,
                "bootstrap_ci": result.bootstrap_ci,
                "dq_ts": "",
                "alpha_ts": "",
                "f_alpha_ts": "",
                "dq_jackknife_std": "",
                "alpha_jackknife_std": "",
                "f_alpha_jackknife_std": "",
            },
        ]

        for i, (q, dq, tau, alpha, f_alpha, r2, alpha_r2, f_alpha_r2, p_value) in enumerate(
            zip(
                result.q,
                result.dq,
                result.tau,
                result.alpha,
                result.f_alpha,
                result.r2,
                result.alpha_r2,
                result.f_alpha_r2,
                result.p_values,
            )
        ):
            rows.append(
                {
                    "row_type": "detail",
                    "status": "accepted",
                    "count": "",
                    "min_r2": result.min_r2,
                    "q": float(q),
                    "dq": float(dq),
                    "tau": float(tau),
                    "alpha": float(alpha),
                    "f_alpha": float(f_alpha),
                    "r2": float(r2),
                    "alpha_r2": float(alpha_r2),
                    "f_alpha_r2": float(f_alpha_r2),
                    "p_value": float(p_value),
                    "dq_ci_low": MUSA._ci_value(result.dq_ci_low, i),
                    "dq_ci_high": MUSA._ci_value(result.dq_ci_high, i),
                    "alpha_ci_low": MUSA._ci_value(result.alpha_ci_low, i),
                    "alpha_ci_high": MUSA._ci_value(result.alpha_ci_high, i),
                    "f_alpha_ci_low": MUSA._ci_value(result.f_alpha_ci_low, i),
                    "f_alpha_ci_high": MUSA._ci_value(result.f_alpha_ci_high, i),
                    "bootstrap_iterations": result.bootstrap_iterations,
                    "bootstrap_ci": result.bootstrap_ci,
                    "dq_ts": MUSA._ci_value(result.dq_ts, i),
                    "alpha_ts": MUSA._ci_value(result.alpha_ts, i),
                    "f_alpha_ts": MUSA._ci_value(result.f_alpha_ts, i),
                    "dq_jackknife_std": MUSA._ci_value(result.dq_jackknife_std, i),
                    "alpha_jackknife_std": MUSA._ci_value(result.alpha_jackknife_std, i),
                    "f_alpha_jackknife_std": MUSA._ci_value(result.f_alpha_jackknife_std, i),
                }
            )

        for q, r2, alpha_r2, f_alpha_r2 in zip(
            result.rejected_q,
            result.rejected_r2,
            result.rejected_alpha_r2,
            result.rejected_f_alpha_r2,
        ):
            rows.append(
                {
                    "row_type": "detail",
                    "status": "eliminated",
                    "count": "",
                    "min_r2": result.min_r2,
                    "q": float(q),
                    "dq": "",
                    "tau": "",
                    "alpha": "",
                    "f_alpha": "",
                    "r2": float(r2),
                    "alpha_r2": float(alpha_r2),
                    "f_alpha_r2": float(f_alpha_r2),
                    "p_value": "",
                    "dq_ci_low": "",
                    "dq_ci_high": "",
                    "alpha_ci_low": "",
                    "alpha_ci_high": "",
                    "f_alpha_ci_low": "",
                    "f_alpha_ci_high": "",
                    "bootstrap_iterations": result.bootstrap_iterations,
                    "bootstrap_ci": result.bootstrap_ci,
                    "dq_ts": "",
                    "alpha_ts": "",
                    "f_alpha_ts": "",
                    "dq_jackknife_std": "",
                    "alpha_jackknife_std": "",
                    "f_alpha_jackknife_std": "",
                }
            )

        MUSA._write_rows_csv(report_path, rows)
        return str(report_path)

    @staticmethod
    def export_analysis_scale_diagnostics(output_dir: str | Path, result: MUSAResult) -> str:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        diagnostics_path = out_dir / "analysis_scale_diagnostics.csv"
        rows = result.scale_diagnostics or []
        MUSA._write_rows_csv(diagnostics_path, rows)
        return str(diagnostics_path)

    @staticmethod
    def export_zeta_sensitivity_summary(
        output_dir: str | Path,
        unstable_alpha_delta: float = 0.15,
        min_r2: float = 0.9,
    ) -> str:
        out_dir = Path(output_dir)
        source_path = out_dir / "multifractal_mother_zeta_sensitivity.csv"
        summary_path = out_dir / "zeta_sensitivity_summary.csv"
        if not source_path.is_file():
            MUSA._write_rows_csv(summary_path, [])
            return str(summary_path)

        with source_path.open(newline="", encoding="utf-8") as fp:
            rows = list(csv.DictReader(fp))
        baseline: dict[tuple[float, int, int], float] = {}
        for row in rows:
            if row.get("profile") != "baseline":
                continue
            key = (
                float(row["q"]),
                int(float(row["mother_ix"])),
                int(float(row["mother_iy"])),
            )
            baseline[key] = float(row["alpha_w"])

        grouped: dict[tuple[float, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            grouped[(float(row["q"]), str(row["profile"]))].append(row)

        summary_rows: list[dict[str, Any]] = []
        for (q, profile), profile_rows in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1])):
            alpha_vals = np.array([float(r["alpha_w"]) for r in profile_rows], dtype=float)
            f_vals = np.array([float(r["f_alpha_w"]) for r in profile_rows], dtype=float)
            deltas: list[float] = []
            reliable_count = 0
            for row in profile_rows:
                mother_key = (q, int(float(row["mother_ix"])), int(float(row["mother_iy"])))
                if mother_key in baseline:
                    deltas.append(abs(float(row["alpha_w"]) - baseline[mother_key]))
                if float(row.get("alpha_w_r2", "nan")) >= min_r2 and float(row.get("f_alpha_w_r2", "nan")) >= min_r2:
                    reliable_count += 1
            delta_vals = np.array(deltas, dtype=float)
            q25, q75 = np.percentile(alpha_vals, [25, 75]) if alpha_vals.size else (np.nan, np.nan)
            f_q25, f_q75 = np.percentile(f_vals, [25, 75]) if f_vals.size else (np.nan, np.nan)
            summary_rows.append(
                {
                    "q": float(q),
                    "profile": profile,
                    "mother_count": int(len(profile_rows)),
                    "alpha_w_median": float(np.median(alpha_vals)) if alpha_vals.size else "",
                    "alpha_w_iqr": float(q75 - q25) if alpha_vals.size else "",
                    "f_alpha_w_median": float(np.median(f_vals)) if f_vals.size else "",
                    "f_alpha_w_iqr": float(f_q75 - f_q25) if f_vals.size else "",
                    "median_abs_delta_vs_baseline": float(np.median(delta_vals)) if delta_vals.size else "",
                    "unstable_fraction": float(np.mean(delta_vals > unstable_alpha_delta)) if delta_vals.size else "",
                    "reliable_fraction": float(reliable_count / len(profile_rows)) if profile_rows else "",
                }
            )
        MUSA._write_rows_csv(summary_path, summary_rows)
        return str(summary_path)

    @staticmethod
    def resolutions_from_mother_cell(
        mother_cell_m: float,
        divisors: Iterable[float],
        include_mother: bool = True,
    ) -> np.ndarray:
        """
        Build square-cell resolutions from a mother cell using scale fractions.

        Example:
            mother_cell_m=4000, divisors=[2,4,6,8,16]
            -> [4000, 2000, 1000, 666.67, 500, 250] (if include_mother=True)
        """
        if not np.isfinite(mother_cell_m) or mother_cell_m <= 0:
            raise ValueError("mother_cell_m debe ser positivo y finito.")

        divs = np.array(list(divisors), dtype=float)
        if divs.size == 0:
            raise ValueError("Debes proporcionar al menos un divisor.")
        if np.any(~np.isfinite(divs)) or np.any(divs <= 0):
            raise ValueError("Los divisores deben ser positivos y finitos.")

        resolutions = mother_cell_m / divs
        if include_mother:
            resolutions = np.concatenate(([mother_cell_m], resolutions))
        return MUSA._validate_resolutions(resolutions)

    @staticmethod
    def _validate_resolutions(resolutions_m: Iterable[float]) -> np.ndarray:
        scales = np.array(list(resolutions_m), dtype=float)
        if scales.size < 3:
            raise ValueError("Debes proporcionar al menos 3 resoluciones para la regresion.")
        if np.any(~np.isfinite(scales)) or np.any(scales <= 0):
            raise ValueError("Las resoluciones deben ser positivas y finitas.")
        # Use unique values sorted from coarse to fine for interpretability.
        return np.array(sorted(np.unique(scales), reverse=True), dtype=float)

    @staticmethod
    def _mu_for_q(probs: np.ndarray, q: float) -> np.ndarray:
        if np.isclose(q, 1.0):
            return probs.copy()
        if np.isclose(q, 0.0):
            n_boxes = int(np.count_nonzero(probs > 0))
            return np.full(probs.shape, 1.0 / n_boxes, dtype=float)
        log_weights = q * np.log(probs)
        return np.exp(log_weights - logsumexp(log_weights))

    @staticmethod
    def _stabilize_probs_for_q(
        probs: np.ndarray,
        q: float,
        floor_fraction: float = 0.0,
    ) -> np.ndarray:
        if floor_fraction <= 0.0 or q >= 0.0 or np.isclose(q, 0.0):
            return probs.copy()
        n_boxes = int(np.count_nonzero(probs > 0))
        if n_boxes <= 0:
            return probs.copy()
        avg_prob = 1.0 / float(n_boxes)
        floor_value = min(0.5 * avg_prob, floor_fraction * max(abs(float(q)), 1.0) * avg_prob)
        stabilized = np.maximum(probs, floor_value)
        total = float(np.sum(stabilized))
        if total <= 0.0:
            return probs.copy()
        return stabilized / total

    @staticmethod
    def _zeta_mother_scale(
        mother_scale: float,
        eps: float,
        eps_coarse: float,
        eps_fine: float,
        m_total: float,
        m_finest: float,
        n_occupied: int,
        entropy: float = 0.0,
        exponents: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0),
        scale_floor: float = 0.25,
        possible_boxes: int | None = None,
    ) -> float:
        """
        Reliability weight zeta (ζ) for a mother cell at scale eps.

        ζ = c * m_r * s
          c = coverage (occupied child cells / possible child cells)
          m_r = relative mass vs finest scale in the same mother cell
          s = scale position between coarsest and finest regression scales
        Implementation also includes exp(entropy)/n_occupied and a scale floor.
        possible_boxes overrides the aligned square count for shifted supports.
        """
        exponents = MUSA._normalize_zeta_exponents(exponents)
        n_side = int(round(mother_scale / eps))
        n_total = max(n_side * n_side if possible_boxes is None else possible_boxes, 1)
        coverage = float(n_occupied) / float(n_total)
        mass_ratio = float(m_total / m_finest) if m_finest > 0 else 0.0
        if n_occupied > 0 and np.isfinite(entropy):
            effective_ratio = float(np.exp(entropy) / float(n_occupied))
            effective_ratio = min(max(effective_ratio, 0.0), 1.0)
        else:
            effective_ratio = 0.0
        ln_scale_denom = float(np.log(eps_coarse / eps_fine))
        if ln_scale_denom > 1e-12:
            raw_scale_position = float(np.log(eps_coarse / eps) / ln_scale_denom)
        else:
            raw_scale_position = 1.0
        raw_scale_position = min(max(raw_scale_position, 0.0), 1.0)
        scale_floor = min(max(float(scale_floor), 0.0), 1.0)
        scale_factor = scale_floor + (1.0 - scale_floor) * raw_scale_position
        cov_exp, mass_exp, scale_exp, effective_exp = exponents
        return (coverage**cov_exp) * (mass_ratio**mass_exp) * (scale_factor**scale_exp) * (
            effective_ratio**effective_exp
        )

    @staticmethod
    def _zeta_lookup_by_mother(
        mother_scale: float,
        regression_scales: np.ndarray,
        mother_meta: dict[tuple[int, int], dict[str, float | int]],
        mother_regression_stats: dict[tuple[int, int], list[dict[str, float | int]]],
        exponents: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0),
        scale_floor: float = 0.25,
    ) -> dict[tuple[int, int, float], float]:
        if regression_scales.size == 0:
            return {}
        eps_coarse = float(regression_scales[0])
        eps_fine = float(regression_scales[-1])
        lookup: dict[tuple[int, int, float], float] = {}
        for mother_key, mother_stats in mother_regression_stats.items():
            meta = mother_meta.get(mother_key)
            if meta is None:
                continue
            m_finest = float(meta["measure_sum_m"])
            for entry in mother_stats:
                eps = float(entry["eps"])
                zeta = MUSA._zeta_mother_scale(
                    mother_scale=mother_scale,
                    eps=eps,
                    eps_coarse=eps_coarse,
                    eps_fine=eps_fine,
                    m_total=float(entry["m_total"]),
                    m_finest=m_finest,
                    n_occupied=int(entry["n_occupied"]),
                    entropy=float(entry.get("entropy", 0.0)),
                    exponents=exponents,
                    scale_floor=scale_floor,
                )
                mkx, mky = mother_key
                lookup[(mkx, mky, eps)] = zeta
        return lookup

    @staticmethod
    def _zeta_list_for_mother(
        mother_key: tuple[int, int],
        regression_scales: np.ndarray,
        zeta_by_mother_eps: dict[tuple[int, int, float], float],
    ) -> list[float]:
        mkx, mky = mother_key
        zeta_list: list[float] = []
        for eps in regression_scales:
            zeta = zeta_by_mother_eps.get((mkx, mky, float(eps)), float("nan"))
            zeta_list.append(float(zeta))
        return zeta_list

    @staticmethod
    def _zeta_summary(zeta_values: list[float]) -> tuple[float, float]:
        finite = [float(v) for v in zeta_values if np.isfinite(v)]
        if not finite:
            return float("nan"), float("nan")
        return float(np.mean(finite)), float(np.min(finite))

    @staticmethod
    def _is_reliable(
        zeta_mean: float,
        r2_values: list[float],
        min_zeta: float,
        min_r2: float,
    ) -> bool:
        if not np.isfinite(zeta_mean) or zeta_mean < min_zeta:
            return False
        for r2 in r2_values:
            if not np.isfinite(r2) or r2 < min_r2:
                return False
        return True

    @staticmethod
    def _ci_value(values: np.ndarray | None, index: int) -> float | str:
        if values is None:
            return ""
        if index < 0 or index >= values.size:
            return ""
        value = float(values[index])
        return value if np.isfinite(value) else ""

    @staticmethod
    def _scalar_or_blank(value: float) -> float | str:
        return float(value) if np.isfinite(value) else ""

    @staticmethod
    def _seed_with_key(base_seed: int | None, *parts: Any) -> int | None:
        if base_seed is None:
            return None
        seed = int(base_seed)
        for part in parts:
            for ch in str(part):
                seed = ((seed * 131) + ord(ch)) & 0xFFFFFFFF
        return seed & 0xFFFFFFFF

    @staticmethod
    def _bootstrap_global_confidence_intervals(
        x_dq: np.ndarray,
        dq_features: np.ndarray,
        x_chhabra: np.ndarray,
        alpha_features: np.ndarray,
        f_features: np.ndarray,
        accepted_mask: np.ndarray,
        iterations: int,
        ci: float,
        seed: int | None,
    ) -> dict[str, np.ndarray]:
        if iterations <= 0:
            return {}
        n_scales = int(x_dq.size)
        if n_scales < 3:
            return {}

        rng = np.random.default_rng(seed)
        n_q = int(dq_features.shape[0])
        dq_boot = np.full((iterations, n_q), np.nan, dtype=float)
        alpha_boot = np.full((iterations, n_q), np.nan, dtype=float)
        f_boot = np.full((iterations, n_q), np.nan, dtype=float)

        for b in range(iterations):
            idx = rng.integers(0, n_scales, size=n_scales)
            if np.unique(idx).size < 2:
                continue
            for j in range(n_q):
                dq_boot[b, j] = MUSA._slope_only(x_dq[idx], dq_features[j, idx])
                alpha_boot[b, j] = MUSA._slope_only(x_chhabra[idx], alpha_features[j, idx])
                f_boot[b, j] = MUSA._slope_only(x_chhabra[idx], f_features[j, idx])

        accepted_idx = np.where(accepted_mask)[0]
        alpha_tail = (1.0 - ci) / 2.0
        percentiles = [100.0 * alpha_tail, 100.0 * (1.0 - alpha_tail)]

        def _bounds(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            subset = samples[:, accepted_idx]
            low = np.full(accepted_idx.size, np.nan, dtype=float)
            high = np.full(accepted_idx.size, np.nan, dtype=float)
            for col in range(subset.shape[1]):
                finite = subset[:, col][np.isfinite(subset[:, col])]
                if finite.size:
                    low[col], high[col] = np.percentile(finite, percentiles)
            return low, high

        dq_low, dq_high = _bounds(dq_boot)
        alpha_low, alpha_high = _bounds(alpha_boot)
        f_low, f_high = _bounds(f_boot)
        return {
            "dq_ci_low": dq_low,
            "dq_ci_high": dq_high,
            "alpha_ci_low": alpha_low,
            "alpha_ci_high": alpha_high,
            "f_alpha_ci_low": f_low,
            "f_alpha_ci_high": f_high,
        }

    @staticmethod
    def _bootstrap_regression_ci(
        x_values: list[float],
        y_values: list[float],
        weights: list[float] | None = None,
        iterations: int = 0,
        ci: float = 0.95,
        seed: int | None = None,
    ) -> tuple[float, float]:
        if iterations <= 0 or len(x_values) < 3 or len(y_values) < 3:
            return float("nan"), float("nan")
        x = np.array(x_values, dtype=float)
        y = np.array(y_values, dtype=float)
        w = None if weights is None else np.array(weights, dtype=float)
        rng = np.random.default_rng(seed)
        boot = np.full(iterations, np.nan, dtype=float)
        for i in range(iterations):
            idx = rng.integers(0, len(x), size=len(x))
            if np.unique(idx).size < 2:
                continue
            if w is None:
                boot[i], _r2 = MUSA._linear_regression_metrics(x[idx].tolist(), y[idx].tolist())
            else:
                boot[i], _r2 = MUSA._linear_regression_metrics(
                    x[idx].tolist(), y[idx].tolist(), weights=w[idx].tolist()
                )
        finite = boot[np.isfinite(boot)]
        if finite.size == 0:
            return float("nan"), float("nan")
        alpha_tail = (1.0 - ci) / 2.0
        low, high = np.percentile(finite, [100.0 * alpha_tail, 100.0 * (1.0 - alpha_tail)])
        return float(low), float(high)

    @staticmethod
    def _theil_sen_metrics(x_values: list[float], y_values: list[float]) -> tuple[float, float]:
        if len(x_values) < 2 or len(y_values) < 2:
            return float("nan"), float("nan")
        x = np.array(x_values, dtype=float)
        y = np.array(y_values, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if np.count_nonzero(mask) < 2:
            return float("nan"), float("nan")
        slope, intercept, _lo, _hi = stats.theilslopes(y[mask], x[mask])
        y_hat = slope * x[mask] + intercept
        ss_res = float(np.sum((y[mask] - y_hat) ** 2))
        ss_tot = float(np.sum((y[mask] - np.mean(y[mask])) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else float("nan")
        return float(slope), float(r2)

    @staticmethod
    def _jackknife_std(
        x_values: list[float],
        y_values: list[float],
        weights: list[float] | None = None,
    ) -> float:
        n = len(x_values)
        if n < 3 or len(y_values) != n:
            return float("nan")
        estimates: list[float] = []
        for i in range(n):
            x_sub = [v for j, v in enumerate(x_values) if j != i]
            y_sub = [v for j, v in enumerate(y_values) if j != i]
            if weights is None:
                slope, _r2 = MUSA._linear_regression_metrics(x_sub, y_sub)
            else:
                w_sub = [v for j, v in enumerate(weights) if j != i]
                slope, _r2 = MUSA._linear_regression_metrics(x_sub, y_sub, weights=w_sub)
            estimates.append(slope)
        finite = np.array([v for v in estimates if np.isfinite(v)], dtype=float)
        if finite.size == 0:
            return float("nan")
        return float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0

    @staticmethod
    def _jackknife_std_by_q(
        rows: list[dict[str, Any]],
        q_key: str,
        value_key: str,
    ) -> np.ndarray:
        grouped: dict[float, list[float]] = defaultdict(list)
        ordered: list[float] = []
        for row in rows:
            q = float(row[q_key])
            if q not in grouped:
                ordered.append(q)
            value = float(row.get(value_key, float("nan")))
            if np.isfinite(value):
                grouped[q].append(value)
        out = np.full(len(ordered), np.nan, dtype=float)
        for i, q in enumerate(ordered):
            vals = np.array(grouped[q], dtype=float)
            if vals.size > 1:
                out[i] = float(np.std(vals, ddof=1))
            elif vals.size == 1:
                out[i] = 0.0
        return out

    @staticmethod
    def _scale_diagnostics_rows(
        q: float,
        scales: np.ndarray,
        x_alpha: list[float],
        y_alpha: list[float],
        y_f: list[float],
        x_dq: list[float] | None = None,
        y_dq: list[float] | None = None,
        mother_key: tuple[int, int] | None = None,
        weights: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        x = np.array(x_alpha, dtype=float)
        if x.size < 3:
            return rows
        leverage = MUSA._leverage_values(x)
        cook_alpha = MUSA._cook_distance(x, np.array(y_alpha, dtype=float))
        cook_f = MUSA._cook_distance(x, np.array(y_f, dtype=float))
        cook_dq = (
            MUSA._cook_distance(np.array(x_dq, dtype=float), np.array(y_dq, dtype=float))
            if x_dq is not None and y_dq is not None
            else np.full(x.size, np.nan, dtype=float)
        )
        for i in range(x.size):
            alpha_loo, _alpha_loo_r2 = MUSA._linear_regression_metrics(
                [v for j, v in enumerate(x_alpha) if j != i],
                [v for j, v in enumerate(y_alpha) if j != i],
            )
            f_loo, _f_loo_r2 = MUSA._linear_regression_metrics(
                [v for j, v in enumerate(x_alpha) if j != i],
                [v for j, v in enumerate(y_f) if j != i],
            )
            row = {
                "q": float(q),
                "scale_m": float(scales[i]),
                "leverage": float(leverage[i]),
                "cook_alpha": float(cook_alpha[i]),
                "cook_f_alpha": float(cook_f[i]),
                "alpha_loo": float(alpha_loo),
                "f_alpha_loo": float(f_loo),
                "accepted_q": True,
            }
            if weights is not None:
                alpha_w_loo, _alpha_w_loo_r2 = MUSA._linear_regression_metrics(
                    [v for j, v in enumerate(x_alpha) if j != i],
                    [v for j, v in enumerate(y_alpha) if j != i],
                    weights=[v for j, v in enumerate(weights) if j != i],
                )
                f_w_loo, _f_w_loo_r2 = MUSA._linear_regression_metrics(
                    [v for j, v in enumerate(x_alpha) if j != i],
                    [v for j, v in enumerate(y_f) if j != i],
                    weights=[v for j, v in enumerate(weights) if j != i],
                )
                row["alpha_w_loo"] = float(alpha_w_loo)
                row["f_alpha_w_loo"] = float(f_w_loo)
            if x_dq is not None and y_dq is not None:
                dq_loo, _dq_loo_r2 = MUSA._linear_regression_metrics(
                    [v for j, v in enumerate(x_dq) if j != i],
                    [v for j, v in enumerate(y_dq) if j != i],
                )
                row["dq_loo"] = float(dq_loo)
                row["cook_dq"] = float(cook_dq[i])
            if mother_key is not None:
                row["mother_ix"] = int(mother_key[0])
                row["mother_iy"] = int(mother_key[1])
            rows.append(row)
        return rows

    @staticmethod
    def _leverage_values(x: np.ndarray) -> np.ndarray:
        n = x.size
        if n == 0:
            return np.array([], dtype=float)
        x_mean = float(np.mean(x))
        sxx = float(np.sum((x - x_mean) ** 2))
        if sxx <= 0:
            return np.full(n, np.nan, dtype=float)
        return (1.0 / n) + (((x - x_mean) ** 2) / sxx)

    @staticmethod
    def _cook_distance(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        if x.size < 3 or y.size != x.size:
            return np.full(x.size, np.nan, dtype=float)
        slope, intercept, _r, _p, _e = stats.linregress(x, y)
        y_hat = slope * x + intercept
        residuals = y - y_hat
        leverage = MUSA._leverage_values(x)
        mse = float(np.sum(residuals**2) / max(x.size - 2, 1))
        if mse <= 0:
            return np.full(x.size, np.nan, dtype=float)
        return ((residuals**2) / (2.0 * mse)) * (leverage / ((1.0 - leverage) ** 2))

    @staticmethod
    def _zeta_profiles(
        base_exponents: tuple[float, ...],
        enabled: bool,
    ) -> dict[str, tuple[float, float, float, float]]:
        if not enabled:
            return {}
        base_exponents = MUSA._normalize_zeta_exponents(base_exponents)
        return {
            "baseline": base_exponents,
            "coverage_heavy": (base_exponents[0] + 1.0, base_exponents[1], base_exponents[2], base_exponents[3]),
            "mass_heavy": (base_exponents[0], base_exponents[1] + 1.0, base_exponents[2], base_exponents[3]),
            "scale_heavy": (base_exponents[0], base_exponents[1], base_exponents[2] + 1.0, base_exponents[3]),
            "neff_heavy": (base_exponents[0], base_exponents[1], base_exponents[2], base_exponents[3] + 1.0),
            "soft": (
                max(base_exponents[0] * 0.5, 0.0),
                max(base_exponents[1] * 0.5, 0.0),
                max(base_exponents[2] * 0.5, 0.0),
                max(base_exponents[3] * 0.5, 0.0),
            ),
        }

    @staticmethod
    def _normalize_zeta_exponents(exponents: tuple[float, ...]) -> tuple[float, float, float, float]:
        values = tuple(float(v) for v in exponents)
        if len(values) == 3:
            values = (values[0], values[1], values[2], 1.0)
        if len(values) != 4 or any((not np.isfinite(v)) or v < 0.0 for v in values):
            raise ValueError("zeta_exponents debe tener 3 o 4 valores finitos y >= 0.")
        return values

    @staticmethod
    def _recompute_zeta_list(
        mother_key: tuple[int, int],
        regression_scales: np.ndarray,
        mother_scale: float,
        mother_meta: dict[tuple[int, int], dict[str, float | int]],
        mother_regression_stats: dict[tuple[int, int], list[dict[str, float | int]]],
        exponents: tuple[float, ...],
        scale_floor: float = 0.25,
    ) -> list[float]:
        zeta_lookup = MUSA._zeta_lookup_by_mother(
            mother_scale=mother_scale,
            regression_scales=regression_scales,
            mother_meta=mother_meta,
            mother_regression_stats=mother_regression_stats,
            exponents=exponents,
            scale_floor=scale_floor,
        )
        return MUSA._zeta_list_for_mother(
            mother_key=mother_key,
            regression_scales=regression_scales,
            zeta_by_mother_eps=zeta_lookup,
        )

    @staticmethod
    def _slope_only(x_values: np.ndarray, y_values: np.ndarray) -> float:
        x = np.asarray(x_values, dtype=float)
        y = np.asarray(y_values, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if np.count_nonzero(mask) < 2:
            return float("nan")
        x = x[mask]
        y = y[mask]
        x_mean = float(np.mean(x))
        y_mean = float(np.mean(y))
        var_x = float(np.sum((x - x_mean) ** 2))
        if var_x <= 0:
            return float("nan")
        cov = float(np.sum((x - x_mean) * (y - y_mean)))
        return float(cov / var_x)

    @staticmethod
    def _weighted_regression_slope_r2(
        x_values: list[float],
        y_values: list[float],
        weights: list[float],
    ) -> tuple[float, float]:
        if len(x_values) < 2 or len(y_values) < 2 or len(weights) < 2:
            return float("nan"), float("nan")
        x = np.array(x_values, dtype=float)
        y = np.array(y_values, dtype=float)
        w = np.array(weights, dtype=float)
        w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
        if float(np.sum(w)) <= 0:
            return float("nan"), float("nan")
        w = w / np.sum(w)
        x_mean = float(np.sum(w * x))
        y_mean = float(np.sum(w * y))
        cov = float(np.sum(w * (x - x_mean) * (y - y_mean)))
        var_x = float(np.sum(w * (x - x_mean) ** 2))
        var_y = float(np.sum(w * (y - y_mean) ** 2))
        if var_x <= 0:
            return float("nan"), float("nan")
        slope = cov / var_x
        r2 = (cov**2) / (var_x * var_y) if var_y > 0 else float("nan")
        return float(slope), float(r2)

    @staticmethod
    def _linear_regression_metrics(
        x_values: list[float],
        y_values: list[float],
        weights: list[float] | None = None,
    ) -> tuple[float, float]:
        if weights is not None:
            return MUSA._weighted_regression_slope_r2(x_values, y_values, weights)
        if len(x_values) < 2 or len(y_values) < 2:
            return float("nan"), float("nan")
        slope, _intercept, r_value, _p_value, _std_err = stats.linregress(
            np.array(x_values, dtype=float),
            np.array(y_values, dtype=float),
        )
        return float(slope), float(r_value**2)

    @staticmethod
    def _chhabra_regression_metrics(
        ln_eps: list[float],
        alpha_features: list[float],
        f_features: list[float],
        weights: list[float] | None = None,
    ) -> tuple[float, float, float, float]:
        if len(ln_eps) < 2:
            return float("nan"), float("nan"), float("nan"), float("nan")
        if weights is not None:
            alpha_slope, alpha_r2 = MUSA._weighted_regression_slope_r2(
                ln_eps, alpha_features, weights
            )
            f_slope, f_r2 = MUSA._weighted_regression_slope_r2(ln_eps, f_features, weights)
            return alpha_slope, f_slope, alpha_r2, f_r2
        x = np.array(ln_eps, dtype=float)
        alpha_slope, _alpha_intercept, alpha_r_value, _alpha_p_value, _alpha_std_err = stats.linregress(
            x, np.array(alpha_features, dtype=float)
        )
        f_slope, _f_intercept, f_r_value, _f_p_value, _f_std_err = stats.linregress(
            x, np.array(f_features, dtype=float)
        )
        return float(alpha_slope), float(f_slope), float(alpha_r_value**2), float(f_r_value**2)

    def _cell_measure_for_scale(self, eps: float, cell_length_threshold_m: float = 0.0) -> dict[tuple[int, int], float]:
        if self._kind == "lines":
            return self._line_length_cells(
                self._line_geometries,
                eps,
                self._origin,
                min_cell_length=cell_length_threshold_m,
            )
        return self._point_count_cells(self.points, eps, self._origin)

    def _probabilities_for_scale(self, eps: float, cell_length_threshold_m: float = 0.0) -> np.ndarray:
        cell_measures = self._cell_measure_for_scale(eps=eps, cell_length_threshold_m=cell_length_threshold_m)
        if not cell_measures:
            return np.array([], dtype=float)
        weights = np.array(list(cell_measures.values()), dtype=float)
        return weights / np.sum(weights)

    @staticmethod
    def _point_probabilities(points: np.ndarray, eps: float, origin: np.ndarray | None) -> np.ndarray:
        if origin is None:
            # Keep points in [0, 1). If a point is exactly 1 due to precision, clamp.
            idx = np.floor(np.clip(points, 0.0, 1.0 - 1e-12) / eps).astype(np.int64)
        else:
            idx = np.floor((points - origin) / eps).astype(np.int64)
        _, counts = np.unique(idx, axis=0, return_counts=True)
        probs = counts.astype(float)
        return probs / probs.sum()

    @staticmethod
    def _point_count_cells(points: np.ndarray, eps: float, origin: np.ndarray | None) -> dict[tuple[int, int], float]:
        if origin is None:
            idx = np.floor(np.clip(points, 0.0, 1.0 - 1e-12) / eps).astype(np.int64)
        else:
            idx = np.floor((points - origin) / eps).astype(np.int64)
        uniq, counts = np.unique(idx, axis=0, return_counts=True)
        return {(int(k[0]), int(k[1])): float(c) for k, c in zip(uniq, counts)}

    @staticmethod
    def _normalize_unit(points: np.ndarray) -> np.ndarray:
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        spans = maxs - mins
        spans[spans == 0] = 1.0
        normalized = (points - mins) / spans
        return np.clip(normalized, 0.0, 1.0)

    def _prepare_input(
        self,
        data: Any,
        boundary: Any | None,
        normalize: bool,
        gis_reproject_to: str,
    ) -> dict[str, Any]:
        # GIS path / GeoDataFrame first
        if isinstance(data, (str, Path)) or hasattr(data, "geometry"):
            return self._prepare_gis_input(
                data=data,
                boundary=boundary,
                gis_reproject_to=gis_reproject_to,
            )

        points = self._coerce_to_points(data)
        if points.ndim != 2 or points.shape[1] != 2:
            raise ValueError("Los datos deben resolverse a una matriz de forma (n, 2).")
        if len(points) < 10:
            raise ValueError("Se requieren al menos 10 puntos para un analisis estable.")
        if normalize:
            return {"kind": "points", "points": self._normalize_unit(points), "origin": None, "crs": None}
        origin = points.min(axis=0)
        return {"kind": "points", "points": points, "origin": origin, "crs": None}

    @staticmethod
    def _coerce_to_points(data: Any) -> np.ndarray:
        if isinstance(data, np.ndarray):
            return np.asarray(data, dtype=float)

        if hasattr(data, "to_numpy") and hasattr(data, "columns"):
            # pandas-like DataFrame
            cols = list(getattr(data, "columns", []))
            lower = [c.lower() for c in cols]
            if "x" in lower and "y" in lower:
                xcol = cols[lower.index("x")]
                ycol = cols[lower.index("y")]
                return data[[xcol, ycol]].to_numpy(dtype=float)
            return data.to_numpy(dtype=float)

        raise TypeError(
            "Formato no soportado. Usa numpy array, DataFrame, GeoDataFrame o ruta vectorial."
        )

    def _prepare_gis_input(self, data: Any, boundary: Any | None, gis_reproject_to: str) -> dict[str, Any]:
        try:
            import geopandas as gpd
            from shapely.geometry import LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon
        except Exception as exc:  # pragma: no cover
            raise ImportError(
                "Para usar entradas GIS instala extras: pip install musa-multifractal[gis]"
            ) from exc

        gdf = gpd.read_file(data) if isinstance(data, (str, Path)) else data.copy()
        if gdf.crs is None:
            raise ValueError("La capa GIS no tiene CRS definido. Define el CRS antes del analisis.")

        if gdf.crs.is_geographic:
            if gis_reproject_to == "auto":
                utm = gdf.estimate_utm_crs()
                if utm is None:
                    raise ValueError("No se pudo estimar UTM para reproyeccion metrica automatica.")
                gdf = gdf.to_crs(utm)
            else:
                gdf = gdf.to_crs(gis_reproject_to)

        boundary_geom = None
        boundary_bounds = None
        if boundary is not None:
            bdf = gpd.read_file(boundary) if isinstance(boundary, (str, Path)) else boundary.copy()
            if bdf.crs is None:
                raise ValueError("El boundary no tiene CRS definido.")
            if bdf.crs != gdf.crs:
                bdf = bdf.to_crs(gdf.crs)
            boundary_geom = bdf.geometry.union_all()
            if boundary_geom is None or boundary_geom.is_empty:
                raise ValueError("El boundary esta vacio o invalido.")
            boundary_bounds = bdf.total_bounds

        geoms = list(gdf.geometry.dropna())
        has_lines = any(isinstance(geom, (LineString, MultiLineString)) for geom in geoms)

        if has_lines:
            if boundary is None:
                raise ValueError("Para lineamientos debes proporcionar boundary (path o GeoDataFrame).")
            lines: list[Any] = []
            for geom in geoms:
                if boundary_geom is not None:
                    geom = geom.intersection(boundary_geom)
                    if geom.is_empty:
                        continue
                if isinstance(geom, LineString):
                    if geom.length > 0:
                        lines.append(geom)
                elif isinstance(geom, MultiLineString):
                    for line in geom.geoms:
                        if line.length > 0:
                            lines.append(line)
            if not lines:
                raise ValueError("No se encontraron lineamientos validos en la capa GIS.")
            bounds = boundary_bounds if boundary_bounds is not None else gdf.total_bounds
            origin = np.array([bounds[0], bounds[1]], dtype=float)
            return {
                "kind": "lines",
                "line_geometries": lines,
                "source_gdf": gdf,
                "origin": origin,
                "boundary_geom": boundary_geom,
                "crs": gdf.crs,
            }

        coords: list[tuple[float, float]] = []
        for geom in geoms:
            if isinstance(geom, Point):
                coords.append((geom.x, geom.y))
            elif isinstance(geom, MultiPoint):
                coords.extend((g.x, g.y) for g in geom.geoms)
            elif isinstance(geom, Polygon):
                coords.extend(list(geom.exterior.coords))
            elif isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    coords.extend(list(poly.exterior.coords))

        if not coords:
            raise ValueError("La capa GIS no contiene geometria compatible (linea, punto o poligono).")

        points = np.asarray(coords, dtype=float)
        origin = points.min(axis=0)
        return {"kind": "points", "points": points, "origin": origin, "boundary_geom": boundary_geom, "crs": gdf.crs}

    @staticmethod
    def _line_length_cells(
        line_geometries: list[Any],
        eps: float,
        origin: np.ndarray,
        min_cell_length: float = 0.0,
    ) -> dict[tuple[int, int], float]:
        from .mass_partition import line_masses

        weights_by_cell = line_masses(line_geometries, eps, origin)
        # The threshold applies to the complete cell, not individual features.
        return {key: value for key, value in weights_by_cell.items()
                if value > min_cell_length}

    def _cell_centroid(self, ix: int, iy: int, eps: float) -> tuple[float, float]:
        if self._origin is None:
            return (float(ix + 0.5) * float(eps), float(iy + 0.5) * float(eps))
        return (
            float(self._origin[0]) + (float(ix) + 0.5) * float(eps),
            float(self._origin[1]) + (float(iy) + 0.5) * float(eps),
        )

    def _mother_key_from_centroid(self, cx: float, cy: float, mother_scale: float) -> tuple[int, int]:
        if self._origin is None:
            return (int(np.floor(cx / mother_scale)), int(np.floor(cy / mother_scale)))
        return (
            int(np.floor((cx - float(self._origin[0])) / mother_scale)),
            int(np.floor((cy - float(self._origin[1])) / mother_scale)),
        )

    @staticmethod
    def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            # Keep predictable output files even when empty.
            path.write_text("", encoding="utf-8")
            return
        fields = list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
