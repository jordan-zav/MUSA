# Interpreting negative q

Local evaluation of November 7, 2026; no changes to the engine or defaults.
Complete evidence is retained in the maintainer's archive
MUSA-negq-20261107_204932 (report, results, protocol with script hash, curves,
and per-scale diagnostics).

## Summary

With MUSA's square partition, q < 0 dimensions do not recover known truth for
a multifractal measure, although D0 through D4 are recovered with small errors.
No tested remedy corrects this without changing the measure. Therefore,
**D(q<0) must not be interpreted as the dimension of the original length
measure without independent evidence of a resolved, stable regime**.

## Design

- Four known-truth cases: a dyadic cascade of 65,536 segments (analytical Dq), the cascade with randomly oriented segments, level-7 Koch (D = log 4/log 3), and a Voronoi network (D = 1 below spacing). Generators are in [scripts/grid_geometry](../scripts/grid_geometry).
- Forty-eight map-rotation/grid-origin configurations, identical across remedies. Actual musa.mass_partition and q = −4, −2, −1, 0, 1, 2, 4.
- Remedies fixed before calculating errors: six negative_q_floor_fraction values; per-cell length thresholds of 0.01, 0.05, and 0.1 eps; three scale-range trims; four/nine-origin averaging; and restricted-range Chhabra–Jensen as a control. No parameter was selected by inspecting truth.
- Descriptive recovery criterion: 48/48 finite estimates, RMSE ≤0.10, absolute bias ≤0.05, and standard deviation ≤0.10. This is a tolerance of this experiment, not a MUSA threshold.

## Results

| Case | Baseline RMSE for D(−4), D(−2), D(−1) | Remedies meeting the q < 0 criterion |
| --- | --- | --- |
| Dyadic cascade | 1.33 / 1.12 / 0.79 | None |
| Isotropic cascade | 1.33 / 1.12 / 0.79 | None |
| Koch | 0.67 / 0.36 / 0.08 | Floors >=0.01 at all three q; baseline only at q = −1 |
| Voronoi | 0.73 / 0.46 / 0.12 | Relative thresholds at q = −4 and −2; none at q = −1 |

- In every case, the lowest-mass 1% of cells contribute 99.8%–100% of the q = −4 sum. Negative moments depend almost entirely on nearly empty cells.
- For Voronoi, a threshold removing only 0.003% of length recovers D(−4). There, the small-mass tail is a grid-cutting artifact.
- For the cascades, the same thresholds remove 53%–94% of mass: rare mass is signal in a multifractal measure. No automatic procedure distinguishes the two situations.
- Origin averaging reduces variability but not bias: cascade D(−4) RMSE increases from 1.33 to 1.39 with nine origins.
- Square and hexagonal cells fail similarly ([GRID_GEOMETRY.md](GRID_GEOMETRY.md)).

## The probability floor drives negative-order dimensions toward D0

The floor in [theory](theory.md), section 8, imposes minimum probability c/N for
q < 0, where c = min(0.5, η·max(|q|,1)) and N is the number of occupied boxes.
After renormalization, p′ ≥ c/[N(1+c)]. Convexity and this bound give:

~~~text
ln N ≤ Hq(p′) ≤ ln N + [q/(1−q)]·ln[c/(1+c)]
~~~

Hq − ln N is bounded by a constant independent of eps. If a scaling regime
exists, the regularized slope therefore tends to D0 for any η > 0 and q < 0.
Finite-range slopes can differ, but the floor cannot preserve a negative-order
spectrum distinct from D0. Numerical success for monofractal Koch, where every
Dq equals D0, is not evidence of recovery for a multifractal measure. This
derivation belongs to the evaluation and was checked separately during review.

## Recommendations

1. Report q < 0 Dq only as sensitivity descriptors, not dimensions of the original measure.
2. Retain the floor and threshold as documented measure-changing options, off by default. If used, also report the untreated path.
3. Proposed diagnostic, not implemented: measure changes in D(q<0) after removing tiny fractions of length. A large change after minimal loss indicates that negative q is not interpretable on that map.

## Limits

One realization per generator; square grid without a study mask; no noise,
censoring, or digitized tracing; bootstrap intervals conditional on these
realizations; OLS entropy regressions outside the interface. This validates no
parameter for geological data.

## Consulted sources

- [Chhabra and Jensen (1989)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1327): direct spectrum.
- [De Bartolo, Gaudio, and Gabriele (2004)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2003WR002760): nearly empty boxes at negative q and the sandbox method.
- [Thiem and Schreiber (2012)](https://arxiv.org/abs/1204.3755): partition schemes and origin averaging.
