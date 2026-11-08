"""Is grid-rotation averaging of squares as good as hexagons? Equal budget: 4 partitions.

Estimators (entropy curves averaged over 4 partitions, then one slope):
  square_4origin  : MUSA-like origin averaging, one grid orientation
  square_4rot     : grid rotated 0, 22.5, 45, 67.5 deg (+ random origin each)
  hex_4origin     : hexagon, 4 origins
  hex_4rot        : hexagon rotated 0, 15, 30, 45 deg (+ random origin each)
  square_1        : single partition baseline
Map orientation itself is random in every configuration.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from run_hex_vs_square import QS, rotate, cascade, koch  # noqa: E402
from run_extended import entropies, slopes, iso_cascade, polygonal, load_real, REAL, paired_p  # noqa: E402

SHIFTS = [np.array(s) for s in ((0, 0), (.5, 0), (0, .5), (.5, .5))]


def curves(s, e, scales, theta, u, rng):
    """Return dict estimator -> averaged entropy array (q x scales)."""
    out = {}
    base_s, base_e = rotate(s, e, theta)
    out["square_1"] = entropies(base_s, base_e, scales, "square", [u])[0]
    out["square_4origin"] = entropies(base_s, base_e, scales, "square", [(u + d) % 1 for d in SHIFTS]).mean(0)
    out["hex_4origin"] = entropies(base_s, base_e, scales, "hex", [(u + d) % 1 for d in SHIFTS]).mean(0)
    for grid, step in (("square", math.pi / 8), ("hex", math.pi / 12)):
        acc = []
        for k in range(4):
            rs, re = rotate(s, e, theta + k * step)
            acc.append(entropies(rs, re, scales, grid, [rng.uniform(0, 1, 2)])[0])
        out[grid + "_4rot"] = np.mean(acc, 0)
    return out


NAMES = ["square_1", "square_4origin", "square_4rot", "hex_4origin", "hex_4rot"]


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261109)
    report = dict(q=QS.tolist(), estimators=NAMES, truth_cases=[], real_maps=[])
    for case in (cascade(), koch(), iso_cascade(rng), polygonal(rng, "voronoi")):
        t0 = time.time()
        truth = np.array([case["truth"][q] for q in QS])
        err = {n: [] for n in NAMES}
        for _ in range(48):
            c = curves(case["starts"], case["ends"], case["scales"], rng.uniform(0, math.pi), rng.uniform(0, 1, 2), rng)
            for n in NAMES:
                err[n].append(slopes(c[n], case["scales"]) - truth)
        row = dict(name=case["name"], seconds=round(time.time() - t0, 1),
                   rmse={n: np.round(np.sqrt((np.array(err[n]) ** 2).mean(0)), 4).tolist() for n in NAMES})
        sq, hx = np.abs(np.array(err["square_4rot"])), np.abs(np.array(err["hex_4origin"]))
        row["p_square4rot_vs_hex4origin"] = [round(paired_p(rng, (sq - hx)[:, k]), 4) for k in range(len(QS))]
        report["truth_cases"].append(row)
        print(case["name"], "done", row["seconds"], "s", flush=True)
    for name in REAL:
        t0 = time.time()
        s0, e0, scales = load_real(name)
        est = {n: [] for n in NAMES}
        for _ in range(32):
            c = curves(s0, e0, scales, rng.uniform(0, math.pi), rng.uniform(0, 1, 2), rng)
            for n in NAMES:
                est[n].append(slopes(c[n], scales))
        report["real_maps"].append(dict(name=name, sd={n: np.round(np.array(est[n]).std(0, ddof=1), 4).tolist() for n in NAMES},
                                        mean={n: np.round(np.array(est[n]).mean(0), 4).tolist() for n in NAMES}))
        print(name, "done", round(time.time() - t0, 1), "s", flush=True)
    (out / "rotation_vs_hex.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("WROTE", out / "rotation_vs_hex.json")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
