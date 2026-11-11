# Cell geometry: squares, hexagons, and grid rotation

Local experiment of November 7, 2026. This exploratory sensitivity study does
not change the engine: MUSA still uses square cells. Hexagonal partitioning is
a prototype in [scripts/grid_geometry](../scripts/grid_geometry), outside the
plugin and API.

## Question

Do hexagonal cells recover Rényi dimensions Dq of a length measure better than
squares? Do they perform better for hexagonally organized networks (120°
junctions, desiccation cracks, columnar joints)? A hexagonal natural pattern
does not imply a hexagonal measurement grid performs better; the latter is
the claim tested here.

## Design

- Point-up hexagonal partition prototype. Every edge lies on n·p = m·a/2, with normals at 0°, 60°, and 120°. Segments are cut at all those lines; each piece is assigned to the center nearest its midpoint. The partition is exact and conserves length to relative tolerance 1e-9 at every scale. Nearest-center assignment agreed with exhaustive search for 20,000 points.
- Equal-area grids (equivalent side eps), matching scales, the same Rényi-entropy estimator, and a line against log(1/eps). Square grids use MUSA's actual partition, musa.mass_partition.
- Each configuration uses a random map rotation and grid origin; both grids receive exactly the same geometry.
- Known-truth cases: the dyadic 65,536-segment cascade (analytical Dq, constructed on a square grid), level-7 Koch (D = log 4/log 3, 60° angles), the cascade with randomly oriented segments, and perturbed-honeycomb/Voronoi polygonal networks (D = 1 below their spacing).
- Public maps without known truth: two Åland maps, three Loviisa maps, FracPaQ map1, HatchFrac, and Hornelen figure 7, using scales declared in the November 2 manifests. Dq standard deviation is measured across 48 configurations.
- q = −4, −2, −1, 0, 1, 2, 4. Paired sign-permutation p values use differences in absolute error.

## Results

Verified archive: MUSA-hex-extended-20261107_195052, retained by the maintainer
(64 configurations per case and averaging across four origins).

| Case | Hexagon RMSE change relative to square, q >= 0 | Observation |
| --- | --- | --- |
| Dyadic cascade | −4% to −11% | p < 0.05 for most q values |
| Isotropic cascade | −3% to −9% | p < 0.05 for D0 and D1 |
| Koch | −5% to −8% | Rarely significant |
| Honeycomb | −1% to −6% for D0–D2; +1% at q = 4 | Consistent (89%–95% of configurations), but small |
| Voronoi | −1% to −8% for D0–D2; +1.5% at q = 4 | Consistent, but small |

On all eight public maps, hexagonal D1 standard deviation fell to 49%–65%
of the square-grid value. D0 fell in seven of eight maps and D2 in eight of
eight. Negative-q results were mixed: improvement in four maps, worsening
by up to 1.33 times in the other four. Absolute D1 standard deviation was
already small (approximately 0.005).

Large errors do not depend on cell shape. D(−4) RMSE reached 1.3 for the cascade
and 0.6 for Koch, Voronoi, and honeycomb with both grids. Cascade D0 bias was
approximately −0.12 for both; polygonal-network bias was +0.06 against D = 1.

## Square-grid rotation

Verified archive: MUSA-rotation-vs-hex-20261107_204652, retained by the maintainer.
All estimators have the same cost: four partitions whose entropy curves are
averaged before fitting one slope.

- Square, four origins: half-step offsets as used by MUSA.
- Square, four rotations: 0°, 22.5°, 45°, and 67.5°, with a random origin for each.
- Hexagon, four origins.
- Hexagon, four rotations: 0°, 15°, 30°, and 45°.

There were 48 configurations per known-truth case and 32 per public map.

| Estimator | D0 RMSE (cascade / isotropic / Voronoi) | Map standard deviation, median relative to square with four origins (D0 / D1 / D2) |
| --- | --- | --- |
| Square, one partition | 0.123 / 0.123 / 0.064 | 1.27 / 2.45 / 3.75 |
| Square, four origins | 0.123 / 0.123 / 0.064 | 1 / 1 / 1 |
| Square, four rotations | 0.120 / 0.120 / 0.064 | 0.37 / 0.92 / 1.83 |
| Hexagon, four origins | 0.114 / 0.114 / 0.059 | 0.32 / 0.30 / 0.35 |
| Hexagon, four rotations | 0.114 / 0.114 / 0.059 | 0.36 / 0.47 / 1.35 |

- Square rotation matches hexagonal D0 stability, but not D0 accuracy (p < 0.02 in all four cases), D1, or D2. At q = 2 and 4, rotations with random origins are even less stable than four structured origins.
- Four-origin hexagons were the most stable estimator on public maps for q >= 0. Absolute D1 standard deviation fell from approximately 0.0025 to 0.0008.
- Accuracy gains against known truth remain a few percentage points. For Koch D(−1), square rotations performed better.
- Design limitation: rotations were combined with random origins rather than structured offsets. Part of their lower stability at q >= 2 may reflect that combination rather than rotation alone.

## Interpretation

- Cell shape is a second-order uncertainty source. Scale range and negative q matter much more.
- Hexagonal gains are not larger for hexagonal networks than for the isotropic cascade. An interpretation in terms of a hexagon's closer approximation to a circle is more consistent with this result than matching the natural pattern's shape.
- Hexagons do not nest: one hexagon does not divide exactly into smaller hexagons. MUSA's mother/child-cell local analysis requires nesting, so a hexagonal grid would apply only to global/support assessment.
- Square rotation does not replace hexagons for D1/D2. A possible use of the gain would be experimental global-only hexagons without changing defaults. Its absolute size gives it lower priority than negative q and null-model calibration.

## Limits

One scale interval per case; equal-area cell sizing; no boundary/partial-coverage
treatment; public maps measure stability, not accuracy. The prototype is not
covered by the repository test suite. None of this establishes geological validity.

## Reproduction

Run from the repository root with a new output folder:

~~~text
python scripts/grid_geometry/run_hex_vs_square.py RESULTS
python scripts/grid_geometry/run_extended.py RESULTS
python scripts/grid_geometry/run_rotation.py RESULTS
~~~

The last two need the prepared extended-suite inputs. Set MUSA_BENCH_DATASETS
to the datasets directory produced by scripts/extended_benchmark_inputs.py.
They require numba.
