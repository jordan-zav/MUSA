"""Finite-range Renyi scaling diagnostics and a conditional spatial null model.

Fit criteria are explicit operational diagnostics, not a proof of fractality.
Monte Carlo inference concerns trace placement conditional on supplied shapes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

from .control import check_cancelled


@dataclass(frozen=True)
class ScalingOptions:
    resolution_m: float
    min_scales: int = 8
    min_decades: float = 1.0
    min_effective_boxes: float = 2.0
    max_box_fraction: float = 0.25
    min_coverage: float = 0.8
    min_r2: float = 0.98
    slope_tolerance: float = 0.10
    curvature_effect: float = 0.03
    cv_ratio: float = 0.75
    null_replicates: int = 0
    seed: int = 42
    max_placement_attempts: int = 1000
    renyi_order_policy: str = "legacy_block"

    def validate(self):
        numeric = [self.resolution_m, self.min_decades, self.min_effective_boxes,
                   self.max_box_fraction, self.min_coverage, self.min_r2,
                   self.slope_tolerance, self.curvature_effect, self.cv_ratio]
        if not np.isfinite(numeric).all() or self.resolution_m <= 0:
            raise ValueError("Declare a positive, finite observation resolution in metres.")
        if type(self.min_scales) is not int or not 8 <= self.min_scales <= 64:
            raise ValueError("Scaling diagnostics require 8 to 64 minimum scales.")
        if self.min_decades <= 0 or self.min_effective_boxes < 2:
            raise ValueError("Use a positive scaling span and at least two effective boxes.")
        if not 0 < self.max_box_fraction <= 1 or not 0 < self.min_coverage <= 1:
            raise ValueError("Invalid boundary or coverage limits.")
        if not 0 <= self.min_r2 < 1 or self.slope_tolerance <= 0 or self.curvature_effect <= 0:
            raise ValueError("Invalid fit or stability tolerances.")
        if not 0 < self.cv_ratio < 1:
            raise ValueError("The alternative-model CV ratio must be in (0,1).")
        if type(self.null_replicates) is not int or self.null_replicates not in (0,) and not 19 <= self.null_replicates <= 9999:
            raise ValueError("Use zero null replicates, or 19 to 9999.")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("Use a nonnegative integer seed.")
        if type(self.max_placement_attempts) is not int or self.max_placement_attempts < 1:
            raise ValueError("Placement attempts must be a positive integer.")
        if self.renyi_order_policy not in ("legacy_block", "inform_q0_q2"):
            raise ValueError("Use renyi_order_policy='legacy_block' or 'inform_q0_q2'.")
        return self


def renyi_entropy(probabilities, q):
    """Natural-log Renyi entropy on occupied boxes; Shannon limit at q=1."""
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 1 or not p.size or not np.isfinite(p).all() or (p <= 0).any():
        raise ValueError("Use positive, finite occupied-box probabilities.")
    if not np.isfinite(q) or abs(q) > 100:
        raise ValueError("q must be finite and within [-100,100].")
    total = p.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Probability mass must have a finite positive total.")
    p = p / total
    logp = np.log(p)
    if q == 0:
        return float(np.log(len(p)))
    if abs(q - 1) < 1e-7:
        # First-order expansion avoids catastrophic cancellation near one.
        mean = float(p @ logp)
        variance = float(p @ (logp - mean) ** 2)
        return -mean - .5 * (q - 1) * variance
    return float(logsumexp(q * logp) / (1 - q))


def _design(x, model, knot=None):
    columns = [np.ones(len(x)), x]
    if model == "quadratic":
        columns.append(x * x)
    elif model == "segmented":
        columns.append(np.maximum(0, x - knot))
    return np.column_stack(columns)


def _fit(x, y, model):
    candidates = [None]
    if model == "segmented":
        ordered = np.sort(x)
        candidates = [(ordered[i - 1] + ordered[i]) / 2 for i in range(3, len(x) - 2)]
    best = None
    for knot in candidates:
        matrix = _design(x, model, knot)
        beta, _, rank, _ = np.linalg.lstsq(matrix, y, rcond=None)
        if rank != matrix.shape[1]:
            continue
        sse = float(np.sum((y - matrix @ beta) ** 2))
        if best is None or sse < best[0]:
            best = (sse, beta, knot)
    return best


def _models(x, y):
    # The knot is reselected inside every training fold, never on the held-out y.
    output = {}
    for model in ("linear", "quadratic", "segmented"):
        fit = _fit(x, y, model)
        errors = []
        for i in range(len(x)):
            keep = np.arange(len(x)) != i
            training = _fit(x[keep], y[keep], model)
            if training is None:
                break
            _, beta, knot = training
            errors.append(float(y[i] - (_design(x[i:i + 1], model, knot) @ beta)[0]))
        if fit is not None and len(errors) == len(x):
            sse, beta, knot = fit
            output[model] = {"sse": sse, "cv_rmse": float(np.sqrt(np.mean(np.square(errors)))),
                             "coefficients": beta.tolist(), "knot_centered_log_inverse_scale": knot}
    return output


def assess_curve(scales_m, entropies, options, *, origin_dimensions=(), min_effective=None, observable="dq"):
    """Assess a fixed interval, without selecting favorable subranges or q."""
    options.validate()
    scales, y = np.asarray(scales_m, float), np.asarray(entropies, float)
    if scales.ndim != 1 or y.shape != scales.shape or not np.isfinite(scales).all() or (scales <= 0).any():
        raise ValueError("Scales must be positive, finite and match the curve.")
    if len(np.unique(scales)) != len(scales):
        raise ValueError("Duplicate scales are not independent scale observations.")
    result = {"status": "insufficient_information", "reasons": [], "scale_count": len(scales),
              "span_decades": float(np.log10(max(scales) / min(scales))) if len(scales) else 0,
              "dimension": None, "models": {}, "r2": None,
              "leave_scale_out_range": None, "origin_dimension_range": None}
    # Signed distances are descriptive only; the native decisions below retain
    # their original inequalities and numerical tolerances.
    result["margins"] = {
        "scale_count": len(scales) - options.min_scales,
        "span_decades": result["span_decades"] - options.min_decades,
        "resolution_m": float(min(scales) - options.resolution_m) if len(scales) else None,
        "min_effective_boxes": float(min_effective - options.min_effective_boxes)
        if min_effective is not None and np.isfinite(min_effective) else None,
        "r2": None, "dimension_lower": None, "dimension_upper": None,
        "leave_scale_out_range": None, "origin_dimension_range": None, "curvature": {},
    }
    reasons = result["reasons"]
    if len(scales) < options.min_scales:
        reasons.append("too_few_resolved_scales")
    if result["span_decades"] < options.min_decades - 1e-12:
        reasons.append("short_scaling_interval")
    if not np.isfinite(y).all():
        reasons.append("invalid_entropy")
    if len(scales) and min(scales) < options.resolution_m:
        reasons.append("below_observation_resolution")
    if min_effective is not None:
        if not np.isfinite(min_effective):
            reasons.append("invalid_effective_boxes")
        elif min_effective < options.min_effective_boxes - 1e-10:
            reasons.append("insufficient_effective_boxes")
    if reasons:
        return result
    x = np.log(1 / scales)
    result["x_center_log_inverse_scale"] = float(x.mean())
    x -= x.mean()
    models = _models(x, y)
    result["models"] = models
    dimension = models["linear"]["coefficients"][1]
    result["dimension"] = dimension
    total = float(np.sum((y - y.mean()) ** 2))
    result["r2"] = 0.0 if total < 1e-20 else max(0.0, 1 - models["linear"]["sse"] / total)
    result["margins"].update(r2=result["r2"] - options.min_r2,
                             dimension_lower=dimension + options.slope_tolerance,
                             dimension_upper=2 + options.slope_tolerance - dimension)
    slopes = []
    for indices in [np.delete(np.arange(len(x)), i) for i in range(len(x))] + [np.arange(1, len(x) - 1)]:
        slopes.append(float(_fit(x[indices], y[indices], "linear")[1][1]))
    spread = max(slopes + [dimension]) - min(slopes + [dimension])
    result["leave_scale_out_range"] = spread
    result["margins"]["leave_scale_out_range"] = options.slope_tolerance - spread
    origins = np.asarray(origin_dimensions, float)
    if origins.size and not np.isfinite(origins).all():
        result["reasons"].append("invalid_origin_estimate")
        return result
    origin_range = float(np.ptp(origins)) if origins.size else 0.0
    result["origin_dimension_range"] = origin_range
    result["margins"]["origin_dimension_range"] = options.slope_tolerance - origin_range
    failure = result["reasons"]
    if total < 1e-20:
        failure.append("constant_curve")
    if result["r2"] < options.min_r2:
        failure.append("poor_linear_fit")
    if observable == "dq" and not -options.slope_tolerance <= dimension <= 2 + options.slope_tolerance:
        failure.append("dimension_outside_planar_range")
    if spread > options.slope_tolerance:
        failure.append("scale_sensitive_dimension")
    if origin_range > options.slope_tolerance:
        failure.append("grid_sensitive_dimension")
    linear_error = models["linear"]["cv_rmse"]
    for name, model in models.items():
        if name == "linear":
            continue
        gain = (linear_error - model["cv_rmse"]) / np.ptp(x)
        ratio = model["cv_rmse"] / linear_error if linear_error else None
        result["margins"]["curvature"][name] = {
            "gain_effect": float(gain), "effect": float(options.curvature_effect - gain),
            "cv_ratio": float(ratio) if ratio is not None else None,
            "ratio": float(ratio - options.cv_ratio) if ratio is not None else None,
        }
        if model["cv_rmse"] < options.cv_ratio * linear_error and gain > options.curvature_effect:
            failure.append(name + "_predicts_better")
    result["status"] = "not_supported" if failure else "compatible_finite_range"
    return result


def _curves(lines, boundary, scales, qs, offsets, cancelled=None, *, singularities=False):
    from .mass_partition import primitive_arrays, primitive_masses
    starts, ends = primitive_arrays(lines)
    total = sum(line.length for line in lines)
    origin = np.asarray(boundary.bounds[:2])
    curves = np.empty((len(offsets), len(qs), len(scales)))
    features = {name: np.empty_like(curves) for name in ("tau", "alpha", "f_alpha")} if singularities else {}
    effective = np.full(len(qs), np.inf)
    for j, scale in enumerate(scales):
        check_cancelled(cancelled)
        for i, offset in enumerate(offsets):
            masses = np.asarray(list(primitive_masses(starts, ends, float(scale),
                                                      *map(float, origin + offset * scale)).values()))
            if not np.isclose(masses.sum(), total, rtol=1e-9, atol=1e-8):
                raise ArithmeticError("Scaling partition did not conserve line length.")
            p = masses / total
            logp = np.log(p)
            for k, q in enumerate(qs):
                curves[i, k, j] = renyi_entropy(p, q)
                logmu = q * logp - logsumexp(q * logp)
                effective[k] = min(effective[k], float(np.exp(-logsumexp(2 * logmu))))
                if singularities:
                    mu = np.exp(logmu)
                    # All slopes use x=log(1/epsilon); CJ features change sign.
                    features["tau"][i, k, j] = 0.0 if q == 1 else -logsumexp(q * logp)
                    features["alpha"][i, k, j] = -np.sum(mu * logp)
                    features["f_alpha"][i, k, j] = -np.sum(mu * logmu)
    return (curves, effective, features) if singularities else (curves, effective)


def _relocate(lines, boundary, rng, attempts, cancelled=None):
    from shapely.affinity import translate
    xmin, ymin, xmax, ymax = boundary.bounds
    relocated = []
    for line in lines:
        a, b, c, d = line.bounds
        for _ in range(attempts):
            check_cancelled(cancelled)
            dx = rng.uniform(xmin - a, xmax - c)
            dy = rng.uniform(ymin - b, ymax - d)
            candidate = translate(line, xoff=dx, yoff=dy)
            if boundary.covers(candidate):
                relocated.append(candidate)
                break
        else:
            return None
    return relocated


def monte_carlo_tail(observed, simulations):
    values = np.asarray(simulations, float)
    if not values.size or not np.isfinite(values).all() or not np.isfinite(observed):
        raise ValueError("Monte Carlo statistics must be finite and nonempty.")
    tolerance = 1e-12 * max(1.0, abs(observed))
    return float((1 + np.count_nonzero(values >= observed - tolerance)) / (len(values) + 1))


def holm_adjust(p_values):
    """Familywise adjustment valid under dependence, for the declared family."""
    values = np.asarray(p_values, float)
    if values.ndim != 1 or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Use finite p values in [0,1].")
    order = np.argsort(values)
    result = np.empty(len(values))
    result[order] = np.minimum(1, np.maximum.accumulate(values[order] * np.arange(len(values), 0, -1)))
    return result.tolist()


def _pair_order(q_results):
    """Explicit q=0,2 diagnostic, independent of the requested spectrum grid."""
    dimensions = {r["q"]: r["dimension"] for r in q_results
                  if r["q"] in (0, 2) and r["dimension"] is not None
                  and np.isfinite(r["dimension"])}
    delta = float(dimensions[2] - dimensions[0]) if len(dimensions) == 2 else None
    warning = delta > .10 if delta is not None else None
    return {"q": [0.0, 2.0], "delta02": delta, "tolerance": .10,
            "margin": .10 - delta if delta is not None else None,
            "status": "not_evaluated" if delta is None else
            "violated_beyond_tolerance" if warning else "within_tolerance",
            "warning": warning,
            "message": "D2 exceeds D0 by more than 0.10 in this finite range; not an entropy error."
            if warning else None}


def assess_lineament_scaling(analyzer, scales_m, options, *, support_id="global",
                             boundary=None, nominal_area=None, cancelled=None, progress=None):
    """Diagnostics for one explicit planar support, all q retained, no q filtering.

    Scales below resolution or above the declared boundary fraction are excluded
    by design, not by observed fit. No favorable interval is searched.
    """
    options.validate()
    check_cancelled(cancelled)
    from .network import _iter_line_parts
    from shapely.ops import unary_union
    boundary = analyzer._boundary_geom if boundary is None else boundary
    if analyzer._kind != "lines" or boundary.is_empty or not boundary.is_valid or boundary.area <= 0:
        raise ValueError("Scaling support requires lines and a valid polygon domain.")
    requested = np.asarray(scales_m, float)
    qs = np.asarray(analyzer.q_values, float)
    if requested.ndim != 1 or not 1 <= len(requested) <= 64 or not np.isfinite(requested).all() or (requested <= 0).any() or len(np.unique(requested)) != len(requested):
        raise ValueError("Declare 1 to 64 distinct, positive box sizes.")
    if qs.ndim != 1 or not 1 <= len(qs) <= 401 or not np.isfinite(qs).all() or np.max(abs(qs)) > 100 or len(np.unique(qs)) != len(qs):
        raise ValueError("Declare distinct q values in [-100,100].")
    lines = []
    for line in analyzer._line_geometries:
        check_cancelled(cancelled)
        lines.extend(part for part in _iter_line_parts(line.intersection(boundary)) if part.length > 0)
    length = sum(line.length for line in lines)
    # Reject overlapping trace multiplicity rather than silently altering the
    # conditional shape/length inventory used by the spatial null hypothesis.
    if lines and not np.isclose(unary_union(lines).length, length, rtol=1e-9, atol=1e-8):
        raise ValueError("Deduplicate coincident trace segments before scaling assessment.")
    width, height = np.diff(np.asarray(boundary.bounds).reshape(2, 2), axis=0)[0]
    maximum = min(width, height) * options.max_box_fraction
    scales = np.sort(requested[(requested >= options.resolution_m) & (requested <= maximum)])[::-1]
    offsets = np.array([(.137, .271), (.637, .271), (.137, .771), (.637, .771)])
    coverage = boundary.area / (nominal_area if nominal_area is not None else boundary.area)
    report = {"support_id": str(support_id), "options": asdict(options), "coverage": coverage,
              "renyi_order_policy": options.renyi_order_policy,
              "renyi_spectrum_order": {"status": "not_evaluated", "scope": "requested_q"},
              "renyi_pair_order": _pair_order([]),
              "margins": {"coverage": float(coverage - options.min_coverage)},
              "scale_margins": [{"scale_m": float(scale),
                                 "resolution_m": float(scale - options.resolution_m),
                                 "maximum_box_m": float(maximum - scale),
                                 "used": bool(options.resolution_m <= scale <= maximum)}
                                for scale in requested],
              "requested_scales_m": requested.tolist(), "used_scales_m": scales.tolist(),
              "excluded_scales_m": sorted(set(requested.tolist()) - set(scales.tolist())),
              "grid_offsets": offsets.tolist(), "measure": "line length; no floor or zeta weighting",
              "curves": [], "q_results": [], "null": {"status": "not_requested", "p_value": None,
              "statistic": "D0_minus_D2", "values": [], "replicates_requested": options.null_replicates},
              "interpretation": "finite-range Renyi scaling diagnostics; not proof of fractality"}
    if not lines or coverage < options.min_coverage or not len(scales):
        reason = "no_line_support" if not lines else "low_coverage" if coverage < options.min_coverage else "no_resolved_scales"
        report["q_results"] = [{"q": float(q), "status": "insufficient_information", "reasons": [reason],
                                "dimension": None, "margins": {}} for q in qs]
        report["null"]["status"] = "insufficient_information"
        return report
    curves, effective, features = _curves(lines, boundary, scales, qs, offsets, cancelled, singularities=True)
    for k, q in enumerate(qs):
        origins = []
        if len(scales) > 1:
            x = np.log(1 / scales)
            origins = [_fit(x - x.mean(), curve[k], "linear")[1][1] for curve in curves]
        result = assess_curve(scales, curves[:, k].mean(axis=0), options,
                              origin_dimensions=origins, min_effective=float(effective[k]))
        result.update(q=float(q), min_effective_boxes=float(effective[k]))
        result["observables"] = {}
        for name, values in features.items():
            per_origin = [_fit(x - x.mean(), curve[k], "linear")[1][1] for curve in values] if len(scales) > 1 else []
            assessment = assess_curve(scales, values[:, k].mean(axis=0), options,
                                      origin_dimensions=per_origin, min_effective=float(effective[k]), observable=name)
            if name == "tau" and q == 1:
                # Normalization fixes tau(1)=0: no fit R2 or scaling claim.
                assessment.update(status="identity", dimension=0.0, r2=None, models={},
                                  reasons=["normalization_identity_not_scaling_evidence"])
            result["observables"][name] = assessment
        result["tau"] = (float(q) - 1) * result["dimension"] if result["dimension"] is not None else None
        result["alpha"] = result["observables"]["alpha"]["dimension"]
        result["f_alpha"] = result["observables"]["f_alpha"]["dimension"]
        if q == 1:
            result["tau"] = 0.0
        from .spectrum_products import identity_diagnostics
        result["identities"] = identity_diagnostics(float(q), result["dimension"], result["tau"], result["alpha"], result["f_alpha"])
        report["q_results"].append(result)
        report["curves"].extend({"q": float(q), "scale_m": float(scale),
                                 "entropy": float(curves[:, k, j].mean()),
                                 "origin_entropies": curves[:, k, j].tolist(),
                                 **{name + "_feature": float(value[:, k, j].mean()) for name, value in features.items()},
                                 **{name + "_origin_features": value[:, k, j].tolist() for name, value in features.items()}}
                                for j, scale in enumerate(scales))
    ordered = sorted((r["q"], r["dimension"]) for r in report["q_results"] if r["dimension"] is not None)
    report["renyi_dimension_order"] = {
        "status": "not_evaluated" if len(ordered) < 2 else "violated_beyond_tolerance"
        if any(b[1] - a[1] > options.slope_tolerance for a, b in zip(ordered, ordered[1:])) else "within_tolerance",
        "expectation": "Dq nonincreasing in q; finite-range estimates may deviate",
        "tolerance": options.slope_tolerance,
    }
    # Keep the historical field and its scope unchanged for legacy consumers.
    report["renyi_spectrum_order"] = {**report["renyi_dimension_order"], "scope": "requested_q"}
    report["renyi_pair_order"] = _pair_order(report["q_results"])
    if not options.null_replicates:
        return report
    if options.renyi_order_policy == "legacy_block" and report["renyi_dimension_order"]["status"] == "violated_beyond_tolerance":
        report["null"]["status"] = "inconsistent_renyi_dimension_order"
        return report
    q0, q2 = np.flatnonzero(qs == 0), np.flatnonzero(qs == 2)
    if not len(q0) or not len(q2):
        report["null"]["status"] = "requires_q0_and_q2"
        return report
    pair = [int(q0[0]), int(q2[0])]
    if any(report["q_results"][i]["status"] != "compatible_finite_range" for i in pair):
        report["null"]["status"] = "scaling_not_supported_for_q0_q2"
        return report
    observed = report["q_results"][pair[0]]["dimension"] - report["q_results"][pair[1]]["dimension"]
    null = report["null"]
    null.update(observed=observed, model="independent_uniform_translation_of_fixed_observed_trace_shapes",
                preserves="trace count, shape, length, orientation, total mass and polygon containment",
                changes="trace positions, intersections, local density and spatial dependence",
                inference="conditional spatial heterogeneity under this relocation model; not multifractality proof")
    rng = np.random.default_rng(options.seed)
    x = np.log(1 / scales)
    x -= x.mean()
    for i in range(options.null_replicates):
        check_cancelled(cancelled)
        if progress:
            progress(f"{support_id}: spatial null {i + 1}/{options.null_replicates}")
        relocated = _relocate(lines, boundary, rng, options.max_placement_attempts, cancelled)
        if relocated is None:
            null["status"] = "placement_failed_no_p_value"
            return report
        null_curves, null_effective = _curves(relocated, boundary, scales, qs[pair], offsets, cancelled)
        # Never discard a difficult realization or resample until a fit passes.
        if min(null_effective) < options.min_effective_boxes - 1e-10:
            null["status"] = "null_support_failed_no_p_value"
            return report
        dimensions = [_fit(x, null_curves[:, j].mean(axis=0), "linear")[1][1] for j in range(2)]
        null["values"].append(float(dimensions[0] - dimensions[1]))
    if np.ptp(null["values"]) < 1e-10:
        null["status"] = "degenerate_null_no_p_value"
    else:
        null.update(status="complete", p_value=monte_carlo_tail(observed, null["values"]),
                    minimum_p=1 / (options.null_replicates + 1))
    return report


def write_scaling_reports(output_dir, reports):
    """Adjust over all requested supports, including untestable ones as p=1."""
    reports = list(reports)
    adjusted = holm_adjust([r["null"]["p_value"] if r["null"]["p_value"] is not None else 1.0 for r in reports])
    for report, p in zip(reports, adjusted):
        null = report["null"]
        null["holm_family_size"] = len(reports)
        null["p_holm"] = p if null["p_value"] is not None else None
        null["reject_relocation_at_0_05"] = bool(null["p_value"] is not None and p <= .05)
        b = null["replicates_requested"]
        null["minimum_possible_holm_p"] = min(1.0, len(reports) / (b + 1)) if b else None
        null["resolution_sufficient_for_family_at_0_05"] = bool(b and len(reports) / (b + 1) <= .05)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"format": "musa-scaling-support", "version": 2, "supports": reports,
               "selection": "fixed requested scales, resolution/boundary exclusions; no best-range search",
               "inference": "fit criteria are operational; Holm covers this report's support family only"}
    target = out / "scaling_support.json"
    target.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    table = out / "scaling_support.csv"
    fields = ["support_id", "center_id", "center_x", "center_y", "window_m", "q", "status", "reasons", "dimension", "r2", "scale_count", "span_decades",
              "leave_scale_out_range", "origin_dimension_range", "tau", "alpha", "f_alpha",
              "tau_status", "alpha_status", "f_alpha_status", "identity_status", "identity_max_error",
              "null_status", "null_p", "null_p_holm"]
    margin_keys = ("scale_count", "span_decades", "resolution_m", "min_effective_boxes", "r2",
                   "dimension_lower", "dimension_upper", "leave_scale_out_range", "origin_dimension_range")
    fields += ["renyi_order_policy", "renyi_spectrum_order_status", "renyi_pair_order_status",
               "delta02", "renyi_pair_order_warning", "renyi_pair_order_message",
               "margin_pair_order", "margin_coverage", "scale_margins_json"]
    fields += ["margin_" + key for key in margin_keys]
    for model in ("quadratic", "segmented"):
        fields += [model + "_gain_effect", "margin_" + model + "_effect",
                   model + "_cv_ratio", "margin_" + model + "_cv_ratio"]
    with table.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for report in reports:
            for result in report["q_results"]:
                row = {k: result.get(k) for k in fields}
                row.update({key: report.get(key) for key in ("center_id", "center_x", "center_y", "window_m")})
                row.update({name + "_status": result.get("observables", {}).get(name, {}).get("status")
                            for name in ("tau", "alpha", "f_alpha")})
                row.update(identity_status=result.get("identities", {}).get("status"),
                           identity_max_error=result.get("identities", {}).get("max_error"))
                row.update(support_id=report["support_id"], reasons=";".join(result["reasons"]),
                           null_status=report["null"]["status"], null_p=report["null"]["p_value"],
                           null_p_holm=report["null"]["p_holm"])
                pair_order = report.get("renyi_pair_order", {})
                row.update(renyi_order_policy=report.get("renyi_order_policy", "legacy_block"),
                           renyi_spectrum_order_status=report.get("renyi_spectrum_order", {}).get("status"),
                           renyi_pair_order_status=pair_order.get("status"),
                           delta02=pair_order.get("delta02"), renyi_pair_order_warning=pair_order.get("warning"),
                           renyi_pair_order_message=pair_order.get("message"),
                           margin_pair_order=pair_order.get("margin"),
                           margin_coverage=report.get("margins", {}).get("coverage"),
                           scale_margins_json=json.dumps(report.get("scale_margins", []), allow_nan=False))
                margins = result.get("margins", {})
                row.update({"margin_" + key: margins.get(key) for key in margin_keys})
                for model in ("quadratic", "segmented"):
                    values = margins.get("curvature", {}).get(model, {})
                    row.update({model + "_gain_effect": values.get("gain_effect"),
                                "margin_" + model + "_effect": values.get("effect"),
                                model + "_cv_ratio": values.get("cv_ratio"),
                                "margin_" + model + "_cv_ratio": values.get("ratio")})
                writer.writerow(row)
    from .spectrum_products import write_spectrum_products
    products = write_spectrum_products(out, assessments=reports, source="assessment")
    return {"scaling_support_json": str(target), "scaling_support_csv": str(table), **products}
