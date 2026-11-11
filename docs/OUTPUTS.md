# Outputs, states, and result interpretation

The outputs field of run_manifest.json is the inventory for each run. Files
depend on enabled options; not every run produces every product.

execute_analysis writes a folder, with no automatic ZIP. Preserve its complete
structure when sharing. The legacy package_run_output helper only bundles
top-level files; it is not a recursive backup of the current workflow. Do not
assume it includes subfolders, original inputs, or everything needed for reproduction.

## Start reading a run

1. Check status in run_manifest.json. complete means execution finished, not that every q/window is supported.
2. Read analysis_report.csv for descriptive analysis and scaling_support.json/CSV for the independent assessment, if requested.
3. Select a source, support, and estimator in spectrum_summary.csv or the QGIS viewer. Check usable q values before interpreting a peak or spectral width.
4. For local maps, check coverage, scale, quality, and product definition. Keep structural intensity, reliability, and spectra separate.

## Main inventory

| Product | When available | Interpretation |
| --- | --- | --- |
| recipe.json | execute_analysis workflow | Reusable parameters; no input files |
| run_manifest.json | Shared workflow | Version, status, available provenance, outputs, and hashes |
| analysis_report.csv | Completed global fit | Summaries, accepted/rejected q values, and descriptive quality |
| analysis_scale_diagnostics.csv | Shared workflow | Integrands and scale diagnostics for the global fit |
| spectrum_fit_summary.csv | Shared workflow | Descriptive quadratic check of the global spectrum |
| spectrum_curves.sqlite | Spectral products | Index by source, support, and estimator; points and quality |
| spectrum_summary.csv | Spectral products | One row per series; singularity references, usable q values, identities |
| scaling_support.json / scaling_support.csv | Requested assessment | Interval, exclusions, origins, criteria, observables, reasons, and null test |
| monofractal_cells.csv / multifractal_cells.csv | local=True | Measures and integrands per child cell |
| monofractal_mother_agg.csv / multifractal_mother_agg.csv | local=True | Results per mother cell, q, and available estimator |
| musa_mother_cells.gpkg | gis=True and mother-cell products | Spatial workflow layers; actual layers depend on options |
| moving_windows.csv / moving_nodes.csv | moving=True | Moving supports and exact topology |
| musa_moving_windows.gpkg | moving=True and gis=True | Windows, candidates/controls, and available spectral tables |

Global/local figure names are listed in outputs; some include q. Bootstrap
and sensitivity options can add columns/files. Experimental postprocessors
have separate contracts in [nodes](node_products.md) and [candidates](candidate_scoring.md).

## Four different kinds of state

| Field/context | Meaning |
| --- | --- |
| Run status | running, complete, failed, or cancelled; execution state |
| Descriptive accepted | Quality under that path's filter; not a formal test of fractality |
| reliable / reliable_w | Local quality/zeta rule of its estimator; not geological-validity probability |
| Assessment status | compatible_finite_range, not_supported, or insufficient_information for the declared support/observable |

The assessment can retain a calculated Dq with status=not_supported: the value
is kept for audit, not promoted to a supported estimate. With insufficient
information, dimension can be null; never replace it with zero. tau, alpha,
and f_alpha have their own states under observables. A q value can have a
compatible Dq and insufficient alpha.

## Spectral fields and units

| Field | Meaning |
| --- | --- |
| q | Moment order; changes mass emphasis, not spatial dimensionality |
| dq / dimension | Rényi-entropy slope over the interval; check source and state |
| tau / tau_w | Mass exponent for the corresponding canonical/weighted estimate |
| alpha / f_alpha | Canonical singularity and spectral-dimension estimates |
| alpha_w / f_alpha_w | Separate local zeta-weighted variant |
| alpha_q0 | Usable alpha at q=0; no substitution from a neighboring q |
| observed_peak_alpha | Alpha at observed maximum f; check ties and endpoints |
| fit_peak_alpha | Valid descriptive quadratic vertex; may be absent |
| delta_alpha | Alpha range over usable points; no extrapolation to untested q |
| measure_sum_m | Local length recorded at the finest scale for metric lines; not a multifractal dimension |
| zeta_mean | Operational weighting summary; neither connectivity nor favorability |
| coverage | Observed fraction of the nominal support, as defined by the product |

Dq, tau, alpha, f(alpha), q, R², and zeta are dimensionless. Coordinates,
lengths, window sides, and scales of an ordinary GIS run are meters in the
projected CRS. UNLOCATED benchmarks use explicitly declared model/pixel units;
their m suffixes do not establish real geographic measurements. Normalized-point
inputs use the scale of that normalization.

## Sources and joins

analysis and assessment are different sources; canonical and zeta are different
estimators. The global support is not the average of windows. Identify a series
by source, support_id, and estimator; for windows add center_id and window_m as
available. Do not join only on q or coordinates.

The moving GeoPackage's window_spectrum_summary table retains nonspatial
summaries when exported. The SQLite index contains points for reconstructing
the four curves. The viewer loads saved selections; changing windows does not
repeat the analysis.

## Traceability and failures

A workflow can write valid scaling_support.json and subsequently fail its
global fit. The whole run remains failed and must not be opened as complete.
For an independent assessment without that global filter, use
assess_lineament_scaling or musa:scaling_support.

The manifest records product hashes and transformed-geometry hashes if supplied
by the host. A recipe without inputs cannot reproduce a map: retain the data,
CRS, selection, preprocessing, version, and original licenses.

The [spectral guide](SPECTRA.md) covers ties, peak criteria, and index queries.
[Theory](theory.md) explains formulas and estimator differences.
