"""Extended hex vs square test.

A) Known truth, 64 random rotation/origin configurations, single origin and
   4-origin averaged entropy: dyadic cascade (square-native), Koch (triangular-
   native) and an isotropic cascade (same measure, random segment orientation).
B) Public maps (no truth): stability of Dq across 48 rotations/origins, using
   the scales declared in the 2 Nov benchmark manifests.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from run_hex_vs_square import QS, rotate, cascade, koch, primitive_masses, renyi_entropy  # noqa: E402
from hex_partition import hex_masses, spacing_from_eps, SQ3  # noqa: E402

# Prepared inputs from scripts/extended_benchmark_inputs.py (see docs/EXTENDED_BENCHMARKS.md).
BENCH = Path(os.environ.get("MUSA_BENCH_DATASETS",
                            Path(__file__).resolve().parents[2] / "data/extended_datasets"))
REAL = ["aland_ahvenanmaa_integrated_lineaments_1_200000_traces", "aland_ahvenanmaa_lidar_lineaments_1_200000_traces",
        "loviisa_kb11", "loviisa_og1", "loviisa_kl5", "fracpaq_map1_edit_converted",
        "hatchfrac_fractures", "hornelen_fig7_map1"]


def iso_cascade(rng, levels=8, weights=((.125, .125), (.25, .5))):
    c = cascade(levels, weights)
    mid = (c["starts"] + c["ends"]) / 2
    L = np.linalg.norm(c["ends"] - c["starts"], axis=1)
    th = rng.uniform(0, math.pi, len(L))
    d = np.column_stack([np.cos(th), np.sin(th)]) * (L / 2)[:, None]
    c.update(name="isotropic cascade (random segment orientation)", starts=mid - d, ends=mid + d)
    return c


def polygonal(rng, kind, n=900):
    """Polygonal crack networks (honeycomb with jitter, or Voronoi ~ mud cracks /
    columnar jointing). Below the cell spacing the length measure is a set of
    straight edges, so the finite-range target is Dq = 1 for every q."""
    from scipy.spatial import Voronoi
    side = int(math.sqrt(n))
    if kind == "honeycomb":
        ii, jj = np.meshgrid(np.arange(side), np.arange(side))
        pts = np.column_stack([(ii + (jj % 2) / 2).ravel(), (jj * SQ3 / 2).ravel()]) / side
        pts += rng.normal(0, .03 / side, pts.shape)
        name = "honeycomb crack network (jittered hexagons)"
    else:
        pts = rng.uniform(0, 1, (n, 2))
        name = "Voronoi crack network (mud-crack / columnar-joint analogue)"
    vor = Voronoi(pts)
    s, e = [], []
    for a, b in vor.ridge_vertices:
        if a < 0 or b < 0:
            continue
        p, r = vor.vertices[a], vor.vertices[b]
        if (np.all((p > .1) & (p < .9)) and np.all((r > .1) & (r < .9))):
            s.append(p), e.append(r)
    spacing = 1 / side
    return dict(name=name, starts=np.array(s), ends=np.array(e), truth={q: 1.0 for q in QS},
                scales=np.geomspace(spacing / 3, spacing / 60, 16))


def entropies(starts, ends, scales, grid, us):
    total = float(np.linalg.norm(ends - starts, axis=1).sum())
    lo = np.minimum(starts.min(axis=0), ends.min(axis=0))
    H = np.zeros((len(us), len(QS), len(scales)))
    for j, eps in enumerate(scales):
        for i, u in enumerate(us):
            if grid == "square":
                o = lo + u * eps
                m = primitive_masses(starts, ends, float(eps), float(o[0]), float(o[1]))
            else:
                a = spacing_from_eps(eps)
                o = lo + u[0] * a * np.array([1., 0.]) + u[1] * a * np.array([.5, SQ3 / 2])
                m = hex_masses(starts, ends, float(a), float(o[0]), float(o[1]))
            p = np.fromiter(m.values(), float)
            if not math.isclose(p.sum(), total, rel_tol=1e-9):
                raise ArithmeticError(grid + " lost length")
            p = p[p > 0] / total
            for k, q in enumerate(QS):
                H[i, k, j] = renyi_entropy(p, q)
    return H


def slopes(H, scales):
    x = np.log(1 / np.asarray(scales))
    return np.array([np.polyfit(x, H[k], 1)[0] for k in range(H.shape[0])])


def configs(rng, n):
    out = []
    for _ in range(n):
        theta, u = rng.uniform(0, math.pi), rng.uniform(0, 1, 2)
        four = [(u + np.array(s)) % 1 for s in ((0, 0), (.5, 0), (0, .5), (.5, .5))]
        out.append((theta, four))
    return out


def paired_p(rng, diff):
    obs = diff.mean()
    signs = rng.choice([-1, 1], (20000, len(diff)))
    return float((np.abs((signs * diff).mean(1)) >= abs(obs)).mean())


def summarise(err, rng):
    out = {}
    for g in err:
        e = np.array(err[g])
        out[g] = dict(bias=np.round(e.mean(0), 4).tolist(), sd=np.round(e.std(0, ddof=1), 4).tolist(),
                      rmse=np.round(np.sqrt((e ** 2).mean(0)), 4).tolist())
    sq, hx = np.abs(np.array(err["square"])), np.abs(np.array(err["hex"]))
    out["rmse_change_pct_hex_vs_square"] = np.round(
        100 * (np.sqrt((hx ** 2).mean(0)) / np.sqrt((sq ** 2).mean(0)) - 1), 1).tolist()
    out["hex_better_fraction"] = np.round((hx < sq).mean(0), 3).tolist()
    out["paired_p"] = [round(paired_p(rng, (sq - hx)[:, k]), 4) for k in range(len(QS))]
    return out


def load_real(name):
    import geopandas as gpd
    from musa.mass_partition import primitive_arrays
    folder = BENCH / name
    manifest = json.loads((folder / "input_manifest.json").read_text(encoding="utf-8"))
    frame = gpd.read_file(folder / "input.gpkg", layer="lineaments")
    s, e = primitive_arrays(list(frame.geometry))
    shift = s.min(axis=0)  # avoid large projected coordinates
    return s - shift, e - shift, np.asarray(manifest["scales"])[::-1]


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261108)
    report = dict(q=QS.tolist(), truth_cases=[], real_maps=[])
    for case in (cascade(), koch(), iso_cascade(rng), polygonal(rng, "honeycomb"), polygonal(rng, "voronoi")):
        t0 = time.time()
        truth = np.array([case["truth"][q] for q in QS])
        err = {mode: {"square": [], "hex": []} for mode in ("single_origin", "four_origin_mean")}
        for theta, us in configs(rng, 64):
            s, e = rotate(case["starts"], case["ends"], theta)
            for g in ("square", "hex"):
                H = entropies(s, e, case["scales"], g, us)
                err["single_origin"][g].append(slopes(H[0], case["scales"]) - truth)
                err["four_origin_mean"][g].append(slopes(H.mean(0), case["scales"]) - truth)
        report["truth_cases"].append(dict(name=case["name"], truth=np.round(truth, 4).tolist(),
                                          seconds=round(time.time() - t0, 1),
                                          **{m: summarise(err[m], rng) for m in err}))
        print(case["name"], "done", round(time.time() - t0, 1), "s", flush=True)
    for name in REAL:
        t0 = time.time()
        s0, e0, scales = load_real(name)
        est = {"square": [], "hex": []}
        for theta, us in configs(rng, 48):
            s, e = rotate(s0, e0, theta)
            for g in est:
                est[g].append(slopes(entropies(s, e, scales, g, us[:1])[0], scales))
        row = dict(name=name, segments=len(s0), scales=[float(scales[0]), float(scales[-1])])
        for g in est:
            a = np.array(est[g])
            row[g] = dict(mean=np.round(a.mean(0), 4).tolist(), sd=np.round(a.std(0, ddof=1), 4).tolist(),
                          range=np.round(np.ptp(a, 0), 4).tolist())
        sd_s, sd_h = np.array(row["square"]["sd"]), np.array(row["hex"]["sd"])
        row["sd_ratio_hex_over_square"] = np.round(sd_h / sd_s, 3).tolist()
        row["mean_shift_hex_minus_square"] = np.round(np.array(row["hex"]["mean"]) - np.array(row["square"]["mean"]), 4).tolist()
        report["real_maps"].append(row)
        print(name, "done", round(time.time() - t0, 1), "s", flush=True)
    (out / "hex_vs_square_extended.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("WROTE", out / "hex_vs_square_extended.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
