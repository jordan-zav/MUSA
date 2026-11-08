"""Hexagonal vs square cells: recovery of known Dq under random rotation and grid origin.

Both grids see identical rotated geometry, the same equal-area scales and the
same fit. The square grid uses the real MUSA partition (musa.mass_partition).
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

MUSA_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(MUSA_SRC))
sys.path.insert(0, str(Path(__file__).parent))

from musa.mass_partition import primitive_masses  # noqa: E402
from musa.scaling import renyi_entropy  # noqa: E402
from hex_partition import hex_masses, spacing_from_eps, _nearest, SQ3  # noqa: E402

QS = np.array([-4., -2., -1., 0., 1., 2., 4.])


# ---------------------------------------------------------------- truth cases
def cascade(levels=8, weights=((.125, .125), (.25, .5))):
    w = np.array(weights)
    mass = np.ones((1, 1))
    for _ in range(levels):
        mass = np.kron(mass, w)
    side = mass.shape[0]
    lengths = mass / mass.max() / (8 * side)
    ys, xs = np.indices(mass.shape)
    cx, cy = (xs.ravel() + .5) / side, (ys.ravel() + .5) / side
    L = lengths.ravel()
    starts = np.column_stack([cx - L / 2, cy])
    ends = np.column_stack([cx + L / 2, cy])
    lw = np.log(w.ravel())
    truth = {}
    for q in QS:
        if q == 1:
            truth[q] = float(-(w.ravel() @ lw) / math.log(2))
        else:
            truth[q] = float(-np.log(np.sum(np.exp(q * lw))) / math.log(2) / (q - 1))
    scales = np.geomspace(2 ** -2, 2 ** -7.5, 16)
    return dict(name="dyadic multifractal cascade (65,536 segments)", starts=starts, ends=ends,
                truth=truth, scales=scales)


def koch(levels=7):
    pts = np.array([[0., 0.], [1., 0.]])
    rot = np.array([[.5, -SQ3 / 2], [SQ3 / 2, .5]])
    for _ in range(levels):
        new = [pts[0]]
        for p, r in zip(pts[:-1], pts[1:]):
            d = (r - p) / 3
            a, b = p + d, p + 2 * d
            new += [a, a + rot @ d, b, r]
        pts = np.array(new)
    D = math.log(4) / math.log(3)
    return dict(name="Koch curve, level 7 (16,384 segments)", starts=pts[:-1], ends=pts[1:],
                truth={q: D for q in QS}, scales=np.geomspace(3 ** -1.5, 3 ** -5.5, 16))


# ---------------------------------------------------------------- estimation
def rotate(starts, ends, theta):
    c, s = math.cos(theta), math.sin(theta)
    R = np.array([[c, -s], [s, c]])
    centre = np.vstack([starts, ends]).mean(axis=0)
    return (starts - centre) @ R.T + centre, (ends - centre) @ R.T + centre


def estimate(starts, ends, scales, grid, u):
    total = float(np.linalg.norm(ends - starts, axis=1).sum())
    lo = np.minimum(starts.min(axis=0), ends.min(axis=0))
    H = np.empty((len(QS), len(scales)))
    occupied = []
    for j, eps in enumerate(scales):
        if grid == "square":
            o = lo + u * eps
            m = primitive_masses(starts, ends, float(eps), float(o[0]), float(o[1]))
        else:
            a = spacing_from_eps(eps)
            o = lo + u[0] * a * np.array([1., 0.]) + u[1] * a * np.array([.5, SQ3 / 2])
            m = hex_masses(starts, ends, float(a), float(o[0]), float(o[1]))
        p = np.fromiter(m.values(), float)
        if not math.isclose(p.sum(), total, rel_tol=1e-9):
            raise ArithmeticError(f"{grid} partition lost length")
        p = p[p > 0] / total
        occupied.append(len(p))
        for k, q in enumerate(QS):
            H[k, j] = renyi_entropy(p, q)
    x = np.log(1 / scales)
    slopes, r2 = [], []
    for k in range(len(QS)):
        b, c = np.polyfit(x, H[k], 1)
        res = H[k] - (b * x + c)
        slopes.append(b)
        r2.append(1 - res @ res / np.sum((H[k] - H[k].mean()) ** 2))
    return np.array(slopes), np.array(r2), occupied


# ---------------------------------------------------------------- self-checks
def self_checks(rng):
    a = 0.37
    pts = rng.uniform(-5, 5, (20000, 2))
    bad = 0
    for x, y in pts:
        i, j = _nearest(x, y, a)
        best = None
        for di in range(-2, 3):
            for dj in range(-2, 3):
                ci, cj = i + di, j + dj
                cx, cy = a * (ci + cj / 2), a * cj * SQ3 / 2
                d = (x - cx) ** 2 + (y - cy) ** 2
                if best is None or d < best[0] - 1e-15:
                    best = (d, (ci, cj))
        bad += best[1] != (i, j)
    # a long straight line must give D0 ~ 1 on both grids
    s = np.array([[0., 0.]])
    e = np.array([[math.cos(.3), math.sin(.3)]])
    sl = {g: float(estimate(s, e, np.geomspace(1e-2, 1e-4, 10), g, np.array([.3, .7]))[0][3])
          for g in ("square", "hex")}
    return dict(nearest_centre_mismatches=int(bad), points_checked=len(pts), straight_line_D0=sl)


def main(out):
    rng = np.random.default_rng(20261107)
    out.mkdir(parents=True, exist_ok=True)
    report = dict(self_checks=self_checks(rng), q=QS.tolist(), cases=[])
    n_cfg = 48
    for case in (cascade(), koch()):
        t0 = time.time()
        truth = np.array([case["truth"][q] for q in QS])
        cfgs = [(0.0, np.array([0., 0.]))] + [(rng.uniform(0, math.pi), rng.uniform(0, 1, 2)) for _ in range(n_cfg)]
        res = {g: [] for g in ("square", "hex")}
        r2s = {g: [] for g in ("square", "hex")}
        for theta, u in cfgs:
            s, e = rotate(case["starts"], case["ends"], theta)
            for g in res:
                d, r2, _ = estimate(s, e, case["scales"], g, u)
                res[g].append(d - truth)
                r2s[g].append(r2)
        summary = {}
        for g in res:
            err = np.array(res[g][1:])
            summary[g] = dict(
                aligned_error=np.round(res[g][0], 4).tolist(),
                bias=np.round(err.mean(0), 4).tolist(),
                sd=np.round(err.std(0, ddof=1), 4).tolist(),
                rmse=np.round(np.sqrt((err ** 2).mean(0)), 4).tolist(),
                max_abs=np.round(np.abs(err).max(0), 4).tolist(),
                median_r2=np.round(np.median(np.array(r2s[g][1:]), 0), 5).tolist())
        sq, hx = np.abs(np.array(res["square"][1:])), np.abs(np.array(res["hex"][1:]))
        summary["hex_better_fraction"] = np.round((hx < sq).mean(0), 3).tolist()
        # paired sign-flip permutation p-value on mean |error| difference, per q
        diff = sq - hx
        pv = []
        for k in range(len(QS)):
            obs = diff[:, k].mean()
            signs = rng.choice([-1, 1], (20000, len(diff)))
            pv.append(float((np.abs((signs * diff[:, k]).mean(1)) >= abs(obs)).mean()))
        summary["paired_p_value"] = np.round(pv, 4).tolist()
        report["cases"].append(dict(name=case["name"], truth=np.round(truth, 4).tolist(),
                                    scales=[float(case["scales"][0]), float(case["scales"][-1])],
                                    random_configurations=n_cfg, seconds=round(time.time() - t0, 1),
                                    **summary))
    (out / "hex_vs_square.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
