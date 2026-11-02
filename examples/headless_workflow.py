"""Run the shared workflow without QGIS on a synthetic line in an unlocated plane.

This is a repository example, not an installed MUSA command-line interface.
The output must be a new directory. Coordinates are synthetic model metres;
the custom CRS deliberately carries no real survey location.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pyproj import CRS
from shapely.geometry import LineString, box

from musa import MUSA
from musa.workflow import RunConfig, execute_analysis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    crs = CRS.from_proj4("+proj=eqc +R=6371000 +units=m +no_defs +type=crs").to_wkt().replace(
        'PROJCRS["unknown"', 'PROJCRS["MUSA synthetic UNLOCATED demo"', 1)
    analyzer = MUSA.from_line_geometries(
        [LineString([(0, 5000), (10000, 5000)])], box(0, 0, 10000, 10000), crs, q_values=[0, 1, 2])
    config = RunConfig(
        mother_cell_m=4000, divisors=(2, 4, 8, 16), q_min=0, q_max=2,
        threshold_m=0, local=True, structural=False, network=False, plots=True, gis=True,
        scaling_support=True, scaling_resolution_m=1,
        scaling_scales_m=(5, 8, 13, 20, 32, 50, 80, 125, 200, 315, 500, 800, 1250, 2000))
    recipe = RunConfig.from_recipe(config.recipe())
    manifest = execute_analysis(analyzer, recipe, args.output,
        source_info={"kind": "synthetic demo", "crs": crs, "units": "synthetic model metres; no real-world geolocation"},
        progress=lambda percent, message: print(f"{percent:3g}% {message}", flush=True))
    print("Completed:", args.output / "run_manifest.json")
    print("Accepted q:", manifest["accepted_q"], "Rejected q:", manifest["rejected_q"])


if __name__ == "__main__":
    main()
