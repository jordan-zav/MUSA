# Candidate classification: open-boundary origin ensemble (v7)

The GUI and Python export use the same backend. `trap_candidates` contains three
**relative contrast classes**, not three levels of geological prospectivity.
Exact interior intersections and proximity relations supply locations; ordinary
line vertices/endpoints are controls. No automatic bonus is awarded for a crossing,
degree, angle, proximity or interpreted structural order.

## Current v7 execution profile

The experimental GUI defaults use 16 equally weighted origins per scale,
with two distinct origin banks. Low-level Python `analyze_moving_windows` remains
compatible with a single origin unless `origin_offsets` is supplied. Use
`ENSEMBLE_OFFSETS` and `ENSEMBLE_DIVISORS` from `musa.moving` to reproduce v7.
The GUI permits disabling the ensemble; it never silently changes the divisor
list when the checkbox is toggled.

The fixed offsets form a 4 by 4 grid shifted by (0.137, 0.271) modulo one box.
This avoids assigning special weight to exactly edge-aligned origins. The second
bank shifts by (0.125, 0.125). Seven divisors are used: 16,24,32,48,64,96,128.
These settings are numerical choices checked with known-dimension synthetic
controls, not published geological calibration or a project-specific benchmark.
No periodic wrapping, reflection, snapping or continuation of faults is applied.

For each scale, each origin conserves the same observed length. Compute the
entropy, generalized-dimension feature, alpha feature and f feature separately
for every origin, then average the FEATURES before regression. Do not concatenate
probabilities from different origins as if they were extra cells. Zeta is computed
by the existing four-factor rule per origin and averaged per scale for weighted
regression. `origin_alpha_json` / `origin_alpha_w_json` retain the per-origin
slopes under the same regression weights. `scale_diagnostics_json` contains the
per-origin counts, mass, entropy and zeta as well as the aggregate fit features.
Origin samples are dependent; their spread is NOT divided by sqrt(number of origins).

Candidate and reference backgrounds are computed for BOTH banks. Rankings use
paired reference supports usable in both banks. Supported classes also require
that the background median changes by <=0.05 and the per-size relative class is
the same in both banks. The original 50/80 cuts and complete-size rule are retained.
`origin_width_range` in diagnostics and `median_origin_width_range` on candidates
expose the spread of individual origins; agreement of the two averaged banks does
not prove stability of every origin. No confidence interval or permeability is inferred.
The alternate background is exported as `window_shifted_spectra`, with QGIS style.

Physical box sizes are calculated as L/divisor for the requested support L.
Choose the scale range using the accuracy and resolution of the input map.
Changing that range changes the measured quantity; results from different
profiles must not be read as physical trends over time. No private case-study
data, production counts or geological validation metrics are included here.

An optional `fast` install extra supplies Numba. The identical partition function
has a Python fallback; tests compare it with both compiled execution and an
independent geometric partition. Four spawned worker processes are used only by
the folder runner. Sequential and parallel results are tested for equality.

## Measurement and spatial support

For every candidate, recompute H = alpha(q=0) - alpha(q=2) on centered square
windows of each requested side L, using internal box sizes L/divisor. The contextual
half-width L/2 is not a circular radius. Proximity radii only generate candidate
relations and do not establish hydraulic connection.

H is a partial finite-scale spectral contrast, not the complete spectrum width.
The primary q0 and q2 fits must pass coverage, regression and effective-box checks;
negative spectral ordering is not classified. Include q=0 and q=2 in background
analysis settings. High q alone does not identify permeable structures.

## Comparable reference and descriptive score

Use primary-phase background windows with accepted q0/q2 fits, nonnegative H,
the same L, line density within a factor of two, coverage within 0.1, and no
intersection with the candidate window. Require at least 20 references.

For each evaluable L:

    percentile_L = (number of lower H + 0.5 * number of tied H) / references
    score = 100 * median(percentile_L over evaluable sizes)

Both candidate and reference use the SAME grid convention. The score is an
empirical relative rank, not a probability. References may overlap one another;
window sizes are correlated. This is not a significance test.

The fixed cuts apply to background-relative ranks, not quantiles of the candidate
population. No prescribed fraction of candidates must occupy any class:

1. Low relative contrast: score <= 50 (at or below the reference median).
2. Intermediate relative contrast: 50 < score <= 80.
3. High relative contrast: score > 80.

These are operational descriptive classes; a high class does not establish a
statistically significant anomaly, geological trap or permeability. Identical
candidates receive identical scores/classes. Ties with the reference give 50,
not high contrast. A single extreme window does not dominate a three-size median.

## Rank and supported class rules inherited from v6

`score` remains the descriptive percentile and `relative_class` retains its
50/80 category. Neither establishes effect magnitude or prospectivity.
`evidence_class` is now nullable independently of that rank. It is assigned only
when every requested size has sufficient reference and usable spectra in both
phases, with abs(H1-H2) <= the existing 0.05 sensitivity tolerance. For positive
classes (2/3), median contrast must also exceed median phase difference and the
1e-8 numerical resolution used for spectral ordering. No class is forced to exist.
`class_status` explains incomplete support, grid sensitivity or unresolved effect.
The weighted counterpart has the same rules and its own `_w` fields.

This is a conservative computational eligibility rule, not a new multifractal
estimator or a statistical confidence interval. Missing or unstable evidence is
NULL, never class 1. Raw estimates and ranks are preserved, not corrected by a
percentage, a minimum across phases or a fitted count of desired candidates.

The boundary/origin effect is reduced, not eliminated, in v7 finite-scale spectra: the
uniform-line shifted-origin control still differs from the aligned one. Two
phases do not prove stability under every origin or scale range. The sensitivity
threshold is an explicit methodological convention, not geological calibration.
Background windows overlap; v7 checks both background banks, but neither correlation nor full sampling uncertainty is modeled.
Consequently even an assigned class is only a computationally supported relative
pattern, not a validated trap. Further validation of scale ranges and map accuracy remains
necessary before predictive geological use.

## Geometry corrections (2026-09-26)

Length is split at grid crossings and assigned once by primitive midpoint into
half-open cells. The bounded window assigns its outer upper edge to its final
interior cell. Cell thresholds apply after summing all pieces, not per feature.
Structural orientation integrates each straight primitive by length. Proximity
uses maximal endpoint-connected degree-two chains without snapping or noding
interior crossings; part_a/part_b identify those computational chains, not source
fault IDs. Source participants are still recovered geometrically from the input.
A relation is the nearest approach between disjoint chains; multiple local close
approaches and equidistant corridors are not exhaustively enumerated. It is not
an estimate of the number of geological traps.

## Angles and interpreted order

Intersection angles use distinct local axial tangents, excluding opposite branches
of one axis. Multiway intersections retain all angle pairs. Nearby disconnected
traces retain axial angle separately, not a measured intersection angle.

High angle=1, Late=2, Other=3 remain interpreted priority attributes.
Late is interpreted as transverse, not inferred age. Shared classifications retain
all source memberships. `order_priority` is independent of score and null when
ambiguous. No perpendicularity bonus is applied.

## GIS audit

- `trap_candidates`: class, rank, quality, angles and source-order attributes.
- `candidate_centered_spectra` / `candidate_shifted_spectra`: raw spectra at each node.
- `candidate_evidence`: candidate/size H, background median, contrast, percentile,
  reference IDs and phase diagnostic.
- `candidate_scoring`: formula, version, settings and interpretation.

QGIS default style shows the three contrast classes plus an unclassified fallback.
Tooltips expose score, support and quality. All diagnostics are exported by the GUI
backend; no prepared QGIS project is required.

## Method references and limits

The spectral estimator follows [Chhabra and Jensen (1989)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1327).
Grid partition sensitivity is discussed by [Thiem and Schreiber (2012)](https://arxiv.org/abs/1204.3755).
Neither publication validates the operational class cuts used here or links them
to mineralization. Synthetic tests verify ranking, ties, missing support, separate
quality, identical candidates and uniform-network controls. Geological validation
requires independent observations.


## Zeta integration (v5)

Moving windows now call MUSA's `_zeta_mother_scale` for every support and box size.
The same four exponents, scale floor and reliability threshold selected in the GUI
are passed to background, candidate-centered and shifted analyses. Defaults are
(1,1,1,1), 0.25 and 0.15, respectively.

    zeta = occupancy^a * mass_ratio^b * scale_factor^c * effective_ratio^d
    effective_ratio = exp(Shannon entropy of p) / occupied_boxes
    scale_factor = floor + (1-floor) * log(eps_coarse/eps) / log(eps_coarse/eps_fine)

The moving window supplies the local support formerly supplied by a mother cell.
Mass ratio compares length with the finest box size within the SAME support; it
should be approximately one for conserved line length. Coverage here is box
occupancy, not the observed-AOI area fraction. Nominal possible boxes for divisor
n are n*n when aligned, (n+1)*(n+1) when shifted along both axes. This prevents
shift-induced extra edge boxes from inflating occupancy. Partial-AOI coverage
remains an explicit independent filter. Partial boxes are not area-weighted. V7 averages per-origin zeta and fit features;
residual finite-boundary sensitivity remains. Small occupancy can make the fixed
reliable_min_zeta flag false even for well-resolved synthetic lines; it is an
operational diagnostic, not a calibrated probability of estimator accuracy.

Each window retains canonical `alpha`, `f_alpha`, `dq` and their R2 alongside
`alpha_w`, `f_alpha_w`, `dq_w` and weighted R2. At least three positive-weight
scales are required for `accepted_w`; regression and effective-box checks also
apply. `reliable_w` additionally requires `zeta_mean >= reliable_min_zeta`.
This operational reliability threshold is not a geological confidence probability.

`scale_diagnostics_json` records eps, box counts, conserved mass, entropy, zeta,
and regression features, enabling independent reconstruction of both fits.
The entropy weights belong to the unmodified mass distribution p, not the q escort
distribution. Weights do not change p, q or the measured line geometry.

The backend performs the relative classification TWICE: canonical candidates
against canonical references, and weighted candidates against weighted references.
`score_w`, `evidence_class_w`, `quality_status_w`, `evaluated_sizes_w`,
`score_delta_w` and `class_agreement` expose the comparison. `score` and the default
map remain canonical; a second saved QGIS style, `MUSA_trap_candidates_zeta`, uses
`evidence_class_w` without duplicating features. It is not an automatic replacement
of the canonical estimator. No class or percentile is multiplied by zeta.

`zeta_mean` and `zeta_min` summarize primary-centered weights. `zeta_reliable_sizes`
counts sizes whose q0/q2 weighted fits meet the reliability threshold; spectral
ordering and phase stability remain additional diagnostics. Classification can
still be high with low reliability, explicitly visible in the exported attributes.
Strong concentration may itself reduce the entropy factor: weighting can suppress
an interesting pattern, so comparison with the canonical result is retained.

Zeta does not correct map completeness, establish permeable connectivity, remove
all origin sensitivity, or calibrate the relative 50/80 class cuts.
