"""Run declared public-data cases, retaining all rejections and failed cases."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
import numpy as np
from PIL import Image
from scipy.special import logsumexp
from shapely.geometry import box

from musa import MUSA
from musa.scaling import ScalingOptions, assess_lineament_scaling, holm_adjust, write_scaling_reports
from musa.spectrum_products import list_spectra, read_spectrum, spectrum_figure, write_spectrum_products
from extended_benchmark_inputs import RAW, sha256


def independent_mask_counts(mask, scales):
    """Binary occupied-box count at corner origin, intentionally no length measure."""
    pixels_y, pixels_x = np.nonzero(mask)
    sizes, counts = [], []
    for scale in np.unique(np.maximum(1, np.rint(scales).astype(int))):
        cells = np.column_stack([pixels_x//scale, pixels_y//scale])
        sizes.append(int(scale))
        counts.append(int(len(np.unique(cells, axis=0))))
    slope = float(np.polyfit(np.log(1/np.array(sizes)), np.log(counts), 1)[0]) if min(counts, default=0) > 0 and len(counts) >= 3 else None
    return dict(estimator="binary mask box count, corner origin; finite descriptive slope, not acceptance assessment",
                scales_pixels=sizes, occupied_boxes=counts, d0_slope=slope)


def exact_cascade_validation(output):
    """Dyadic 2D cascade: compare aggregated masses with independent closed forms."""
    from musa.scaling import renyi_entropy
    weights = np.array([[.1, .2], [.3, .4]])
    measure = np.ones((1, 1))
    levels = []
    for level in range(1, 9):
        measure = np.kron(measure, weights)
        levels.append(measure.ravel())
    x = np.arange(1, 9)*np.log(2.)
    rows = []
    for q in np.arange(-4., 4.1):
        logw = np.log(weights.ravel())
        logmu = q*logw-logsumexp(q*logw)
        escort = np.exp(logmu)
        tau = -float(logsumexp(q*logw))/np.log(2.) if q != 1 else 0.
        expected = dict(dq=-float(weights.ravel()@logw)/np.log(2.) if q == 1 else tau/(q-1),
                        tau=tau, alpha=-float(escort@logw)/np.log(2.), f_alpha=-float(escort@logmu)/np.log(2.))
        observables = {name: [] for name in expected}
        for masses in levels:
            logp = np.log(masses)
            logu = q*logp-logsumexp(q*logp)
            u = np.exp(logu)
            observables["dq"].append(renyi_entropy(masses, q))
            observables["tau"].append(0. if q == 1 else -float(logsumexp(q*logp)))
            observables["alpha"].append(-float(u@logp))
            observables["f_alpha"].append(-float(u@logu))
        estimated = {name: float(np.polyfit(x, y, 1)[0]) for name, y in observables.items()}
        errors = {name: estimated[name]-value for name, value in expected.items()}
        rows.append(dict(q=float(q), expected=expected, estimated=estimated, errors=errors))
    maximum = max(abs(value) for row in rows for value in row["errors"].values())
    result = dict(type="exact mass cascade algebra check; not geometric line-network validation", weights=weights.tolist(),
                  levels=8, q_results=rows, max_absolute_error=float(maximum), passed=bool(maximum < 1e-10))
    assert result["passed"]
    (output / "exact_cascade_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def geometric_cascade_validation(output, levels=8):
    """Check the actual line-partition/CJ core against a dyadic exact cascade.

    Dyadic weights and coordinates avoid tiny-endpoint subtraction noise.
    This is an aligned-grid finite-interval check, not origin robustness.
    """
    from shapely.geometry import LineString
    from musa.scaling import _curves
    from extended_benchmark_inputs import CRS_WKT
    weights = np.array([[.125, .125], [.25, .5]])
    mass = np.ones((1, 1))
    for _ in range(levels):
        mass = np.kron(mass, weights)
    side = mass.shape[0]
    lengths = mass / mass.max() / (8*side)
    lines = []
    for y, x in np.ndindex(mass.shape):
        cx, cy = (x+.5)/side, (y+.5)/side
        lines.append(LineString([(cx-lengths[y, x]/2, cy), (cx+lengths[y, x]/2, cy)]))
    domain = box(0, 0, 1, 1)
    qs = np.arange(-4., 4.1)
    model = MUSA.from_line_geometries(lines, domain, CRS_WKT, q_values=qs)
    scales = 2. ** (-np.arange(1, levels+1))
    entropies, _, features = _curves(lines, domain, scales, qs, np.array([[0., 0.]]), singularities=True)
    x = np.log(1/scales)
    rows = []
    for index, q in enumerate(qs):
        logw = np.log(weights.ravel())
        logmu = q*logw-logsumexp(q*logw)
        escort = np.exp(logmu)
        tau = -float(logsumexp(q*logw))/np.log(2.) if q != 1 else 0.
        target = dict(dq=-float(weights.ravel()@logw)/np.log(2.) if q == 1 else tau/(q-1),
                      tau=tau, alpha=-float(escort@logw)/np.log(2.), f_alpha=-float(escort@logmu)/np.log(2.))
        actual = dict(dq=float(np.polyfit(x, entropies[0, index], 1)[0]),
                      **{name: float(np.polyfit(x, values[0, index], 1)[0]) for name, values in features.items()})
        rows.append(dict(q=float(q), target=target, actual=actual,
                         errors={name: actual[name]-value for name, value in target.items()}))
    maximum = float(max(abs(value) for row in rows for value in row["errors"].values()))
    result = dict(weights=weights.tolist(), levels=levels, line_features=len(lines), q_results=rows,
                  max_absolute_error=maximum, passed=maximum < 1e-9,
                  core_checked="actual musa.scaling._curves: geometric length partition, Dq entropy, tau, alpha and f(alpha)",
                  scope="one aligned origin; finite declared dyadic scales; no claim of four-origin acceptance or geological validation",
                  model_total_length=sum(line.length for line in model._line_geometries))
    assert result["passed"], result
    (output / "geometric_cascade_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_case(case, root, null_replicates=0):
    started = time.monotonic()
    folder = root / "results" / case["dataset_id"]
    if sha256(Path(case["input"])) != case["input_sha256"]:
        raise ValueError("Prepared input changed after its manifest; preserve the run and prepare a new input")
    if (folder / "run_manifest.json").exists():
        existing = json.loads((folder / "run_manifest.json").read_text())
        if (existing["status"] == "complete" and existing["input_sha256"] == case["input_sha256"]
                and existing["input_manifest"] == case
                and existing["options"]["null_replicates"] == null_replicates):
            return existing
        raise ValueError("Existing nonmatching result; preserve it and use a fresh output folder")
    folder.mkdir(parents=True, exist_ok=True)
    frame = gpd.read_file(case["input"], layer="lineaments")
    boundary = gpd.read_file(case["input"], layer="boundary").geometry.union_all()
    qs = np.arange(-4., 4.1)
    model = MUSA.from_line_geometries(frame.geometry.tolist(), boundary, case["crs"], q_values=qs)
    options = ScalingOptions(case["resolution"], null_replicates=null_replicates, seed=20261102)
    report = assess_lineament_scaling(model, case["scales"], options, progress=lambda text: print(case["dataset_id"], text, flush=True))
    report["coordinate_units"] = "metres" if case["georeferenced"] else case["metadata"].get("units", "model units")
    report["null_trace_unit"] = "curated unique noded line part; not necessarily original fracture identity"
    reports = [report]
    x0, y0, x1, y1 = boundary.bounds
    window_side = min(x1-x0, y1-y0)/2
    windows = []
    for index, (fx, fy) in enumerate(((.25, .25), (.75, .25), (.25, .75), (.75, .75))):
        x, y = x0+fx*(x1-x0), y0+fy*(y1-y0)
        rectangle = box(x-window_side/2, y-window_side/2, x+window_side/2, y+window_side/2)
        support = rectangle.intersection(boundary)
        if support.area <= 0:
            continue
        local = assess_lineament_scaling(model, case["scales"], ScalingOptions(case["resolution"]),
                                        support_id=f"window_{index}", boundary=support, nominal_area=rectangle.area)
        local.update(center_id=index, center_x=x, center_y=y, window_m=window_side,
                     coordinate_units=report["coordinate_units"])
        reports.append(local)
        for row in local["q_results"]:
            windows.append(dict(support_id=local["support_id"], q=row["q"], status=row["status"],
                                dq=row["dimension"], tau=row.get("tau"), alpha=row.get("alpha"), f_alpha=row.get("f_alpha"),
                                coverage=local["coverage"], reasons="; ".join(row["reasons"]), geometry=support))
    outputs = write_scaling_reports(folder, reports)
    legacy = dict(status="not_run_insufficient_scales")
    if len(case["scales"]) >= 3:
        try:
            result = model.run_analysis(resolutions_m=case["scales"], min_r2=.9, cell_length_threshold_m=0)
            outputs["analysis_report"] = MUSA.export_analysis_report(folder, result)
            outputs.update(write_spectrum_products(folder, result=result, requested_q=qs))
            legacy = dict(status="complete", accepted_q=result.accepted_count, rejected_q=result.rejected_count)
        except ValueError as error:
            legacy = dict(status="rejected", reason=str(error))
    gpkg = folder / "window_results.gpkg"
    if windows:
        window_frame = gpd.GeoDataFrame(windows, crs=case["crs"])
        window_frame.to_file(gpkg, layer="all_q", driver="GPKG")
        window_frame[window_frame.q == 0].to_file(gpkg, layer="q0", driver="GPKG")
        window_frame[window_frame.q == 2].to_file(gpkg, layer="q2", driver="GPKG")
        import sqlite3
        with sqlite3.connect(gpkg) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("PRAGMA journal_mode=DELETE")
    comparisons = []
    for row in report["q_results"]:
        expected = case.get("expected", {}).get(str(row["q"]), {})
        estimated = dict(dq=row["dimension"], tau=row.get("tau"), alpha=row.get("alpha"), f_alpha=row.get("f_alpha"))
        comparisons.append(dict(q=row["q"], expected=expected, estimated=estimated, status=row["status"], reasons=row["reasons"],
                                errors={name: estimated[name]-value if estimated[name] is not None else None for name, value in expected.items()}))
    independent = None
    if case["source"] == "fraxet_selected":
        pixels = np.asarray(Image.open(RAW / "fraxet_selected/original" / case["metadata"]["member"]))
        independent = independent_mask_counts(pixels > case["metadata"]["threshold"], case["scales"])
    for item in list_spectra(folder / "spectrum_curves.sqlite"):
        if item["support_id"] == "global" and item["source"] == "assessment":
            figure = spectrum_figure(read_spectrum(folder / "spectrum_curves.sqlite", item["series_id"]))
            figure.savefig(folder / "global_spectrum.png", dpi=150)
            figure.clear()
    q0 = next(row for row in report["q_results"] if row["q"] == 0)
    result = dict(format="musa-extended-benchmark", version=1, status="complete", dataset_id=case["dataset_id"],
                  source=case["source"], input_sha256=case["input_sha256"], input_manifest=case,
                  outputs=outputs, legacy_analysis=legacy, options=asdict(options),
                  global_q0=dict(d0=q0["dimension"], status=q0["status"], reasons=q0["reasons"]),
                  global_status_counts=dict(Counter(r["status"] for r in report["q_results"])),
                  windows=len(reports)-1, null=report["null"], comparison=comparisons,
                  independent_mask_counts=independent, seconds=time.monotonic()-started)
    result["files"] = {path.name: sha256(path) for path in folder.iterdir() if path.is_file()}
    (folder / "run_manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output
    catalog = json.loads((root / "input_catalog.json").read_text())
    exact_cascade_validation(root)
    geometric_cascade_validation(root)
    # The null subset is declared by source/count before any scaling fits.
    natural = sorted((c for c in catalog["cases"] if c["georeferenced"]), key=lambda c: (c["unique_parts"], c["dataset_id"]))[:1]
    selected = {c["dataset_id"] for c in natural} | {"control_cantor_binomial_7", "hatchfrac_growth_2"}
    selected &= {c["dataset_id"] for c in catalog["cases"]}
    (root / "declared_null_subset.json").write_text(json.dumps(dict(cases=sorted(selected), replicates=99,
        selection="one natural case with the fewest unique parts, finite Cantor level 7 and earliest author growth snapshot; before fitting",
        trace_unit="unique noded part; no claim of preserving original fracture identity", family_scope="selected global tests; untestable cases retained as p=1 for Holm"), indent=2), encoding="utf-8")
    summaries, results, failures = [], [], []
    for index, case in enumerate(catalog["cases"]):
        print("CASE", index+1, len(catalog["cases"]), case["dataset_id"], flush=True)
        try:
            result = run_case(case, root, 99 if case["dataset_id"] in selected else 0)
            results.append(result)
            summaries.append(dict(dataset_id=case["dataset_id"], source=case["source"], parts=case["unique_parts"],
                                  georeferenced=case["georeferenced"], **result["global_q0"],
                                  global_counts=result["global_status_counts"], windows=result["windows"], seconds=result["seconds"]))
            print("RESULT", summaries[-1], flush=True)
        except Exception as error:
            failure = dict(dataset_id=case["dataset_id"], error=type(error).__name__ + ": " + str(error))
            failures.append(failure)
            print("FAILED", failure, flush=True)
        (root / "summary.json").write_text(json.dumps(dict(cases=summaries, failures=failures), indent=2), encoding="utf-8")
    null_cases = [r for r in results if r["dataset_id"] in selected]
    by_name = {r["dataset_id"]: r for r in null_cases}
    tests = [dict(dataset_id=name, **by_name[name]["null"]) if name in by_name else dict(dataset_id=name, p_value=None, status="analysis_failed") for name in sorted(selected)]
    corrected = holm_adjust([r["p_value"] if r["p_value"] is not None else 1. for r in tests])
    for row, p in zip(tests, corrected):
        row.update(p_holm_extended_global_family=p if row["p_value"] is not None else None,
                   extended_family_size=len(selected), reject_extended_family_0_05=bool(row["p_value"] is not None and p <= .05))
    (root / "conditional_null_results.json").write_text(json.dumps(tests, indent=2), encoding="utf-8")
    print("COMPLETE", root, "cases", len(results), "failures", failures, flush=True)


if __name__ == "__main__":
    main()
