"""Build auditable controls/author-map derivatives and run the actual MUSA core.

Raw author files stay in Shared; derivatives, reports and QGIS inputs are written
to a new external session directory. This is not geological validation.
"""
import argparse
from dataclasses import asdict
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
import numpy as np
from PIL import Image
from pyproj import CRS
from shapely.geometry import LineString, box
from shapely.ops import unary_union
from musa import MUSA
from musa.network import _iter_line_parts
from musa.scaling import ScalingOptions, assess_lineament_scaling, write_scaling_reports
from musa.spectrum_products import write_spectrum_products, list_spectra, read_spectrum, spectrum_figure

SIDE = 10000.0
QS = np.array([-2., -1., 0., 1., 2.])
CRS_WKT = CRS.from_proj4("+proj=eqc +R=6371000 +units=m +no_defs +type=crs").to_wkt().replace(
    'PROJCRS["unknown"', 'PROJCRS["MUSA UNLOCATED normalized benchmark plane"', 1)


def cantor(p, levels=7):
    lines = []
    for bits in itertools.product((0, 1), repeat=levels):
        start = SIDE * sum(2 * b * 3. ** (-k - 1) for k, b in enumerate(bits))
        length = SIDE * 3. ** (-levels) * np.prod([p if b == 0 else 1 - p for b in bits]) / max(p, 1 - p) ** levels
        center = start + SIDE * 3. ** (-levels) / 2
        lines.append(LineString([(center - length / 2, SIDE / 2), (center + length / 2, SIDE / 2)]))
    return lines


def roy_lattice(level):
    """Independent implementation of b=2,n=1, upper-left unfractured blocks."""
    cells, lines = [(0., 0., SIDE)], []
    for _ in range(level + 1):
        following = []
        for x, y, length in cells:
            half = length / 2
            lines += [LineString([(x + half, y), (x + half, y + length)]),
                      LineString([(x, y + half), (x + length, y + half)])]
            following += [(x, y, half), (x + half, y, half), (x + half, y + half, half)]
        cells = following
    return lines


def binary_runs(values):
    changes = np.diff(np.pad(np.asarray(values, dtype=np.int8), (1, 1)))
    return zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1))


def bitmap_centerlines(path, threshold=128):
    """Axis-aligned connected pixel-center runs, not invented author vectors."""
    pixels = np.asarray(Image.open(path).convert("L"))
    ink = pixels < threshold
    height, width = ink.shape
    covered = np.zeros_like(ink)
    factor = SIDE / max(width, height)
    lines = []
    for y in range(height):
        for start, end in binary_runs(ink[y]):
            if end - start >= 2:
                lines.append(LineString([((start + .5) * factor, (height - y - .5) * factor),
                                         ((end - .5) * factor, (height - y - .5) * factor)]))
                covered[y, start:end] = True
    for x in range(width):
        for start, end in binary_runs(ink[:, x]):
            if end - start >= 2:
                lines.append(LineString([((x + .5) * factor, (height - start - .5) * factor),
                                         ((x + .5) * factor, (height - end + .5) * factor)]))
                covered[start:end, x] = True
    metadata = {"source_pixels": [width, height], "threshold": threshold, "model_units_per_pixel": factor,
                "grayscale_values": np.unique(pixels).tolist(),
                "black_pixels": int(ink.sum()), "unrepresented_black_pixels": int((ink & ~covered).sum()),
                "method": "horizontal/vertical black-pixel runs of at least two pixels; pixel-center endpoints; no snapping"}
    return lines, box(0, 0, width * factor, height * factor), metadata, ink


def raster_capacity(ink, lower, upper):
    if lower > upper:
        return {"dimension": None, "pixel_sizes": [], "occupied_boxes": [], "reason": "no_interval_above_finite_size_cutoff"}
    scales = np.unique(np.rint(np.geomspace(max(1, lower), upper, 12)).astype(int)) if lower < upper else np.array([int(round(upper))])
    counts = []
    for scale in scales:
        h, w = ink.shape
        padded = np.pad(ink, ((0, (-h) % scale), (0, (-w) % scale)))
        counts.append(int(padded.reshape(padded.shape[0] // scale, scale, padded.shape[1] // scale, scale).any(axis=(1, 3)).sum()))
    dimension = float(np.polyfit(np.log(1 / scales), np.log(counts), 1)[0]) if len(scales) >= 2 else None
    return {"method": "independent binary-raster occupied boxes; origin at image corner; no length weights",
            "pixel_sizes": scales.tolist(), "occupied_boxes": counts, "dimension": dimension,
            "comparable_interval_only": True}


def expected_cantor(q, p):
    tau = -np.log(p ** q + (1 - p) ** q) / np.log(3)
    dq = -sum(v * np.log(v) for v in (p, 1 - p)) / np.log(3) if q == 1 else tau / (q - 1)
    weights = np.array([p, 1 - p]) ** q
    weights /= weights.sum()
    alpha = -float(weights @ np.log([p, 1 - p])) / np.log(3)
    return dict(dq=float(dq), tau=float(tau), alpha=alpha, f_alpha=float(q * alpha - tau))


def prepare_cases(raw_root):
    cases = [dict(id="uniform_line", lines=[LineString([(0, SIDE / 2), (SIDE, SIDE / 2)])],
                  domain=box(0, 0, SIDE, SIDE), resolution=1., lower=5., upper=80.,
                  source="local analytic control", expected={float(q): dict(dq=1., tau=float(q - 1), alpha=1., f_alpha=1.) for q in QS})]
    for p in (.5, .7):
        cases.append(dict(id="cantor_uniform" if p == .5 else "cantor_binomial", lines=cantor(p),
                          domain=box(0, 0, SIDE, SIDE), resolution=.01, lower=50., upper=1000.,
                          source="local finite Cantor approximation", p=p, levels=7,
                          expected={float(q): expected_cantor(q, p) for q in QS}))
    for level in (4, 6, 8):
        cases.append(dict(id=f"roy_reconstruction_{level}", lines=roy_lattice(level), domain=box(0, 0, SIDE, SIDE),
                          resolution=.01, lower=SIDE / 2 ** level, upper=SIDE / 4, level=level,
                          source="local reimplementation of Roy 2007 / Sahu and Roy 2020 construction; not an author vector file",
                          expected_d0=float(np.log(3) / np.log(2))))
    paths = sorted((raw_root / "sahu_roy_2020/original").rglob("*.bmp"), key=lambda p: int(p.stem))
    if len(paths) != 8:
        raise ValueError("Download the complete eight-map Sahu/Roy supplement first.")
    for path in paths:
        level = int(path.stem)
        lines, domain, metadata, ink = bitmap_centerlines(path)
        lower_pixels = max(4., ink.shape[1] / 2 ** level)
        reference = raster_capacity(ink, lower_pixels, ink.shape[1] / 4)
        factor = metadata["model_units_per_pixel"]
        cases.append(dict(id=f"sahu_roy_author_map_{level}", lines=lines, domain=domain,
                          resolution=4 * factor, lower=lower_pixels * factor, upper=min(domain.bounds[2:]) / 4,
                          source="vector derivative of original author bitmap; no original vector coordinates supplied",
                          source_path=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          level=level, vectorization=metadata, raster_capacity=reference,
                          expected_d0=float(np.log(3) / np.log(2))))
        if level >= 6:
            for threshold in (64, 192):
                other, domain, metadata, alternative_ink = bitmap_centerlines(path, threshold=threshold)
                cases.append(dict(id=f"sahu_roy_author_map_{level}_threshold_{threshold}", lines=other, domain=domain,
                                  resolution=4 * factor, lower=lower_pixels * factor, upper=min(domain.bounds[2:]) / 4,
                                  source="predeclared threshold sensitivity of author bitmap", source_path=str(path),
                                  source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), level=level,
                                  vectorization=metadata, raster_capacity=raster_capacity(alternative_ink, lower_pixels, alternative_ink.shape[1] / 4),
                                  expected_d0=float(np.log(3) / np.log(2))))
    return cases


def run_case(case, out, windows):
    started = time.perf_counter()
    folder = out / "results" / case["id"]
    folder.mkdir(parents=True, exist_ok=False)
    boundary = case["domain"]
    raw_length = sum(line.length for line in case["lines"])
    lines = list(_iter_line_parts(unary_union(case["lines"])))
    analyzer = MUSA.from_line_geometries(lines, boundary, CRS_WKT, q_values=QS)
    # A zero/short theoretical interval is retained as insufficient information,
    # not expanded below the published finite-size cutoff to obtain a good fit.
    lower, upper = case["lower"], case["upper"]
    scales = np.geomspace(lower, upper, 12) if lower < upper else np.array([lower])
    options = ScalingOptions(case["resolution"], seed=20261102)
    report = assess_lineament_scaling(analyzer, scales, options)
    reports = [report]
    if windows:
        for index, (x, y) in enumerate(((SIDE / 4, SIDE / 4), (3 * SIDE / 4, SIDE / 4),
                                      (SIDE / 4, 3 * SIDE / 4), (3 * SIDE / 4, 3 * SIDE / 4))):
            support = box(x - SIDE / 4, y - SIDE / 4, x + SIDE / 4, y + SIDE / 4).intersection(boundary)
            if support.is_empty:
                continue
            r = assess_lineament_scaling(analyzer, scales, options, support_id=f"window_{index}_5000m",
                                         boundary=support, nominal_area=(SIDE / 2) ** 2)
            r.update(center_id=index, center_x=x, center_y=y, window_m=SIDE / 2)
            reports.append(r)
    outputs = write_scaling_reports(folder, reports)
    legacy = {"status": "not_run"}
    if len(scales) >= 3:
        try:
            result = analyzer.run_analysis(resolutions_m=scales, min_r2=.9, cell_length_threshold_m=0)
            legacy = {"status": "complete", "accepted_q": result.accepted_count, "rejected_q": result.rejected_count}
            outputs["analysis_report"] = MUSA.export_analysis_report(folder, result)
            outputs.update(write_spectrum_products(folder, result=result, requested_q=QS))
        except ValueError as error:
            legacy = {"status": "rejected", "reason": str(error)}
    differences = []
    for row in report["q_results"]:
        expected = case.get("expected", {}).get(row["q"], {})
        values = {"dq": row["dimension"], **{name: row.get(name) for name in ("tau", "alpha", "f_alpha")}}
        differences.append({"q": row["q"], "status": row["status"], "reasons": row["reasons"],
                            "estimated": values, "expected": expected,
                            "errors": {key: values[key] - target if values[key] is not None else None for key, target in expected.items()}})
    rows0 = next((r for r in report["q_results"] if r["q"] == 0), {})
    expected_d0 = case.get("expected_d0")
    meta = {key: value for key, value in case.items() if key not in ("lines", "domain")}
    meta.update(raw_features=len(case["lines"]), unique_noded_parts=len(lines), raw_length=raw_length,
                unique_length=sum(line.length for line in lines), options=asdict(options), scales_m=scales.tolist(),
                normalized_coordinate_frame="UNLOCATED model plane; values are not real-world metres/georeferenced outcrops")
    manifest = {"format": "musa-author-benchmark", "version": 1, "status": "complete", "source": meta,
                "outputs": outputs, "legacy_analysis": legacy, "comparison": differences,
                "d0_theory": expected_d0, "d0_estimated": rows0.get("dimension"),
                "d0_error": rows0["dimension"] - expected_d0 if rows0.get("dimension") is not None and expected_d0 is not None else None,
                "seconds": time.perf_counter() - started}
    for item in list_spectra(folder / "spectrum_curves.sqlite"):
        if item["support_id"] == "global" and item["source"] == "assessment":
            figure = spectrum_figure(read_spectrum(folder / "spectrum_curves.sqlite", item["series_id"]))
            figure.savefig(folder / "global_spectrum.png", dpi=140)
            figure.clear()
    manifest["files"] = {file.name: hashlib.sha256(file.read_bytes()).hexdigest() for file in folder.iterdir() if file.is_file()}
    (folder / "run_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    return manifest, lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=Path("D:/DevResources/Shared/MUSA-benchmarks"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = prepare_cases(args.raw_root)
    geometries, domains, summaries = [], [], []
    for index, case in enumerate(cases):
        print(f"CASE {index + 1}/{len(cases)} {case['id']} ({len(case['lines'])} traces)", flush=True)
        manifest, lines = run_case(case, args.output, windows=True)
        summaries.append({"dataset_id": case["id"], "kind": case["source"], "level": case.get("level"),
                          "features": len(lines), "d0_estimated": manifest["d0_estimated"], "d0_theory": manifest["d0_theory"],
                          "d0_error": manifest["d0_error"], "legacy_status": manifest["legacy_analysis"]["status"],
                          "d0_status": manifest["comparison"][2]["status"], "seconds": manifest["seconds"]})
        geometries.extend({"dataset_id": case["id"], "part_id": i, "georeferenced": 0, "geometry": line} for i, line in enumerate(lines))
        domains.append({"dataset_id": case["id"], "georeferenced": 0, "geometry": case["domain"]})
        (args.output / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
        print("RESULT", summaries[-1], flush=True)
    inputs = args.output / "datasets"
    inputs.mkdir()
    gpd.GeoDataFrame(geometries, crs=CRS_WKT).to_file(inputs / "benchmarks.gpkg", layer="lineaments", driver="GPKG")
    gpd.GeoDataFrame(domains, crs=CRS_WKT).to_file(inputs / "benchmarks.gpkg", layer="boundaries", driver="GPKG")
    import pandas as pd
    pd.DataFrame(summaries).to_csv(args.output / "summary.csv", index=False)
    unresolved = {"doi": "10.4121/14464893", "status": "not_analyzed_no_verified_archive",
                  "metadata": str(args.raw_root / "zhu_2022_v2/metadata_figshare.json"),
                  "reason": "4TU and public Figshare file endpoints returned timeout/502/504; no author coordinates downloaded",
                  "license_from_metadata": "CC BY-NC 4.0"}
    (args.output / "zhu_status.json").write_text(json.dumps(unresolved, indent=2), encoding="utf-8")
    print("COMPLETE", args.output, flush=True)


if __name__ == "__main__":
    main()
