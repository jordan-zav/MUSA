"""Generate synthetic inputs and run the independent MUSA 1.2.0 assessment.

Run from a source checkout: python examples/scaling_tutorial.py --output NEW_DIR
Coordinates are unlocated model meters, not observations from a real site.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.geometry import LineString, box

# Use this checkout even when another MUSA version is installed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from musa import MUSA, ScalingOptions, __version__, assess_lineament_scaling, write_scaling_reports  # noqa: E402
from musa.workflow import RunConfig  # noqa: E402


def definition():
    """Return a fixed line, domain, CRS, and scales declared before fitting."""
    crs = CRS.from_proj4("+proj=eqc +R=6371000 +units=m +no_defs +type=crs").to_wkt().replace(
        'PROJCRS["unknown"', 'PROJCRS["MUSA synthetic UNLOCATED tutorial"', 1)
    return [LineString([(1000, 1500), (9000, 6500)])], box(0, 0, 10000, 10000), crs, np.geomspace(10, 1000, 16)


def summarize(report):
    """Select portable numerical fields; exclude filenames and timestamps."""
    return {
        "software_version": __version__,
        "q_results": [{k: row.get(k) for k in ("q", "status", "dimension", "tau", "reasons")}
                      for row in report["q_results"]],
        "used_scales_m": report["used_scales_m"],
        "null": {k: report["null"].get(k) for k in (
            "status", "p_value", "p_holm", "minimum_p", "tail", "replicates_requested",
            "observed", "reject_relocation_at_0_05", "holm_family_size")},
        "valid_null_replicates": len(report["null"]["values"]),
    }


def compare_summary(actual, expected):
    """Check documented outcomes and numerical values with an explicit tolerance."""
    def compare(a, b, location):
        if isinstance(b, dict):
            if set(a) != set(b):
                raise AssertionError("Fields differ: " + location)
            for key in b:
                compare(a[key], b[key], location + "." + key)
        elif isinstance(b, list):
            if len(a) != len(b):
                raise AssertionError("Lengths differ: " + location)
            for i, (first, second) in enumerate(zip(a, b)):
                compare(first, second, location + "." + str(i))
        elif isinstance(b, float):
            if not np.isclose(a, b, rtol=0, atol=1e-10):
                raise AssertionError("Numerical difference: " + location)
        elif a != b:
            raise AssertionError("Value differs: " + location)
    compare(actual, expected, "summary")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output folder; must not exist")
    parser.add_argument("--prepare-only", action="store_true", help="Write inputs and configuration without fitting")
    parser.add_argument("--check", action="store_true", help="Compare with the committed numerical reference")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    lines, domain, crs, scales = definition()
    options = ScalingOptions(
        resolution_m=1, null_replicates=999, seed=42,
        renyi_order_policy="inform_q0_q2", null_tail="two_sided",
        coarse_trim_min_effective_q2=4)
    options.validate()
    dataset = args.output / "inputs.gpkg"
    gpd.GeoDataFrame({"trace_id": [1]}, geometry=lines, crs=crs).to_file(dataset, layer="lineaments", driver="GPKG")
    gpd.GeoDataFrame({"domain_id": [1]}, geometry=[domain], crs=crs).to_file(dataset, layer="boundary", driver="GPKG")
    (args.output / "crs.wkt").write_text(crs, encoding="utf-8")
    geometry = {"lines": [list(line.coords) for line in lines], "boundary_wkt": domain.wkt, "crs": crs}
    protocol = {
        "kind": "synthetic; no real-world location", "q_values": [0, 1, 2],
        "requested_scales_m": scales.tolist(), "options": asdict(options),
        "geometry_sha256": hashlib.sha256(json.dumps(geometry, sort_keys=True).encode()).hexdigest(),
        "input_file_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "processing": {"SCALES": ",".join(repr(float(v)) for v in scales), "RESOLUTION": 1,
                       "Q_MIN": 0, "Q_MAX": 2, "Q_STEP": 1, "NULL_REPLICATES": 999,
                       "RENYI_ORDER_POLICY": 1, "NULL_TAIL": 1, "COARSE_TRIM": 4, "SEED": 42},
    }
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    config = RunConfig(q_min=0, q_max=2, q_step=1, scaling_support=True, scaling_resolution_m=1,
                       scaling_scales_m=tuple(scales), scaling_null_replicates=999,
                       renyi_order_policy="inform_q0_q2", scaling_null_tail="two_sided",
                       scaling_coarse_trim_min_effective_q2=4, seed=42)
    (args.output / "recipe.json").write_text(json.dumps(config.recipe(), indent=2), encoding="utf-8")
    if args.prepare_only:
        print("Inputs prepared; no assessment requested.")
        return
    analyzer = MUSA.from_line_geometries(lines, domain, crs, q_values=[0, 1, 2])
    report = assess_lineament_scaling(analyzer, scales, options, support_id="global")
    write_scaling_reports(args.output / "assessment", [report])
    summary = summarize(report)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if args.check:
        reference = Path(__file__).with_name("scaling_tutorial_expected.json")
        compare_summary(summary, json.loads(reference.read_text(encoding="utf-8")))
        print("Documented numerical reference: PASS (absolute tolerance 1e-10).")


if __name__ == "__main__":
    main()
