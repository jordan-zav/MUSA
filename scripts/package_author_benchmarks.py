"""Add source attribution, honest comparisons, plots and window layers to a run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import zipfile

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import box

from run_author_benchmarks import CRS_WKT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--raw-root", type=Path, default=Path(os.environ.get("MUSA_BENCHMARK_DATA", Path(__file__).resolve().parents[1] / "data/benchmarks")))
    args = parser.parse_args()
    root = args.output
    summaries = json.loads((root / "summary.json").read_text())
    assert len(summaries) == 20
    rows, comparisons = [], []
    for case in summaries:
        folder = root / "results" / case["dataset_id"]
        manifest = json.loads((folder / "run_manifest.json").read_text())
        for item in manifest["comparison"]:
            comparisons.append({"dataset_id": case["dataset_id"], **item})
        supports = json.loads((folder / "scaling_support.json").read_text())["supports"]
        for support in supports:
            if "center_x" not in support:
                continue
            x, y, half = support["center_x"], support["center_y"], support["window_m"] / 2
            for q in support["q_results"]:
                rows.append(dict(dataset_id=case["dataset_id"], support_id=support["support_id"], q=q["q"],
                                 status=q["status"], dq=q["dimension"], tau=q.get("tau"), alpha=q.get("alpha"),
                                 f_alpha=q.get("f_alpha"), reasons="; ".join(q["reasons"]), georeferenced=0,
                                 geometry=box(x-half, y-half, x+half, y+half)))
    gpd.GeoDataFrame(rows, crs=CRS_WKT).to_file(root / "datasets/benchmarks.gpkg", layer="window_results", driver="GPKG")
    with sqlite3.connect(root / "datasets/benchmarks.gpkg") as connection:
        for table in ("lineaments", "boundaries", "window_results"):
            connection.execute(f'CREATE INDEX IF NOT EXISTS "idx_{table}_dataset" ON "{table}" (dataset_id)')
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    # Physical per-case layers avoid stacking unrelated normalized domains and
    # make the project independent of provider-specific subset SQL behavior.
    cases_dir = root / "datasets/cases"
    cases_dir.mkdir(exist_ok=True)
    for layer in ("lineaments", "boundaries", "window_results"):
        frame = gpd.read_file(root / "datasets/benchmarks.gpkg", layer=layer)
        for identity, group in frame.groupby("dataset_id"):
            path = cases_dir / (identity + ".gpkg")
            group.to_file(path, layer=layer, driver="GPKG")
            if layer == "window_results":
                group[group.q == 0].to_file(path, layer="windows_q0", driver="GPKG")
    for path in cases_dir.glob("*.gpkg"):
        with sqlite3.connect(path) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("PRAGMA journal_mode=DELETE")
    (root / "analytic_comparisons.json").write_text(json.dumps(comparisons, indent=2, allow_nan=False), encoding="utf-8")
    originals = root / "originals"
    originals.mkdir(exist_ok=True)
    shutil.copy2(args.raw_root / "sahu_roy_2020/supplement.zip", originals / "sahu_roy_2020_supplement.zip")
    shutil.copy2(args.raw_root / "zhu_2022_v2/metadata_figshare.json", originals / "zhu_metadata_only.json")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    selected = [row for row in summaries if row["dataset_id"] in [f"sahu_roy_author_map_{n}" for n in range(1, 9)]]
    axes[0].axhline(1.5849625007211563, color="#d66b20", ls="--", label="Theoretical limiting D0")
    axes[0].plot([r["level"] for r in selected], [r["d0_estimated"] for r in selected], "o-", label="MUSA / image derivative")
    axes[0].set(xlabel="Author image iteration", ylabel="D0", title="Finite author maps; missing estimates retained")
    axes[0].legend()
    colors = {"dq": "#166a9b", "tau": "#8855aa", "alpha": "#be6335", "f_alpha": "#328058"}
    for key, color in colors.items():
        points = [r for r in comparisons if r["dataset_id"] == "cantor_binomial"]
        axes[1].plot([r["q"] for r in points], [r["errors"].get(key) for r in points], "o-", label=key, color=color)
    axes[1].axhline(0, color="gray", lw=.8)
    axes[1].set(xlabel="q", ylabel="Estimated minus analytic target", title="Finite binomial Cantor: errors are not hidden")
    axes[1].legend()
    fig.savefig(root / "benchmark_comparison.png", dpi=160)
    plt.close(fig)
    table = "\n".join(f"| {r['dataset_id']} | {r['d0_estimated']:.6f} | {r['d0_status']} |" if r['d0_estimated'] is not None else
                      f"| {r['dataset_id']} | unavailable | {r['d0_status']} |" for r in summaries)
    errors = [abs(value) for r in comparisons if r["dataset_id"] == "cantor_binomial" for value in r["errors"].values() if value is not None]
    report = f"""# MUSA: public-author and analytic benchmarks, 2026-11-02

20 cases completed, each with global assessment and four fixed quarter-domain windows. A completed run does not mean every q or window passed. No null simulations were requested in this suite.

## Sources and attribution

Ajay K. Sahu and Ankur Roy (2020), Clustering, Connectivity and Flow Responses of Deterministic Fractal-Fracture Networks, Adv. Geosci. 54, 149–156, [article and CC BY 4.0 notice](https://adgeo.copernicus.org/articles/54/149/2020/). [Original author supplement](https://adgeo.copernicus.org/articles/54/149/2020/adgeo-54-149-2020-supplement.zip). The unchanged supplement ZIP is in originals. Cite the authors when reusing it. Original BMP files are author data; the GeoPackage contains our pixel-center derivatives, not author-supplied vectors. Local Roy lattice reconstructions are separately labelled.

Weiwei Zhu et al., [dataset DOI 10.4121/14464893](https://doi.org/10.4121/14464893), CC BY-NC 4.0 according to the archived public metadata: NOT DOWNLOADED OR ANALYZED. The landing server timed out and the public file endpoints returned 502/504. Only metadata is included. There is no natural-outcrop validation in this delivery.

## Method and limits

The control cases are a uniform line, uniform and binomial finite Cantor line measures, independent Roy reconstructions (iterations 4, 6 and 8), eight author maps, and thresholds 64/192 for author maps 6–8 around the principal threshold 128. Endpoints are pixel centers; no geological interpretation, snapping or gap filling was applied. Coincident multiplicity is removed by explicit geometric union; raw/unique lengths, source hashes, raster counts and thresholds are recorded in each manifest. Raster box counts provide an additional image-based comparison, not an exact independent Dq reference.

All inputs use a labelled UNLOCATED model plane normalized to width 10000. Software field names ending in m are model units here; these are not georeferenced outcrops or real-world metre measurements. Do not overlay them on geographic maps. The theoretical Roy D0 is log(3)/log(2) = 1.584963; no analytic targets are asserted for the other Roy Dq values.

Scales are declared before fitting, bounded by image resolution, the finite construction cutoff and one quarter of domain width; windows apply their own smaller upper bound. The complete interval is assessed with four grid origins. Short intervals stay insufficient instead of being extended to produce a good fit. This is compatibility over a finite interval, not proof of fractality or general calibration.

The binomial Cantor comparison includes Dq, tau, alpha and f(alpha) for q=-2,-1,0,1,2. Maximum absolute error across these outputs is {max(errors):.6f}; negative-q singularity estimates are visibly less accurate. Values and rejected statuses are retained in analytic_comparisons.json. Do not interpret the compatibility flag as a precision guarantee.

| Case | Estimated global D0 | Assessment |
| --- | ---: | --- |
{table}

## Open and reproduce

Open MUSA_author_benchmarks.qgz in QGIS. Groups contain original-source derivatives, independent reconstructions and analytic controls. The initial view shows author map 6; other groups are disabled to avoid stacking unrelated synthetic coordinate planes. Window layers show q=0; all five q values remain in the GeoPackage.

Each results folder contains global/window Dq, tau, alpha, f(alpha), acceptance reasons, JSON/CSV, spectrum SQLite and a global spectrum image. Open that folder with MUSA's completed-run viewer to select individual windows and estimators. Analysis and assessment spectra have distinct sources and may differ.

Repository scripts: fetch_fractal_benchmarks.py, run_author_benchmarks.py, package_author_benchmarks.py, qgis_author_benchmarks.py. Run from the repository root; the QGIS helper is scripts/run_qgis_python.cmd. Inputs and results stay outside the plugin ZIP.
"""
    (root / "README.md").write_text(report, encoding="utf-8")
    (root / "source_hashes.json").write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in originals.iterdir()}, indent=2), encoding="utf-8")
    print("PACKAGED", root, "windows", len(rows), flush=True)


def archive(root):
    """Called after QGIS validation; leave originals and all earlier runs intact."""
    target = root.with_suffix(".zip")
    with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                stream.write(path, path.relative_to(root.parent))
    with zipfile.ZipFile(target) as stream:
        assert stream.testzip() is None
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest + "  " + target.name + "\n", encoding="ascii")
    print("ARCHIVE", target, digest)


if __name__ == "__main__":
    main()
