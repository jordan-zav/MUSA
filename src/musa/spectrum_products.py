"""Indexed spectra and descriptive peaks shared by Python, Processing and QGIS."""
from __future__ import annotations

import csv
from contextlib import closing
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import uuid

import numpy as np

from .control import check_cancelled
from .spectrum import fit_quadratic_spectrum

OBSERVABLES = ("dq", "tau", "alpha", "f_alpha")
IDENTITY_TOLERANCE = 1e-7


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def _true(value):
    return str(value).lower() in ("true", "1", "1.0")


def identity_diagnostics(q, dq, tau, alpha, f_alpha):
    values = {name: _number(value) for name, value in zip(OBSERVABLES, (dq, tau, alpha, f_alpha))}
    errors = {}
    if values["tau"] is not None and values["dq"] is not None:
        errors["tau_from_dq"] = abs(values["tau"] - (q - 1) * values["dq"])
    if all(values[name] is not None for name in ("tau", "alpha", "f_alpha")):
        errors["legendre_identity"] = abs(values["f_alpha"] - q * values["alpha"] + values["tau"])
    if np.isclose(q, 0, rtol=0, atol=1e-12) and values["f_alpha"] is not None and values["dq"] is not None:
        errors["f0_equals_d0"] = abs(values["f_alpha"] - values["dq"])
    if np.isclose(q, 1, rtol=0, atol=1e-12):
        if values["tau"] is not None:
            errors["tau1_equals_zero"] = abs(values["tau"])
        if values["alpha"] is not None and values["f_alpha"] is not None:
            errors["f1_equals_alpha1"] = abs(values["f_alpha"] - values["alpha"])
    maximum = max(errors.values()) if errors else None
    return {"status": "not_evaluated" if maximum is None else "consistent" if maximum <= IDENTITY_TOLERANCE else "discrepancy",
            "max_error": maximum, "absolute_tolerance": IDENTITY_TOLERANCE, "errors": errors}


def _point(q, values, accepted, reason, statuses=None):
    point = {"q": float(q), **{name: _number(values.get(name)) for name in OBSERVABLES},
             "accepted": bool(accepted), "reason": str(reason), "statuses": statuses or {}}
    point["identities"] = identity_diagnostics(point["q"], *(point[name] for name in OBSERVABLES))
    return point


def summarize_spectrum(points):
    """Keep q=0, sampled maxima/ties and a descriptive quadratic peak separate."""
    points = sorted(points, key=lambda p: p["q"])
    usable = [p for p in points if p["accepted"] and all(p[n] is not None for n in OBSERVABLES)
              and p["identities"]["status"] == "consistent"]
    zero = next((p for p in points if np.isclose(p["q"], 0, rtol=0, atol=1e-12)), None)
    summary = {"requested_q_count": len(points), "valid_q_count": len(usable),
               "alpha_q0": zero["alpha"] if zero is not None and zero in usable else None,
               "alpha_q0_status": "supported" if zero is not None and zero in usable else "q0_not_evaluated" if zero is None else "q0_not_supported",
               "observed_peak_alpha": None, "observed_peak_f": None, "observed_peak_qs": [],
               "observed_peak_alphas": [], "observed_peak_tied": False, "observed_peak_at_q_edge": None,
               "fit_peak_alpha": None, "fit_peak_f": None, "fit_status": "too_few_valid_q",
               "peak_fit_r2": None, "delta_alpha": None, "fit_coefficients": None,
               "identity_status": "discrepancy" if any(p["identities"]["status"] == "discrepancy" for p in points) else "consistent" if usable else "not_evaluated",
               "identity_max_error": max((p["identities"]["max_error"] for p in points if p["identities"]["max_error"] is not None), default=None)}
    if not usable:
        return summary
    alpha = np.array([p["alpha"] for p in usable])
    f = np.array([p["f_alpha"] for p in usable])
    ties = [p for p in usable if np.isclose(p["f_alpha"], max(f), rtol=1e-9, atol=1e-10)]
    summary.update(observed_peak_f=float(max(f)), observed_peak_qs=[p["q"] for p in ties],
                   observed_peak_alphas=[p["alpha"] for p in ties], observed_peak_tied=len(ties) > 1,
                   observed_peak_alpha=ties[0]["alpha"] if len({p["alpha"] for p in ties}) == 1 else None,
                   observed_peak_at_q_edge=any(p is usable[0] or p is usable[-1] for p in ties),
                   delta_alpha=float(np.ptp(alpha)))
    if len(usable) < 3:
        return summary
    fit = fit_quadratic_spectrum(alpha, f)
    if not fit["points_count"]:
        summary["fit_status"] = "degenerate_alpha_or_rank"
    elif fit["fit_valid"]:
        summary.update(fit_peak_alpha=float(fit["alpha_peak"]), fit_peak_f=float(fit["f_peak"]),
                       fit_status="interpolation_only" if len(usable) == 3 else "descriptive_fit",
                       peak_fit_r2=_number(fit["quadratic_r2"]),
                       fit_coefficients=[float(fit[n]) for n in ("quadratic_a", "quadratic_b", "quadratic_c")])
    else:
        summary["fit_status"] = "nonconcave_constant_or_vertex_outside_range"
    return summary


def _global_series(result, requested_q):
    accepted = {float(q): i for i, q in enumerate(result.q)}
    points = []
    for q in requested_q:
        index = accepted.get(float(q))
        values = {name: getattr(result, name)[index] for name in OBSERVABLES} if index is not None else {}
        points.append(_point(q, values, index is not None, "accepted" if index is not None else "legacy_fit_rejected"))
    yield {"source": "analysis", "support_id": "global", "kind": "global", "estimator": "canonical",
           "support_basis": "legacy_fit", "points": points}


def _moving_series(path, cancelled):
    # Stream groups from the existing center/size/q ordered export; no whole CSV
    # or geometry table is loaded into a QGIS UI process.
    current, group = None, []
    with Path(path).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            check_cancelled(cancelled)
            key = (int(row["center_id"]), float(row["window_m"]))
            if current is not None and key != current:
                yield from _moving_group(group)
                group = []
            current = key
            group.append(row)
        if group:
            yield from _moving_group(group)


def _moving_group(group):
    first = group[0]
    center_id, size = int(first["center_id"]), float(first["window_m"])
    for estimator, suffix in (("canonical", ""), ("zeta", "_w")):
        points = []
        for row in group:
            q = float(row["q"])
            values = {name: row.get(name + suffix) for name in OBSERVABLES}
            points.append(_point(q, values, _true(row["accepted" + suffix]), row["reason" + suffix]))
        yield {"source": "analysis", "support_id": f"window_{center_id}_{size:g}m", "kind": "window",
               "center_id": center_id, "center_x": float(first["center_x"]), "center_y": float(first["center_y"]),
               "window_m": size, "estimator": estimator, "support_basis": "legacy_fit_and_effective_boxes",
               "points": points}


def _assessment_series(reports):
    for report in reports:
        points = []
        for row in report["q_results"]:
            statuses = {name: row.get("observables", {}).get(name, {}).get("status", "insufficient_information")
                        for name in ("tau", "alpha", "f_alpha")}
            statuses["dq"] = row["status"]
            accepted = all(status in ("compatible_finite_range", "identity") for status in statuses.values())
            values = {"dq": row["dimension"], **{name: row.get(name) for name in ("tau", "alpha", "f_alpha")}}
            points.append(_point(row["q"], values, accepted, ";".join(row["reasons"]), statuses))
        yield {"source": "assessment", "support_id": report["support_id"],
               "kind": "window" if "window_m" in report else "global", "estimator": "canonical",
               **{k: report.get(k) for k in ("center_id", "center_x", "center_y", "window_m")},
               "support_basis": "fixed_range_diagnostics", "points": points}


def write_spectrum_products(output_dir, *, result=None, requested_q=(), moving_csv=None,
                            assessments=None, source="analysis", cancelled=None):
    """Replace only one source in an indexed cache, preserving the other source.

    A run owns its newly reserved output folder. Stage the SQLite cache before
    publishing it so a failed rebuild retains its previous complete version.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / "spectrum_curves.sqlite"
    staged = out / ("spectrum_curves_" + uuid.uuid4().hex + ".partial.sqlite")
    if target.exists():
        shutil.copyfile(target, staged)
    with closing(sqlite3.connect(staged)) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS spectra (
                series_id TEXT PRIMARY KEY, source TEXT NOT NULL, kind TEXT NOT NULL,
                support_id TEXT NOT NULL, center_id INTEGER, window_m REAL, estimator TEXT NOT NULL,
                metadata_json TEXT NOT NULL, summary_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS spectra_selector ON spectra(source, kind, center_id, window_m, estimator);
            CREATE TABLE IF NOT EXISTS points (
                series_id TEXT NOT NULL REFERENCES spectra(series_id) ON DELETE CASCADE,
                q REAL NOT NULL, point_json TEXT NOT NULL, PRIMARY KEY(series_id, q));
            PRAGMA user_version=1;
        """)
        with db:
            db.execute("DELETE FROM spectra WHERE source=?", (source,))
            def series():
                if source == "assessment":
                    yield from _assessment_series(assessments or [])
                else:
                    if result is not None:
                        yield from _global_series(result, requested_q)
                    if moving_csv is not None:
                        yield from _moving_series(moving_csv, cancelled)
            for item in series():
                check_cancelled(cancelled)
                points = item.pop("points")
                key = f"{item['source']}|{item['support_id']}|{item['estimator']}"
                summary = summarize_spectrum(points)
                db.execute("INSERT INTO spectra VALUES (?,?,?,?,?,?,?,?,?)",
                           (key, item["source"], item["kind"], item["support_id"], item.get("center_id"),
                            item.get("window_m"), item["estimator"], json.dumps(item, allow_nan=False),
                            json.dumps(summary, allow_nan=False)))
                db.executemany("INSERT INTO points VALUES (?,?,?)",
                               [(key, p["q"], json.dumps(p, allow_nan=False)) for p in points])
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Spectrum cache integrity check failed.")
    check_cancelled(cancelled)
    os.replace(staged, target)
    summary_path = out / "spectrum_summary.csv"
    columns = ["source", "support_id", "center_id", "center_x", "center_y", "window_m", "estimator", "support_basis"]
    summary_columns = list(summarize_spectrum([]))
    with _read_db(target) as db, summary_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns + summary_columns)
        writer.writeheader()
        for metadata, summary in db.execute("SELECT metadata_json,summary_json FROM spectra ORDER BY source,kind,center_id,window_m,estimator"):
            check_cancelled(cancelled)
            row = {key: json.loads(metadata).get(key) for key in columns}
            row.update(json.loads(summary))
            writer.writerow({key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in row.items()})
    return {"spectrum_curves": str(target), "spectrum_summary": str(summary_path)}


def _read_db(path):
    # URI read-only mode prevents a missing/wrong path from creating a new DB.
    return closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True))


def export_spectrum_summary_gpkg(summary_csv, geopackage):
    """Register a nonspatial summary table without changing vector layers."""
    with Path(summary_csv).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    numeric = {"center_id", "center_x", "center_y", "window_m", "requested_q_count", "valid_q_count",
               "alpha_q0", "observed_peak_alpha", "observed_peak_f", "fit_peak_alpha", "fit_peak_f",
               "peak_fit_r2", "delta_alpha", "identity_max_error"}
    # Field names are our fixed CSV schema, never SQL supplied by a layer/user.
    if not fields or any(not name.replace("_", "").isalnum() for name in fields):
        raise ValueError("Unexpected spectrum summary fields.")
    definitions = ",".join('"' + name + '" ' + ("REAL" if name in numeric else "TEXT") for name in fields)
    with closing(sqlite3.connect(geopackage)) as db, db:
        db.execute(f'CREATE TABLE IF NOT EXISTS window_spectrum_summary (fid INTEGER PRIMARY KEY AUTOINCREMENT,{definitions})')
        db.execute("DELETE FROM window_spectrum_summary")
        placeholders = ",".join("?" for _ in fields)
        names = ",".join('"' + name + '"' for name in fields)
        db.executemany(f"INSERT INTO window_spectrum_summary ({names}) VALUES ({placeholders})",
                       [tuple(_number(row[name]) if name in numeric else row[name] for name in fields) for row in rows])
        db.execute("""INSERT OR REPLACE INTO gpkg_contents
            (table_name,data_type,identifier,description,last_change,srs_id)
            VALUES ('window_spectrum_summary','attributes','window_spectrum_summary',
            'Descriptive spectrum summaries; source and estimator are explicit',
            strftime('%Y-%m-%dT%H:%M:%fZ','now'),NULL)""")


def list_spectra(path):
    with _read_db(path) as db:
        return [{"series_id": row[0], **json.loads(row[1])}
                for row in db.execute("SELECT series_id,metadata_json FROM spectra ORDER BY source,kind,center_id,window_m,estimator")]


def read_spectrum(path, series_id):
    with _read_db(path) as db:
        row = db.execute("SELECT metadata_json,summary_json FROM spectra WHERE series_id=?", (series_id,)).fetchone()
        if row is None:
            raise KeyError("Spectrum is not available in this run.")
        points = [json.loads(value[0]) for value in db.execute(
            "SELECT point_json FROM points WHERE series_id=? ORDER BY q", (series_id,))]
        return {**json.loads(row[0]), "summary": json.loads(row[1]), "points": points}


def spectrum_figure(spectrum):
    """No pyplot/backend switch; connect only consecutive supported q points."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure = Figure(figsize=(10, 7), constrained_layout=True)
    FigureCanvasAgg(figure)
    axes = figure.subplots(2, 2).ravel()
    points = sorted(spectrum["points"], key=lambda p: p["q"])
    for ax, (name, label) in zip(axes[:3], (("dq", r"$D_q$"), ("tau", r"$\tau(q)$"), ("alpha", r"$\alpha(q)$"))):
        q = np.array([p["q"] for p in points])
        values = np.array([np.nan if p[name] is None else p[name] for p in points])
        accepted = np.array([p["accepted"] for p in points], bool)
        ax.plot(q, np.where(accepted, values, np.nan), "o-", color="#166c91")
        ax.scatter(q[~accepted], values[~accepted], marker="x", color="#888888", label="unsupported/rejected")
        ax.set(xlabel="q", ylabel=label)
        ax.grid(alpha=.2)
    ax = axes[3]
    alpha = np.array([np.nan if p["alpha"] is None else p["alpha"] for p in points])
    f = np.array([np.nan if p["f_alpha"] is None else p["f_alpha"] for p in points])
    accepted = np.array([p["accepted"] for p in points], bool)
    q = np.array([p["q"] for p in points])
    ax.plot(np.where(accepted, alpha, np.nan), np.where(accepted, f, np.nan), color="#166c91", alpha=.7)
    good = accepted & np.isfinite(alpha) & np.isfinite(f)
    if good.any():
        scatter = ax.scatter(alpha[good], f[good], c=q[good], cmap="coolwarm", zorder=3)
        figure.colorbar(scatter, ax=ax, label="q")
    ax.scatter(alpha[~accepted], f[~accepted], color="#888888", marker="x")
    summary = spectrum["summary"]
    if summary["fit_coefficients"] is not None and good.any():
        x = np.linspace(min(alpha[good]), max(alpha[good]), 100)
        ax.plot(x, np.polyval(summary["fit_coefficients"], x), "--", color="#a46623", label="descriptive quadratic fit")
        ax.legend(fontsize=7)
    ax.set(xlabel=r"$\alpha$", ylabel=r"$f(\alpha)$")
    ax.grid(alpha=.2)
    figure.suptitle(f"{spectrum['support_id']} | {spectrum['source']} | {spectrum['estimator']}\n"
                   f"{spectrum['support_basis'].replace('_', ' ')} | descriptive peaks; not proof of multifractality", fontsize=10)
    return figure
