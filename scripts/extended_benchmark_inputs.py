"""Explicit adapters for public vectors, MATLAB graphs and mask derivatives."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
import numpy as np
from PIL import Image
from pyproj import CRS
from scipy import sparse
from scipy.io import loadmat
from shapely import make_valid
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from musa.network import _iter_line_parts
from run_author_benchmarks import CRS_WKT, cantor, expected_cantor

RAW = Path(os.environ.get("MUSA_BENCHMARK_DATA", Path(__file__).resolve().parents[1] / "data/benchmarks"))


class EmptyObservedNetwork(ValueError):
    """A valid selected source has no nonzero observed lines; no fit applies."""


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thin_mask(mask):
    """Zhang-Suen thinning of a binary mask; preserve isolated pixels for QA."""
    image = np.pad(np.asarray(mask, dtype=bool), 1)
    for _ in range(max(image.shape)):
        changed = False
        for phase in (0, 1):
            p = image[1:-1, 1:-1]
            n = [image[:-2, 1:-1], image[:-2, 2:], image[1:-1, 2:], image[2:, 2:],
                 image[2:, 1:-1], image[2:, :-2], image[1:-1, :-2], image[:-2, :-2]]
            count = sum(v.astype(np.uint8) for v in n)
            transitions = sum((~n[i] & n[(i + 1) % 8]).astype(np.uint8) for i in range(8))
            if phase == 0:
                constraint = ~(n[0] & n[2] & n[4]) & ~(n[2] & n[4] & n[6])
            else:
                constraint = ~(n[0] & n[2] & n[6]) & ~(n[0] & n[4] & n[6])
            remove = p & (count >= 2) & (count <= 6) & (transitions == 1) & constraint
            if remove.any():
                p[remove] = False
                changed = True
        if not changed:
            return image[1:-1, 1:-1].copy()
    raise ValueError("Thinning did not converge")


def skeleton_lines(mask, pixel_size=1., *, already_thin=False):
    skeleton = np.asarray(mask, bool).copy() if already_thin else thin_mask(mask)
    height, width = skeleton.shape
    lines, covered = [], np.zeros_like(skeleton)
    for y, x in np.argwhere(skeleton):
        for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and ny < height and skeleton[ny, nx]):
                continue
            if dx and dy and (skeleton[y, nx] or skeleton[ny, x]):
                continue  # avoid triangular diagonal shortcuts around orthogonal corners
            lines.append(LineString([((x+.5)*pixel_size, (height-y-.5)*pixel_size),
                                     ((nx+.5)*pixel_size, (height-ny-.5)*pixel_size)]))
            covered[y, x] = covered[ny, nx] = True
    qa = dict(foreground_pixels=int(np.asarray(mask, bool).sum()), skeleton_pixels=int(skeleton.sum()),
              isolated_skeleton_pixels=int((skeleton & ~covered).sum()), segments=len(lines),
              method="Zhang-Suen; pixel-center 8-neighbor segments; diagonal shortcuts suppressed; not original author traces",
              pixel_size=pixel_size)
    qa["thinning_applied"] = not already_thin
    return lines, box(0, 0, width*pixel_size, height*pixel_size), qa, skeleton


def load_bristol(path):
    record = loadmat(path)
    xy = np.asarray(record["node_xy"], dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
        raise ValueError("Expected finite node_xy with shape (N,2)")
    adjacency = sparse.csr_matrix(record["node_connectivity"])
    if adjacency.shape != (len(xy), len(xy)) or not np.isin(adjacency.data, [0, 1]).all():
        raise ValueError("Expected binary N by N connectivity")
    edges = sparse.triu(adjacency.maximum(adjacency.T), k=1).tocoo()
    lines = [LineString([xy[i], xy[j]]) for i, j in zip(edges.row, edges.col) if not np.array_equal(xy[i], xy[j])]
    qa = dict(nodes=len(xy), edges=len(lines), asymmetric_entries=(adjacency != adjacency.T).nnz,
              self_loops=int(np.count_nonzero(adjacency.diagonal())), zero_length_edges=int(edges.nnz-len(lines)))
    return lines, qa


def read_fracpaq(path):
    lines = []
    for number, row in enumerate(path.read_text().splitlines(), 1):
        values = np.fromstring(row, sep="\t")
        if not len(values):
            continue
        if len(values) % 2 or not np.isfinite(values).all():
            raise ValueError(f"Invalid coordinate pairs on row {number}")
        coords = values.reshape(-1, 2)
        if len(coords) >= 2 and np.any(coords != coords[0]):
            lines.append(LineString(coords))
    return lines


def metric_frame(path):
    frame = gpd.read_file(path)
    if frame.crs is None:
        raise ValueError(f"Missing author CRS: {path}")
    crs = CRS(frame.crs)
    if not crs.is_projected or crs.axis_info[0].unit_conversion_factor != 1:
        raise ValueError(f"Author data require a declared metric projection: {path}")
    # Loviisa names the same TM35FIN projection without an EPSG authority.
    return frame.to_crs(3067)


def write_case(output, identity, source, lines, boundary, crs, metadata, resolution, georeferenced, expected=None):
    folder = output / "datasets" / identity
    folder.mkdir(parents=True, exist_ok=False)
    invalid_domain = not boundary.is_valid
    if invalid_domain:
        boundary = make_valid(boundary)
    if boundary.is_empty or boundary.area <= 0:
        raise ValueError("Empty observation domain")
    original = list(lines)
    clipped = [part for line in original if line is not None and not line.is_empty
               for part in _iter_line_parts(line.intersection(boundary)) if part.length > 0]
    if not clipped:
        raise EmptyObservedNetwork("No nonzero line geometry in domain")
    # Exact geometric union, no snapping, rounding or gap filling. Record its
    # effect and retain the raw originals in Shared.
    unique = list(_iter_line_parts(unary_union(clipped)))
    unique = [line for line in unique if line.length > 0]
    path = folder / "input.gpkg"
    gpd.GeoDataFrame({"part_id": range(len(unique)), "geometry": unique}, crs=crs).to_file(path, layer="lineaments", driver="GPKG")
    gpd.GeoDataFrame({"dataset_id": [identity], "geometry": [boundary]}, crs=crs).to_file(path, layer="boundary", driver="GPKG")
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        connection.execute("PRAGMA journal_mode=DELETE")
    minx, miny, maxx, maxy = boundary.bounds
    width = min(maxx-minx, maxy-miny)
    lower, upper = max(4*resolution, width/128), width/4
    scales = np.geomspace(lower, upper, 16).tolist() if lower < upper else [lower]
    result = dict(dataset_id=identity, source=source, input=str(path), crs=CRS(crs).to_wkt(),
                  georeferenced=georeferenced, resolution=resolution, scales=scales,
                  scale_rule="16 geometric scales, max(4*operational_resolution,short_side/128) to short_side/4; no fit optimization",
                  original_features=len(original), clipped_parts=len(clipped), unique_parts=len(unique),
                  clipped_length=sum(line.length for line in clipped), unique_length=sum(line.length for line in unique),
                  domain_repaired=invalid_domain, boundary_bounds=list(boundary.bounds), metadata=metadata,
                  expected=expected or {}, input_sha256=sha256(path))
    (folder / "input_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("PREPARED", identity, len(unique), "parts", flush=True)
    return result


def prepare_hornelen(output):
    folder = RAW / "hornelen_sahu_2021/original"
    definitions = [
        ("hornelen_fig8_parent", "page_9_image_1.png", (13, 10, 469, 480), "Fig.8 left, aperture-rendered parent network"),
        ("hornelen_fig8_dominant", "page_9_image_1.png", (504, 10, 966, 480), "Fig.8 right, dominant sub-network; not an independent outcrop"),
        ("hornelen_fig7_map1", "page_9_image_0.png", (1455, 65, 2047, 655), "Fig.7 right, thin-trace Map1; nominal original panel 18m by 18m"),
    ]
    cases = []
    for identity, filename, crop, label in definitions:
        path = folder / filename
        pixels = np.asarray(Image.open(path).convert("RGB"))
        left, top, right, bottom = crop
        region = pixels[top:bottom, left:right]
        red = (region[..., 0] > 110) & (region[..., 1] < 100) & (region[..., 2] < 100)
        mask = (region.mean(axis=2) < 128) & ~red
        if red.any():
            raise ValueError("Chosen inset contains a red annotation; inspect crop before analyzing")
        lines, domain, qa, _ = skeleton_lines(mask)
        cases.append(write_case(output, identity, "hornelen_published_figure", lines, domain, CRS_WKT,
            dict(doi="10.5194/adgeo-56-117-2021", license="CC BY 4.0 article figures, modified from Odling 1997",
                 path=str(path), sha256=sha256(path), figure_label=label, crop_pixel_bounds=list(crop), threshold=128,
                 vectorization=qa, units="figure pixels; inset crop; not original survey vectors or georeferenced metres",
                 resolution_basis="one source figure pixel; lower fit scale >=4 pixels", domain_basis="declared inset avoids frame and labels",
                 comparison_limit="Bour/Roy approximately 1.8 values use different measures/maps/ranges; no exact target assigned"), 1., False))
    return cases


def prepare_inputs(output):
    output.mkdir(parents=True, exist_ok=False)
    cases, failures, not_applicable = [], [], []
    def add(*args, **kwargs):
        try:
            cases.append(write_case(output, *args, **kwargs))
        except EmptyObservedNetwork as error:
            record = dict(dataset_id=args[0], source=args[1], status="not_applicable_empty_observed_network",
                          reason=str(error), metadata=args[5])
            not_applicable.append(record)
            (output / "datasets" / args[0] / "input_manifest.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
            print("NO FIT APPLIES", args[0], flush=True)
        except Exception as error:
            failures.append(dict(dataset_id=args[0], error=type(error).__name__ + ": " + str(error)))
            print("PREPARATION FAILED", args[0], str(error), flush=True)
    aland_root = next((RAW / "aland_zenodo/original").glob("*"))
    areas = sorted((aland_root / "data/trace_data/area").rglob("*.geojson"))
    traces_root = aland_root / "data/trace_data/traces"
    for area_path in areas:
        name = area_path.stem
        area = metric_frame(area_path).geometry.union_all()
        if area_path.parent.name == "20m":
            pieces = name.split("_")
            prefix = "havsvidden_20m_1" if name.startswith("havsvidden") else "_".join(pieces[:3])
            trace_paths = [traces_root / "20m" / (prefix.replace("havsvidden_20m_1", "havsvidden_20m") + "_traces.geojson")]
            resolution = .05  # explicit conservative operational assumption, not a surveyed accuracy
        elif area_path.parent.name == "200000":
            trace_paths = sorted((traces_root / "200000").glob("*.geojson"))
            resolution = 50.
        else:
            trace_paths = list((traces_root / "infinity").glob("*.geojson"))
            resolution = 5.
        for trace_path in trace_paths:
            trace = metric_frame(trace_path)
            identity = "aland_" + name if len(trace_paths) == 1 else "aland_" + trace_path.stem
            if area_path.parent.name == "infinity":
                identity = "aland_" + name
            add(identity, "aland_2023", trace.geometry, area, "EPSG:3067",
                dict(doi="10.5281/zenodo.7919843", article="10.5194/se-14-603-2023",
                     license="other-open in archive metadata; author/GTK ownership in README; local attributed research derivatives",
                     trace_path=str(trace_path), area_path=str(area_path), trace_sha256=sha256(trace_path), area_sha256=sha256(area_path),
                     resolution_basis="operational assumption: 0.05 m for outcrops; cartographic 0.25 mm at stated denominator for lineaments; not measured accuracy"),
                resolution, True)
    loviisa_root = RAW / "loviisa/original"
    trace_paths = [p for p in loviisa_root.rglob("*.shp") if "traces" in str(p).lower()]
    for area_path in sorted(loviisa_root.rglob("*_area.shp")):
        prefix = area_path.stem.removesuffix("_area").lower()
        candidates = [p for p in trace_paths if p.stem.lower().startswith(prefix + "_")]
        if len(candidates) != 1:
            failures.append(dict(dataset_id="loviisa_"+prefix, error=f"Ambiguous source match: {candidates}"))
            continue
        trace_path = candidates[0]
        add("loviisa_"+prefix, "loviisa_2022", metric_frame(trace_path).geometry, metric_frame(area_path).geometry.union_all(),
            "EPSG:3067", dict(doi="10.5281/zenodo.7077846", license="CC BY 4.0", trace_path=str(trace_path),
                             area_path=str(area_path), trace_sha256=sha256(trace_path), area_sha256=sha256(area_path),
                             resolution_basis="0.05 m operational assumption; sensitivity cases supplied separately"), .05, True)
    bristol = RAW / "bristol/original/Bristol_fracture_network.mat"
    if bristol.exists():
        lines, qa = load_bristol(bristol)
        domain = unary_union(lines).envelope
        width = min(domain.bounds[2]-domain.bounds[0], domain.bounds[3]-domain.bounds[1])
        add("bristol_graph", "bristol_2019", lines, domain, CRS_WKT,
            dict(doi="10.13020/ah7v-6n67", license="CC0 1.0", path=str(bristol), sha256=sha256(bristol), graph_qa=qa,
                 domain_basis="INFERRED bounding rectangle, no author observation polygon supplied",
                 units="original MATLAB coordinate units; no verified real-world scale or geolocation",
                 resolution_basis="assumed short_side/1000; sensitivity only, not geological validation"), width/1000, False)
    hatch = RAW / "hatchfrac/original/2DFractureNetworks"
    for file_name in ("fractures", "Backbone"):
        path = hatch / "Fracture_Data" / (file_name+".txt")
        if not path.exists():
            continue
        array = np.loadtxt(path)
        if array.ndim != 2 or array.shape[1] != 4 or not np.isfinite(array).all():
            raise ValueError("Expected author x1,y1,x2,y2 data")
        add("hatchfrac_"+file_name.lower(), "hatchfrac_author", [LineString(row.reshape(2, 2)) for row in array],
            box(0, 0, 100, 100), CRS_WKT,
            dict(doi="10.17632/zhs97tsdry.1", license="CC BY 4.0", path=str(path), sha256=sha256(path),
                 domain_basis="author PlotFracture.m declares L=100 and [0,L] squared", units="author model units",
                 resolution_basis="0.01 model units operational assumption; no analytic fractal target"), .01, False)
    for stage in (2, 7, 13):
        path = hatch / "FractureGrowth_Data" / f"fracture{stage}.txt"
        if not path.exists():
            continue
        array = np.loadtxt(path)
        add(f"hatchfrac_growth_{stage}", "hatchfrac_author", [LineString(row.reshape(2, 2)) for row in array],
            box(0, 0, 10, 10), CRS_WKT,
            dict(doi="10.17632/zhs97tsdry.1", license="CC BY 4.0", path=str(path), sha256=sha256(path), stage=stage,
                 domain_basis="author Check_MakeVideo.m declares [0,10] squared; crossing traces clipped", units="author model units",
                 resolution_basis="0.001 model units operational assumption; no analytic fractal target"), .001, False)
    for name in ("map1_edit_converted", "map7_edit_converted"):
        path = RAW / "fracpaq/original" / (name+".txt")
        lines = read_fracpaq(path)
        domain = unary_union(lines).envelope
        width = min(domain.bounds[2]-domain.bounds[0], domain.bounds[3]-domain.bounds[1])
        add("fracpaq_"+name, "fracpaq_examples", lines, domain, CRS_WKT,
            dict(path=str(path), sha256=sha256(path), software_license="MIT / preserved FracPaQ LICENSE",
                 provenance="author repository sample named map1/map7; Hornelen attribution pending verification; no fixed dimension target",
                 domain_basis="INFERRED bounding rectangle of supplied paths", units="original drawing units; no inferred metres",
                 resolution_basis="short_side/1000 operational assumption"), width/1000, False)
    if (RAW / "hornelen_sahu_2021/provenance.json").exists():
        cases.extend(prepare_hornelen(output))
    provenance = RAW / "fraxet_selected/provenance.json"
    if provenance.exists():
        for item in json.loads(provenance.read_text())["files"]:
            path = Path(item["path"])
            pixels = np.asarray(Image.open(path))
            if pixels.ndim != 2:
                raise ValueError("Expected one-band ground truth mask")
            threshold = .5 if pixels.max() <= 1 else 127.5
            mask = pixels > threshold
            family = item["member"].split("/")[1]
            identity = "fraxet_"+family+"_"+path.stem
            lines, domain, qa, _ = skeleton_lines(mask)
            add(identity, "fraxet_selected", lines, domain, CRS_WKT,
                dict(doi="10.5281/zenodo.17069947", license="CC BY 4.0", member=item["member"], sha256=item["sha256"],
                     vectorization=qa, threshold=threshold, units="pixels; patch coordinate plane; no stitching or georeferencing",
                     resolution_basis="one source pixel; lower fit scale >=4 pixels"), 1., False)
    # Three finite binomial Cantor resolutions and a periodic grid deliberately
    # sampled both above its spacing and across its nonfractal crossover.
    for levels in (5, 7, 9):
        lines = cantor(.7, levels)
        identity = f"control_cantor_binomial_{levels}"
        add(identity, "analytic_control", lines, box(0, 0, 10000, 10000), CRS_WKT,
            dict(p=.7, levels=levels, units="model units", target="limiting weighted Cantor measure, finite approximation"), .01, False,
            {str(q): expected_cantor(q, .7) for q in np.arange(-4., 4.1)})
    coords = np.linspace(0, 10000, 65)
    grid = [LineString([(x, 0), (x, 10000)]) for x in coords] + [LineString([(0, y), (10000, y)]) for y in coords]
    add("control_periodic_grid", "finite_negative_control", grid, box(0, 0, 10000, 10000), CRS_WKT,
        dict(units="model units", spacing=156.25, target="finite periodic structure with spacing crossover, not an exact fractal"), .01, False)
    import copy
    periodic = copy.deepcopy(cases[-1])
    periodic["dataset_id"] = "control_periodic_grid_wide_range"
    periodic["scales"] = np.geomspace(10., 2500., 24).tolist()
    periodic["scale_rule"] = "exploratory range-sensitivity follow-up: 10 to 2500 model units, crosses known 156.25 spacing by >1 decade below"
    periodic["metadata"]["exploratory_follow_up"] = "added after observing compatibility of the default finite interval; no threshold tuning"
    cases.append(periodic)
    # Resolution sensitivity is declared from geometry/source only, before fits.
    natural = sorted((c for c in cases if c["georeferenced"]), key=lambda c: (c["unique_parts"], c["dataset_id"]))
    representatives = natural[:1] + [c for c in cases if c["source"] == "fraxet_selected"][:1]
    for case in representatives:
        for multiplier in (2, 4):
            variant = copy.deepcopy(case)
            variant["dataset_id"] += f"__resolution_x{multiplier}"
            variant["resolution"] *= multiplier
            x0, y0, x1, y1 = variant["boundary_bounds"]
            width = min(x1-x0, y1-y0)
            lower, upper = max(4*variant["resolution"], width/128), width/4
            variant["scales"] = np.geomspace(lower, upper, 16).tolist() if lower < upper else [lower]
            variant["metadata"]["resolution_sensitivity_of"] = case["dataset_id"]
            variant["metadata"]["resolution_multiplier"] = multiplier
            cases.append(variant)
    manifest = dict(format="musa-extended-inputs", version=1, cases=cases, failures=failures, not_applicable=not_applicable,
                    original_root=str(RAW), suite_q=list(range(-4, 5)))
    (output / "input_catalog.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    catalog = prepare_inputs(args.output)
    print("INPUTS COMPLETE", len(catalog["cases"]), "failures", catalog["failures"], flush=True)
