"""Add a geometry-declared overlapping interior grid; preserve quarter-grid QA.

Circular author observation domains have pi/4 coverage in bounding-box quarters,
just below the fixed 0.8 threshold. Keep those reports, and add four windows
centered at 3/8 and 5/8 of each axis, with unchanged half-short-side size.
No fitting result chooses centers or changes coverage/fit thresholds.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
import numpy as np
from shapely.geometry import box

from musa import MUSA
from musa.scaling import ScalingOptions, assess_lineament_scaling, write_scaling_reports
from extended_benchmark_inputs import sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output
    catalog = json.loads((root / "input_catalog.json").read_text())
    summary = json.loads((root / "summary.json").read_text())
    by_name = {r["dataset_id"]: r for r in summary["cases"]}
    for case in catalog["cases"]:
        if not case["georeferenced"]:
            continue
        started = time.monotonic()
        folder = root / "results" / case["dataset_id"]
        path = folder / "scaling_support.json"
        original = json.loads(path.read_text())
        if any(r.get("window_grid") == "interior_overlap" for r in original["supports"]):
            print("ALREADY EXTENDED", case["dataset_id"], flush=True)
            continue
        shutil.copy2(path, folder / "quarter_grid_scaling_support.json")
        frame = gpd.read_file(case["input"], layer="lineaments")
        boundary = gpd.read_file(case["input"], layer="boundary").geometry.union_all()
        model = MUSA.from_line_geometries(frame.geometry.tolist(), boundary, case["crs"], q_values=np.arange(-4., 4.1))
        reports = original["supports"]
        for report in reports[1:]:
            report["window_grid"] = "bounding_box_quarters"
        x0, y0, x1, y1 = boundary.bounds
        side = min(x1-x0, y1-y0)/2
        for index, (fx, fy) in enumerate(((.375, .375), (.625, .375), (.375, .625), (.625, .625)), 4):
            x, y = x0+fx*(x1-x0), y0+fy*(y1-y0)
            rectangle = box(x-side/2, y-side/2, x+side/2, y+side/2)
            support = rectangle.intersection(boundary)
            if support.area <= 0:
                continue
            report = assess_lineament_scaling(model, case["scales"], ScalingOptions(case["resolution"]),
                support_id=f"interior_window_{index}", boundary=support, nominal_area=rectangle.area)
            report.update(center_id=index, center_x=x, center_y=y, window_m=side, coordinate_units="metres",
                          window_grid="interior_overlap", dependence="overlapping supports; not independent replicates")
            reports.append(report)
        outputs = write_scaling_reports(folder, reports)
        rows = []
        for report in reports[1:]:
            x, y, half = report["center_x"], report["center_y"], report["window_m"]/2
            support = box(x-half, y-half, x+half, y+half).intersection(boundary)
            for row in report["q_results"]:
                rows.append(dict(support_id=report["support_id"], window_grid=report["window_grid"],
                                 q=row["q"], status=row["status"], dq=row["dimension"], tau=row.get("tau"),
                                 alpha=row.get("alpha"), f_alpha=row.get("f_alpha"), coverage=report["coverage"],
                                 reasons="; ".join(row["reasons"]), geometry=support))
        frame = gpd.GeoDataFrame(rows, crs=case["crs"])
        gpkg = folder / "window_results.gpkg"
        for layer, subset in (("all_q", frame), ("q0", frame[frame.q == 0]), ("q2", frame[frame.q == 2])):
            subset.to_file(gpkg, layer=layer, driver="GPKG")
        with sqlite3.connect(gpkg) as connection:
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            connection.execute("PRAGMA journal_mode=DELETE")
        manifest_path = folder / "run_manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["outputs"].update(outputs)
        manifest["windows"] = len(reports)-1
        manifest["interior_window_follow_up"] = dict(rule="geometry-only centers at 3/8 and 5/8; half-short-side size; thresholds unchanged",
            status_counts=dict(Counter(row["status"] for report in reports if report.get("window_grid") == "interior_overlap" for row in report["q_results"])),
            baseline="quarter_grid_scaling_support.json", seconds=time.monotonic()-started)
        manifest["files"] = {path.name: sha256(path) for path in folder.iterdir() if path.is_file() and path != manifest_path}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        by_name[case["dataset_id"]]["windows"] = manifest["windows"]
        print("INTERIOR", case["dataset_id"], manifest["interior_window_follow_up"]["status_counts"], flush=True)
    (root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
