# Analytical controls and published maps

Local test of November 2, 2026. Data and results are retained outside the source
and plugin ZIP.

Twenty cases were processed: a uniform line, two finite Cantor approximations
(uniform/binomial weights), three independent reconstructions of Roy's
construction, eight original images from Sahu and Roy's supplement, and six
threshold variants of images 6–8. Each case includes a global assessment and
four fixed windows; each support requests q = −2, −1, 0, 1, 2. This suite ran no
null simulations.

The published originals are BMP images, not vector coordinates. Derived vectors
follow centers of horizontal/vertical pixel runs, with a declared threshold
and explicit geometric union to remove coincident multiplicity. Originals,
hashes, lengths before/after, raster counts, and acceptance decisions are
retained. Gaps are not filled and fractures are not interpreted automatically.

Results use an UNLOCATED plane normalized to width 10000. Software columns
ending in m refer here to model units, not actual locations or measurements
from georeferenced outcrops.

## Results and scope

The line recovered D0 = 0.997335 against 1. Uniform Cantor gave 0.641731 and
binomial Cantor 0.634066 against capacity target log(2)/log(3) = 0.630930.
The report also compares Dq, tau, alpha, and f(alpha) with the analytical
targets of each measure; errors are not replaced by approval indicators.

For original images 6, 7, and 8 vectorized at threshold 128, D0 was 1.592721,
1.594612, and 1.593810 against theoretical limit log(3)/log(2) = 1.584963.
Images 1–5 lack a sufficient interval under the declared criteria. Threshold
variants expose rasterization sensitivity and are not original coordinates.
Roy's theoretical target is compared only with D0; no exact targets are
assigned to its other Dq values.

Scales are fixed before fitting using resolution, the lower cutoff of the
finite construction, and an upper limit of one quarter of domain width.
Each window also applies its own upper limit. Compatibility over that range
does not prove fractality or guarantee accuracy: binomial Cantor alpha at
q = −1 has an absolute error of approximately 0.137. Rejected q values and
reasons remain available. This is neither geological validation nor a general
calibration of the statistical test.

## Sources

- Sahu, A. K., and Roy, A. (2020), [Clustering, Connectivity and Flow Responses of Deterministic Fractal-Fracture Networks](https://adgeo.copernicus.org/articles/54/149/2020/), Adv. Geosci. 54, 149–156. The article declares CC BY 4.0. Its complete [original supplement](https://adgeo.copernicus.org/articles/54/149/2020/adgeo-54-149-2020-supplement.zip) is retained with attribution and identified derivatives.
- Zhu and colleagues, [dataset 10.4121/14464893](https://doi.org/10.4121/14464893): public metadata indicate CC BY-NC 4.0. Coordinate downloads remained unavailable after timeout/502/504 responses; only metadata and attempts were archived. No analysis of its 80 natural outcrops is claimed.

## Reproduction and archive

Run from the repository root. Originals download to data/benchmarks (or
MUSA_BENCHMARK_DATA); RESULTS must be a new folder:

~~~text
python scripts/fetch_fractal_benchmarks.py --root data/benchmarks
python scripts/run_author_benchmarks.py --output RESULTS
python scripts/package_author_benchmarks.py RESULTS
scripts/run_qgis_python.cmd scripts/qgis_author_benchmarks.py RESULTS dist/qgis/VALIDATED_PLUGIN.zip
~~~

For the last command, set MUSA_QGIS_ROOT to an existing QGIS installation.
If Zhu is inaccessible, the first command retains Sahu/Roy's verified supplement
and exits with an explicit error; subsequent commands use the available
supplement without fabricating Zhu data.

Verified archive: MUSA-author-benchmarks-20261102_135150, retained by the
maintainer. It includes a combined GeoPackage, per-case files, a relative-path
QGIS project, global/window results, spectral caches, analytical comparisons,
originals, and attribution. Separate case files avoid a shared-GeoPackage
subset query that failed in that QGIS provider; geometry was not changed to
resolve it.

The project was created and reopened in QGIS 3.44.12: 60 valid layers, an
accepted model CRS, and the plugin viewer loading a completed run. Isolated
temporary state was used without changing the normal user profile. This checks
native loading/visualization, not repetition of the entire suite through Processing.

Generator tests check Roy's construction, an ungeoreferenced CRS, vectorization
of a controlled pattern, and analytical references. Data were not published
or added to the installable plugin package in that campaign.
