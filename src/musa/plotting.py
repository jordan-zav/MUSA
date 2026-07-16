from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np

from .core import MUSAResult
from .spectrum import fit_quadratic_spectrum


def plot_loglog(result: MUSAResult, q: float = 0.0, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4.5))

    idx = int(np.argmin(np.abs(result.q - q)))
    y = result.dq[idx] * np.log(1.0 / result.scales)
    x = np.log(1.0 / result.scales)
    ax.plot(x, y, "o-", lw=1.5)
    ax.set_title(f"Log-Log Fit (q={result.q[idx]:.2f})")
    ax.set_xlabel("log(1/epsilon)")
    ax.set_ylabel("Scaled measure")
    ax.grid(alpha=0.3)
    return ax


def plot_singularity_spectrum(result: MUSAResult, ax=None):
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 4.5))

    order = np.argsort(result.alpha)
    ax.plot(result.alpha[order], result.f_alpha[order], "o-", lw=1.7, color="#1f4f72")
    ax.set_title("MUSA: Singularity Spectrum f(alpha)")
    ax.set_xlabel("alpha")
    ax.set_ylabel("f(alpha)")
    ax.grid(alpha=0.3)
    return ax


def _read_mother_agg_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fp:
        return list(csv.DictReader(fp))


def _to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _pick_highlight_q(available_q: np.ndarray, highlight_q: float) -> float:
    if available_q.size == 0:
        return highlight_q
    idx = int(np.argmin(np.abs(available_q - highlight_q)))
    return float(available_q[idx])


def _global_spectrum_at_q(result: MUSAResult, q_value: float) -> tuple[float, float] | None:
    matches = np.where(np.isclose(result.q, q_value))[0]
    if matches.size == 0:
        return None
    idx = int(matches[0])
    return float(result.alpha[idx]), float(result.f_alpha[idx])


def _asymmetric_errors(values: np.ndarray, low: np.ndarray | None, high: np.ndarray | None):
    if low is None or high is None:
        return None
    if low.size != values.size or high.size != values.size:
        return None
    lower = np.maximum(values - low, 0.0)
    upper = np.maximum(high - values, 0.0)
    if not np.any(np.isfinite(lower) & np.isfinite(upper)):
        return None
    return np.vstack([lower, upper])


def _mother_rows_for_q(rows: list[dict[str, str]], q_value: float) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for row in rows:
        if not np.isclose(_to_float(row.get("q", "nan")), q_value):
            continue
        if not np.isfinite(_to_float(row.get("alpha_w", "nan"))):
            continue
        if not np.isfinite(_to_float(row.get("f_alpha_w", "nan"))):
            continue
        selected.append(row)
    return selected


def _unique_mother_zeta_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[int, int]] = set()
    unique_rows: list[dict[str, str]] = []
    for row in rows:
        key = (int(float(row["mother_ix"])), int(float(row["mother_iy"])))
        if key in seen:
            continue
        if not np.isfinite(_to_float(row.get("zeta_mean", "nan"))):
            continue
        seen.add(key)
        unique_rows.append(row)
    return unique_rows


def export_analysis_plots(output_dir: str | Path, result: MUSAResult) -> dict[str, str]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: dict[str, str] = {}

    r2_path = out_dir / "r2_fit_quality.png"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.scatter(result.q, result.r2, color="#1f77b4", label="Accepted Dq", s=42)
    ax.scatter(result.q, result.alpha_r2, color="#2ca02c", label="Accepted alpha", s=36, marker="s")
    ax.scatter(result.q, result.f_alpha_r2, color="#9467bd", label="Accepted f(alpha)", s=36, marker="^")
    if result.rejected_count:
        ax.scatter(result.rejected_q, result.rejected_r2, color="#d62728", label="Eliminated Dq", s=42)
        ax.scatter(
            result.rejected_q,
            result.rejected_alpha_r2,
            color="#ff7f0e",
            label="Eliminated alpha",
            s=36,
            marker="s",
        )
        ax.scatter(
            result.rejected_q,
            result.rejected_f_alpha_r2,
            color="#8c564b",
            label="Eliminated f(alpha)",
            s=36,
            marker="^",
        )
    ax.axhline(result.min_r2, color="#444444", linestyle="--", linewidth=1.2, label="R2 threshold")
    ax.set_title("R2 Fit Quality")
    ax.set_xlabel("q")
    ax.set_ylabel("R2")
    ax.set_ylim(0.0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(r2_path, dpi=160)
    plt.close(fig)
    written["r2_fit_quality"] = str(r2_path)

    scatter_path = out_dir / "dq_scatterplot.png"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    dq_yerr = _asymmetric_errors(result.dq, result.dq_ci_low, result.dq_ci_high)
    if dq_yerr is not None:
        ax.errorbar(
            result.q,
            result.dq,
            yerr=dq_yerr,
            fmt="none",
            ecolor="#666666",
            elinewidth=1.0,
            alpha=0.65,
            capsize=2,
            zorder=1,
        )
    points = ax.scatter(result.q, result.dq, c=result.r2, cmap="viridis", s=46, zorder=2)
    ax.set_title("Dq Scatterplot")
    ax.set_xlabel("q")
    ax.set_ylabel("Dq")
    ax.grid(alpha=0.3)
    fig.colorbar(points, ax=ax, label="R2")
    fig.tight_layout()
    fig.savefig(scatter_path, dpi=160)
    plt.close(fig)
    written["dq_scatterplot"] = str(scatter_path)

    spectrum_path = out_dir / "multifractal_singularity_spectrum.png"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    order = np.argsort(result.alpha)
    alpha_xerr = _asymmetric_errors(result.alpha, result.alpha_ci_low, result.alpha_ci_high)
    f_yerr = _asymmetric_errors(result.f_alpha, result.f_alpha_ci_low, result.f_alpha_ci_high)
    if alpha_xerr is not None or f_yerr is not None:
        ax.errorbar(
            result.alpha,
            result.f_alpha,
            xerr=alpha_xerr,
            yerr=f_yerr,
            fmt="none",
            ecolor="#666666",
            elinewidth=1.0,
            alpha=0.65,
            capsize=2,
            zorder=1,
        )
    ax.plot(result.alpha[order], result.f_alpha[order], "o-", linewidth=1.7, color="#1f4f72")
    fit = fit_quadratic_spectrum(result.alpha, result.f_alpha)
    if fit["quadratic_r2"] != "" and np.isfinite(float(fit["quadratic_r2"])):
        x_fit = np.linspace(float(np.min(result.alpha)), float(np.max(result.alpha)), 160)
        y_fit = (
            float(fit["quadratic_a"]) * x_fit**2
            + float(fit["quadratic_b"]) * x_fit
            + float(fit["quadratic_c"])
        )
        ax.plot(
            x_fit,
            y_fit,
            "--",
            linewidth=1.3,
            color="#7a4b22",
            label=f"Quadratic fit R2={float(fit['quadratic_r2']):.3f}",
        )
        ax.legend(loc="best")
    ax.set_title("Singularity vs Multifractal Spectrum")
    ax.set_xlabel("alpha")
    ax.set_ylabel("f(alpha)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(spectrum_path, dpi=160)
    plt.close(fig)
    written["multifractal_singularity_spectrum"] = str(spectrum_path)

    spectrum_q_path = out_dir / "multifractal_singularity_spectrum_by_q.png"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    order_q = np.argsort(result.q)
    ax.plot(result.alpha[order_q], result.f_alpha[order_q], "-", linewidth=1.1, color="#8b7d6b", alpha=0.75)
    points = ax.scatter(
        result.alpha,
        result.f_alpha,
        c=result.q,
        cmap="coolwarm",
        s=58,
        edgecolors="white",
        linewidths=0.6,
        zorder=3,
    )
    for q_value, alpha_value, f_value in zip(result.q, result.alpha, result.f_alpha):
        ax.annotate(
            f"{q_value:g}",
            (alpha_value, f_value),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=7,
            color="#2f3e46",
        )
    ax.set_title("Singularity Spectrum Colored by q")
    ax.set_xlabel("alpha")
    ax.set_ylabel("f(alpha)")
    ax.grid(alpha=0.3)
    fig.colorbar(points, ax=ax, label="q")
    fig.tight_layout()
    fig.savefig(spectrum_q_path, dpi=160)
    plt.close(fig)
    written["multifractal_singularity_spectrum_by_q"] = str(spectrum_q_path)

    return written


def export_mother_plots(
    output_dir: str | Path,
    result: MUSAResult,
    highlight_q: float = 2.0,
    min_zeta: float = 0.0,
    plot_all_q: bool = True,
) -> dict[str, str]:
    """
    Export spatial and statistical plots from multifractal_mother_agg.csv.

    Generates mother-cell weighted diagnostics alongside the global spectrum.
    """
    out_dir = Path(output_dir)
    mother_path = out_dir / "multifractal_mother_agg.csv"
    rows = _read_mother_agg_rows(mother_path)
    if not rows:
        return {}

    available_q = np.array(sorted({ _to_float(r["q"]) for r in rows if np.isfinite(_to_float(r.get("q", "nan"))) }))
    if available_q.size == 0:
        return {}

    q_value = _pick_highlight_q(available_q, highlight_q)
    q_rows = _mother_rows_for_q(rows, q_value)
    if min_zeta > 0:
        q_rows = [r for r in q_rows if _to_float(r.get("zeta_mean", "nan")) >= min_zeta]

    written: dict[str, str] = {}
    if not q_rows:
        return written

    alpha_w = np.array([_to_float(r["alpha_w"]) for r in q_rows], dtype=float)
    f_alpha_w = np.array([_to_float(r["f_alpha_w"]) for r in q_rows], dtype=float)
    alpha_ols = np.array([_to_float(r["alpha"]) for r in q_rows], dtype=float)
    zeta_mean = np.array([_to_float(r["zeta_mean"]) for r in q_rows], dtype=float)
    measure_sum = np.array([_to_float(r["measure_sum_m"]) for r in q_rows], dtype=float)
    cx = np.array([_to_float(r["mother_centroid_x"]) for r in q_rows], dtype=float)
    cy = np.array([_to_float(r["mother_centroid_y"]) for r in q_rows], dtype=float)

    q_label = f"{q_value:g}"
    global_point = _global_spectrum_at_q(result, q_value)

    spectrum_path = out_dir / f"mother_weighted_spectrum_q{q_label}.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    if result.q.size >= 2:
        order = np.argsort(result.alpha)
        ax.plot(
            result.alpha[order],
            result.f_alpha[order],
            "-",
            linewidth=1.8,
            color="#1f4f72",
            label="Global spectrum (OLS)",
        )
    if global_point is not None:
        ax.scatter(
            [global_point[0]],
            [global_point[1]],
            s=110,
            color="#1f4f72",
            edgecolors="white",
            linewidths=0.8,
            zorder=4,
            label=f"Global q={q_label}",
        )
    scatter = ax.scatter(
        alpha_w,
        f_alpha_w,
        c=zeta_mean,
        s=28 + 40 * (measure_sum / np.nanmax(measure_sum) if np.nanmax(measure_sum) > 0 else 1),
        cmap="plasma",
        alpha=0.75,
        edgecolors="none",
        label="Mother cells (weighted)",
    )
    ax.set_title(f"Local Weighted Spectrum (q={q_label})")
    ax.set_xlabel("alpha_w")
    ax.set_ylabel("f(alpha)_w")
    ax.grid(alpha=0.3)
    cbar = fig.colorbar(scatter, ax=ax)
    cbar.set_label("zeta_mean")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(spectrum_path, dpi=160)
    plt.close(fig)
    written["mother_weighted_spectrum"] = str(spectrum_path)

    spatial_alpha_path = out_dir / f"mother_spatial_alpha_w_q{q_label}.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    points = ax.scatter(cx, cy, c=alpha_w, s=34, cmap="viridis", alpha=0.85, edgecolors="none")
    ax.set_title(f"Mother Cells: alpha_w (q={q_label})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(points, ax=ax)
    cbar.set_label("alpha_w")
    fig.tight_layout()
    fig.savefig(spatial_alpha_path, dpi=160)
    plt.close(fig)
    written["mother_spatial_alpha_w"] = str(spatial_alpha_path)

    zeta_rows = _unique_mother_zeta_rows(rows)
    zeta_x = np.array([_to_float(r["mother_centroid_x"]) for r in zeta_rows], dtype=float)
    zeta_y = np.array([_to_float(r["mother_centroid_y"]) for r in zeta_rows], dtype=float)
    zeta_vals = np.array([_to_float(r["zeta_mean"]) for r in zeta_rows], dtype=float)

    spatial_zeta_path = out_dir / "mother_spatial_zeta.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    points = ax.scatter(zeta_x, zeta_y, c=zeta_vals, s=34, cmap="cividis", alpha=0.85, edgecolors="none")
    ax.set_title("Mother Cells: zeta Mean Reliability")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(points, ax=ax)
    cbar.set_label("zeta_mean")
    fig.tight_layout()
    fig.savefig(spatial_zeta_path, dpi=160)
    plt.close(fig)
    written["mother_spatial_zeta"] = str(spatial_zeta_path)

    compare_path = out_dir / f"mother_ols_vs_weighted_q{q_label}.png"
    fig, ax = plt.subplots(figsize=(6.8, 6.2))
    ax.scatter(alpha_ols, alpha_w, c=zeta_mean, cmap="plasma", s=42, alpha=0.8, edgecolors="none")
    finite_alpha = np.concatenate([alpha_ols, alpha_w])
    finite_alpha = finite_alpha[np.isfinite(finite_alpha)]
    if finite_alpha.size:
        lo = float(np.min(finite_alpha))
        hi = float(np.max(finite_alpha))
        pad = 0.05 * (hi - lo if hi > lo else 1.0)
        ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "--", color="#444444", linewidth=1.2, label="y = x")
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
    ax.set_title(f"OLS vs Weighted alpha (q={q_label})")
    ax.set_xlabel("alpha (OLS)")
    ax.set_ylabel("alpha_w (weighted)")
    ax.grid(alpha=0.3)
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(compare_path, dpi=160)
    plt.close(fig)
    written["mother_ols_vs_weighted"] = str(compare_path)

    if plot_all_q:
        for q_item in available_q:
            q_item = float(q_item)
            if np.isclose(q_item, q_value):
                continue
            extra_rows = _mother_rows_for_q(rows, q_item)
            if min_zeta > 0:
                extra_rows = [
                    r for r in extra_rows if _to_float(r.get("zeta_mean", "nan")) >= min_zeta
                ]
            if not extra_rows:
                continue

            extra_label = f"{q_item:g}"
            extra_alpha_w = np.array([_to_float(r["alpha_w"]) for r in extra_rows], dtype=float)
            extra_f_alpha_w = np.array([_to_float(r["f_alpha_w"]) for r in extra_rows], dtype=float)
            extra_alpha_ols = np.array([_to_float(r["alpha"]) for r in extra_rows], dtype=float)
            extra_zeta = np.array([_to_float(r["zeta_mean"]) for r in extra_rows], dtype=float)
            extra_measure = np.array([_to_float(r["measure_sum_m"]) for r in extra_rows], dtype=float)
            extra_cx = np.array([_to_float(r["mother_centroid_x"]) for r in extra_rows], dtype=float)
            extra_cy = np.array([_to_float(r["mother_centroid_y"]) for r in extra_rows], dtype=float)
            extra_global_point = _global_spectrum_at_q(result, q_item)

            extra_spectrum_path = out_dir / f"mother_weighted_spectrum_q{extra_label}.png"
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            if result.q.size >= 2:
                order = np.argsort(result.alpha)
                ax.plot(
                    result.alpha[order],
                    result.f_alpha[order],
                    "-",
                    linewidth=1.8,
                    color="#1f4f72",
                    label="Global spectrum (OLS)",
                )
            if extra_global_point is not None:
                ax.scatter(
                    [extra_global_point[0]],
                    [extra_global_point[1]],
                    s=110,
                    color="#1f4f72",
                    edgecolors="white",
                    linewidths=0.8,
                    zorder=4,
                    label=f"Global q={extra_label}",
                )
            extra_size = 28 + 40 * (
                extra_measure / np.nanmax(extra_measure) if np.nanmax(extra_measure) > 0 else 1
            )
            scatter = ax.scatter(
                extra_alpha_w,
                extra_f_alpha_w,
                c=extra_zeta,
                s=extra_size,
                cmap="plasma",
                alpha=0.75,
                edgecolors="none",
                label="Mother cells (weighted)",
            )
            ax.set_title(f"Local Weighted Spectrum (q={extra_label})")
            ax.set_xlabel("alpha_w")
            ax.set_ylabel("f(alpha)_w")
            ax.grid(alpha=0.3)
            cbar = fig.colorbar(scatter, ax=ax)
            cbar.set_label("zeta_mean")
            ax.legend(loc="best")
            fig.tight_layout()
            fig.savefig(extra_spectrum_path, dpi=160)
            plt.close(fig)
            written[f"mother_weighted_spectrum_q{extra_label}"] = str(extra_spectrum_path)

            extra_spatial_alpha_path = out_dir / f"mother_spatial_alpha_w_q{extra_label}.png"
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            points = ax.scatter(
                extra_cx,
                extra_cy,
                c=extra_alpha_w,
                s=34,
                cmap="viridis",
                alpha=0.85,
                edgecolors="none",
            )
            ax.set_title(f"Mother Cells: alpha_w (q={extra_label})")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_aspect("equal", adjustable="box")
            ax.grid(alpha=0.25)
            cbar = fig.colorbar(points, ax=ax)
            cbar.set_label("alpha_w")
            fig.tight_layout()
            fig.savefig(extra_spatial_alpha_path, dpi=160)
            plt.close(fig)
            written[f"mother_spatial_alpha_w_q{extra_label}"] = str(extra_spatial_alpha_path)

            extra_compare_path = out_dir / f"mother_ols_vs_weighted_q{extra_label}.png"
            fig, ax = plt.subplots(figsize=(6.8, 6.2))
            ax.scatter(
                extra_alpha_ols,
                extra_alpha_w,
                c=extra_zeta,
                cmap="plasma",
                s=42,
                alpha=0.8,
                edgecolors="none",
            )
            finite_extra_alpha = np.concatenate([extra_alpha_ols, extra_alpha_w])
            finite_extra_alpha = finite_extra_alpha[np.isfinite(finite_extra_alpha)]
            if finite_extra_alpha.size:
                lo = float(np.min(finite_extra_alpha))
                hi = float(np.max(finite_extra_alpha))
                pad = 0.05 * (hi - lo if hi > lo else 1.0)
                ax.plot(
                    [lo - pad, hi + pad],
                    [lo - pad, hi + pad],
                    "--",
                    color="#444444",
                    linewidth=1.2,
                    label="y = x",
                )
                ax.set_xlim(lo - pad, hi + pad)
                ax.set_ylim(lo - pad, hi + pad)
            ax.set_title(f"OLS vs Weighted alpha (q={extra_label})")
            ax.set_xlabel("alpha (OLS)")
            ax.set_ylabel("alpha_w (weighted)")
            ax.grid(alpha=0.3)
            ax.set_aspect("equal", adjustable="box")
            ax.legend(loc="best")
            fig.tight_layout()
            fig.savefig(extra_compare_path, dpi=160)
            plt.close(fig)
            written[f"mother_ols_vs_weighted_q{extra_label}"] = str(extra_compare_path)

    hist_path = out_dir / "mother_zeta_histogram.png"
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.hist(zeta_vals, bins=min(30, max(10, zeta_vals.size // 20)), color="#5b8fa8", edgecolor="white")
    ax.set_title("Distribution of zeta_mean Across Mother Cells")
    ax.set_xlabel("zeta_mean")
    ax.set_ylabel("Count")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(hist_path, dpi=160)
    plt.close(fig)
    written["mother_zeta_histogram"] = str(hist_path)

    envelope_path = out_dir / "mother_local_spectrum_envelope.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    all_alpha_w: list[float] = []
    all_f_alpha_w: list[float] = []
    all_q: list[float] = []
    for row in rows:
        aw = _to_float(row.get("alpha_w", "nan"))
        fw = _to_float(row.get("f_alpha_w", "nan"))
        qv = _to_float(row.get("q", "nan"))
        if np.isfinite(aw) and np.isfinite(fw) and np.isfinite(qv):
            all_alpha_w.append(aw)
            all_f_alpha_w.append(fw)
            all_q.append(qv)
    if all_alpha_w:
        ax.scatter(
            all_alpha_w,
            all_f_alpha_w,
            c=all_q,
            s=24,
            cmap="coolwarm",
            alpha=0.35,
            edgecolors="none",
            label="Mother cells (all q)",
        )
    if result.q.size >= 2:
        order = np.argsort(result.alpha)
        ax.plot(
            result.alpha[order],
            result.f_alpha[order],
            "o-",
            linewidth=2.0,
            color="#1f4f72",
            label="Global spectrum (OLS)",
        )
    for q_item in available_q:
        subset = _mother_rows_for_q(rows, float(q_item))
        if len(subset) < 5:
            continue
        alphas = np.array([_to_float(r["alpha_w"]) for r in subset], dtype=float)
        fs = np.array([_to_float(r["f_alpha_w"]) for r in subset], dtype=float)
        ax.scatter(
            [float(np.median(alphas))],
            [float(np.median(fs))],
            s=70,
            marker="D",
            color="black",
            zorder=5,
        )
    ax.set_title("Global Spectrum vs Local Weighted Cloud")
    ax.set_xlabel("alpha")
    ax.set_ylabel("f(alpha)")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(envelope_path, dpi=160)
    plt.close(fig)
    written["mother_local_spectrum_envelope"] = str(envelope_path)

    measure_path = out_dir / "mother_spatial_measure_sum_m.png"
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    measure_rows = _unique_mother_zeta_rows(rows)
    mx = np.array([_to_float(r["mother_centroid_x"]) for r in measure_rows], dtype=float)
    my = np.array([_to_float(r["mother_centroid_y"]) for r in measure_rows], dtype=float)
    mm = np.array([_to_float(r["measure_sum_m"]) for r in measure_rows], dtype=float)
    points = ax.scatter(mx, my, c=mm, s=34, cmap="YlOrRd", alpha=0.85, edgecolors="none")
    ax.set_title("Mother Cells: Structural Intensity (measure_sum_m)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.25)
    cbar = fig.colorbar(points, ax=ax)
    cbar.set_label("measure_sum_m")
    fig.tight_layout()
    fig.savefig(measure_path, dpi=160)
    plt.close(fig)
    written["mother_spatial_measure_sum_m"] = str(measure_path)

    structural_path = out_dir / "lineament_mother_structural_stats.csv"
    structural_rows = _read_mother_agg_rows(structural_path)
    if structural_rows:
        sx = np.array([_to_float(r["mother_centroid_x"]) for r in structural_rows], dtype=float)
        sy = np.array([_to_float(r["mother_centroid_y"]) for r in structural_rows], dtype=float)
        density = np.array([_to_float(r["density_m_per_km2"]) for r in structural_rows], dtype=float)
        finite_density = np.isfinite(sx) & np.isfinite(sy) & np.isfinite(density)
        if np.any(finite_density):
            density_path = out_dir / "mother_spatial_density.png"
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            points = ax.scatter(
                sx[finite_density],
                sy[finite_density],
                c=density[finite_density],
                s=34,
                cmap="YlGnBu",
                alpha=0.85,
                edgecolors="none",
            )
            ax.set_title("Mother Cells: Lineament Density")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_aspect("equal", adjustable="box")
            ax.grid(alpha=0.25)
            cbar = fig.colorbar(points, ax=ax)
            cbar.set_label("density_m_per_km2")
            fig.tight_layout()
            fig.savefig(density_path, dpi=160)
            plt.close(fig)
            written["mother_spatial_density"] = str(density_path)

        azimuth = np.array([_to_float(r["dominant_azimuth_deg"]) for r in structural_rows], dtype=float)
        finite_azimuth = np.isfinite(sx) & np.isfinite(sy) & np.isfinite(azimuth)
        if np.any(finite_azimuth):
            azimuth_path = out_dir / "mother_spatial_dominant_azimuth.png"
            fig, ax = plt.subplots(figsize=(8.5, 5.2))
            points = ax.scatter(
                sx[finite_azimuth],
                sy[finite_azimuth],
                c=azimuth[finite_azimuth],
                s=34,
                cmap="twilight",
                alpha=0.85,
                edgecolors="none",
                vmin=0,
                vmax=180,
            )
            ax.set_title("Mother Cells: Dominant Axial Azimuth")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_aspect("equal", adjustable="box")
            ax.grid(alpha=0.25)
            cbar = fig.colorbar(points, ax=ax)
            cbar.set_label("dominant_azimuth_deg")
            fig.tight_layout()
            fig.savefig(azimuth_path, dpi=160)
            plt.close(fig)
            written["mother_spatial_dominant_azimuth"] = str(azimuth_path)

    return written
