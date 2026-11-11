# Scope of MUSA's mathematical validation

Review of November 2, 2026, covering MUSA 1.1.0. This is neither peer review
nor mathematical certification. Later dated sections retain their own scope.

## Current calculations and checks

MUSA analyzes a lineament-length measure over a spatial 2D domain. It calculates
generalized dimensions Dq and the direct Chhabra–Jensen spectrum, alpha and
f(alpha), at multiple scales. Changing q studies the relative weight of dense
and sparse regions; it adds neither spatial dimensions nor independent variables.

Moving windows separate window size, center spacing, and internal scales.
Checks cover coverage, box counts, weight dominance, length conservation,
and Dq/alpha/f(alpha) fits. Constant fits are not evidence of scaling.
Rejections and reasons remain available. The optional 16-origin ensemble and
a second phase examine grid bias. Overlapping windows and origins are
dependent, not independent statistical replicates. Zeta and its weighted
regression are operational diagnostics separate from canonical estimates.

Global analysis adds per-scale diagnostics, jackknife, and optional bootstrap.
An interval's availability does not establish calibrated coverage for a
dependent spatial network; a slope p value is not a test of fractality or
multifractality.

## Computational controls that actually run the engine

- tests/test_origin_ensemble.py compares partitions with an independent reference and checks length conservation after geometry translation.
- A uniform line is compared with Dq approximately 1 and a narrow spectrum, without forcing that result.
- Binomial Cantor is compared with analytical Dq/alpha over the finite interval and two grid phases.
- tests/test_numerical_bias.py checks boundaries, trace fragmentation, orientation, length conservation, and classification sensitivity.

These are implementation controls for specific cases. They do not establish
fractal scaling in every real map. Their finite traces are not mathematical
fractals in the infinite limit.

The historical run_synthetic_validation API in src/musa/synthetic.py generates
preset profiles and an illustrative table. It neither constructs geometry nor
calls the engine. Its pass/fail fields and table test do not validate
multifractal calculation. The function documentation explicitly states this scope.

## Implemented assessment and outstanding scientific validation

An integrated experimental assessment is described in
[SCALING_SUPPORT.md](SCALING_SUPPORT.md). It evaluates generalized Rényi
dimensions Dq; it is not a universally calibrated fractality/multifractality
test. High R², several accepted q values, or a wide spectrum are insufficient.
A finite set of straight segments has geometric dimension 1 at sufficiently
small scales; larger dimensions estimated from maps describe organization
over a scale interval, not an established fractal limit.

The implemented assessment includes:

1. Declaring a resolvable interval from mapping precision, domain size, and observed support, recording its span in orders of magnitude.
2. Comparing a log–log line with curvature and slope changes using criteria fixed before interval selection and controls on model selection.
3. Evaluating sensitivity to omitted scales, origins, window sizes, and observation resolution without treating overlapping windows as independent.
4. Testing D0−D2 against conditional trace translations preserving supplied shapes, lengths, and orientations. Holm adjusts the complete support family; q values are not additional independent tests. Local density and crossings change, so this tests spatial heterogeneity under that model, not proof of multifractality.
5. Reporting compatible evidence, contrary evidence, and insufficient information separately, with interval/sensitivity rather than a universal label.

States use explicit operational thresholds. A pilot with 24 null-generated
datasets and 39 replicates each produced one rejection at 0.05; its 95%
binomial interval was approximately 0.0011–0.2112. This does not certify a
general 5% error rate. Extensive calibration, power assessment, and independent
validation across domains, inventories, and sampling designs remain necessary.
The user must justify mapping resolution, interval, and null-model suitability.
Joint multifractals of multiple variables are not implemented. Rényi dimensions
are implemented and are not additional spatial dimensions.

## Extended evidence of November 2

The geometry core's 65,536-segment dyadic-cascade check obtained maximum
Dq/tau/alpha/f(alpha) error approximately 2.09 × 10⁻¹⁴ for an aligned origin
and finite scales. The extended suite completed 67 processable cases and 450
supports, retaining insufficiencies and rejections. These are not 67 independent
outcrops or certification of general geological accuracy. Four selected masks
were empty; GeoCrack images and Zhu coordinates are not counted as analyzed.

A periodic-grid control was compatible over an initial interval and rejected
over an exploratory extended interval without changing criteria. This documents
a limitation of interpreting finite slopes as fractality. See
[extended validation](EXTENDED_BENCHMARKS.md), [theory](theory.md), and
[spectral sources](SPECTRA.md).

## Cell-geometry sensitivity (November 7)

An exploratory experiment compared equal-area squares/hexagons against known
truth and eight public maps. Cell shape was a second-order uncertainty source:
q >= 0 RMSE changed by a few percentage points, without correcting large
negative-q errors affecting both grids. The engine was unchanged. See
[cell geometry](GRID_GEOMETRY.md).

## Negative q (November 7)

For four known-truth measures and 48 grid configurations, D(q<0) errors reached
1.33 for D(−4). Neither probability floors, per-cell thresholds, scale trimming,
nor origin averaging corrected these without changing the measure. The floor
also drives negative-order dimensions toward D0 by construction. Treat D(q<0)
as a sensitivity indicator. See [negative q](NEGATIVE_Q.md).

## References

- [Chhabra and Jensen (1989), direct spectrum](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1327).
- [Roy and colleagues (2007), fracture-network box counting and scaling range](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2006JB004582).
- [Gonzato and colleagues (1998), practical dimension/range estimation problems](https://academic.oup.com/gji/article/132/2/275/671597).
