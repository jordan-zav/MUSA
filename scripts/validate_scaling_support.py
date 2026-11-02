"""Reproducible public synthetic controls and a small conditional-null pilot.

No private input data. A pilot is not general scientific calibration.
"""
import argparse
from dataclasses import asdict
import itertools
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from scipy.stats import beta
from shapely.geometry import LineString, box
from musa import MUSA
from musa.scaling import ScalingOptions, assess_curve, assess_lineament_scaling, _relocate, write_scaling_reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--replicates", type=int, default=39)
    args = parser.parse_args()
    if not 1 <= args.trials <= 1000:
        raise ValueError("Use 1 to 1000 pilot trials.")
    options = ScalingOptions(1, null_replicates=args.replicates, seed=20261101).validate()
    args.output.mkdir(parents=True, exist_ok=False)
    boundary = box(0, 0, 1000, 1000)
    def model(lines):
        return MUSA.from_line_geometries(lines, boundary, "EPSG:32718", q_values=[0, 1, 2])
    scales = np.geomspace(2, 32, 12)
    line = assess_lineament_scaling(model([LineString([(0, 500), (1000, 500)])]),
                                   scales, ScalingOptions(1), support_id="known_line")
    p, levels, fragments = .7, 7, []
    for bits in itertools.product((0, 1), repeat=levels):
        start = 1000 * sum(2 * b * 3. ** (-k - 1) for k, b in enumerate(bits))
        length = 1000 * 3. ** (-levels) * np.prod([p if b == 0 else 1 - p for b in bits]) / p ** levels
        center = start + 500 * 3. ** (-levels)
        fragments.append(LineString([(center - length / 2, 500), (center + length / 2, 500)]))
    cantor = assess_lineament_scaling(model(fragments), np.geomspace(5, 100, 14),
                                     ScalingOptions(1), support_id="finite_binomial_cantor")
    write_scaling_reports(args.output / "controls", [line, cantor])
    for row in line["q_results"]:
        assert abs(row["dimension"] - 1) < .04
    target = {0: np.log(2) / np.log(3), 2: -np.log(p * p + (1 - p) ** 2) / np.log(3)}
    for row in cantor["q_results"]:
        if row["q"] in target:
            assert abs(row["dimension"] - target[row["q"]]) < .07
    # The alternative curves are specified independently of the fitting code.
    curve_scales = np.geomspace(1, 100, 16)
    x = np.log(1 / curve_scales)
    x -= x.mean()
    alternatives = {"quadratic": 5 + x + .35 * x * x,
                    "broken": 5 + x + 1.5 * np.maximum(x - .2, 0)}
    curve_checks = {key: assess_curve(curve_scales, y, ScalingOptions(.1)) for key, y in alternatives.items()}
    assert all(row["status"] == "not_supported" for row in curve_checks.values())
    # Generate independent observations FROM the declared null, not from fixed
    # preset Dq profiles. All failures/non-testable observations remain recorded.
    shapes = [LineString([(100, float(y)), (900, float(y))]) for y in np.linspace(100, 900, 8)]
    trials = []
    rng = np.random.default_rng(20261101)
    started = time.perf_counter()
    for i in range(args.trials):
        lines = _relocate(shapes, boundary, rng, options.max_placement_attempts)
        assert lines is not None
        trial_options = ScalingOptions(1, null_replicates=args.replicates, seed=10000 + i)
        report = assess_lineament_scaling(model(lines), scales, trial_options, support_id=f"null_trial_{i}")
        write_scaling_reports(args.output / f"trial_{i:03}", [report])
        trials.append({"trial": i, "status": report["null"]["status"], "p": report["null"]["p_value"],
                       "q_status": {str(row["q"]): row["status"] for row in report["q_results"]}})
        print(f"pilot {i + 1}/{args.trials}: {trials[-1]}", flush=True)
    rejected = sum(t["p"] is not None and t["p"] <= .05 for t in trials)
    tested = sum(t["p"] is not None for t in trials)
    low = float(beta.ppf(.025, rejected, args.trials - rejected + 1)) if rejected else 0.0
    high = float(beta.ppf(.975, rejected + 1, args.trials - rejected)) if rejected < args.trials else 1.0
    report = {"seed": 20261101, "options": asdict(options), "null_pilot_trials": trials,
              "trials": args.trials, "tested": tested, "rejected_at_0_05": rejected,
              "rejection_fraction_over_all_requested_trials": rejected / args.trials,
              "binomial_95_interval_over_all_trials": [low, high],
              "seconds": time.perf_counter() - started, "curve_controls": curve_checks,
              "analytic_cantor_targets": target,
              "interpretation": "small conditional-null pilot, including gates/non-testable trials; not certification of 5% size or power across networks, q or window families"}
    (args.output / "validation.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(13, 5), constrained_layout=True)
    FigureCanvasAgg(fig)
    ax, second = fig.subplots(1, 2)
    for data, label in ((line, "Uniform line"), (cantor, "Finite binomial Cantor")):
        ax.plot([r["q"] for r in data["q_results"]], [r["dimension"] for r in data["q_results"]], "o-", label=label)
    ax.set(xlabel="Renyi order q", ylabel="Estimated Dq", title="Geometry controls: dimensions, not preset profiles")
    ax.legend()
    for key, y in alternatives.items():
        second.plot(x, y, "o-", label=key + ": not supported")
    second.set(xlabel="Centered log(1 / box size)", ylabel="Entropy feature", title="Known nonlinear scaling controls")
    second.legend()
    fig.savefig(args.output / "controls.png", dpi=150)
    print(json.dumps({key: report[key] for key in ("trials", "tested", "rejected_at_0_05", "binomial_95_interval_over_all_trials", "seconds")}, indent=2))


if __name__ == "__main__":
    main()
