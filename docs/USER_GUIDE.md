# MUSA 1.2.0 user guide

MUSA measures the distribution of line length over square cells in a 2D
observation domain. It provides descriptive global/local spectra and a separate
finite-range scaling assessment. Those paths have different acceptance rules.
They do not establish permeability, geological favorability, 3D connectivity,
or a universal classification of fractality.

This English guide adapts the interface workflow of the
[historical Spanish illustrated guide](USER_GUIDE.es.md) and documents 1.2.0
options. Historical screenshots describe an earlier example; the executable
[tutorial](TUTORIAL.md) instead uses generated synthetic data and needs no
permission-dependent field dataset. Instructions and option names are in English.

## 1. Install and choose a calculation path

See [INSTALLATION.md](INSTALLATION.md) for Python dependencies and the QGIS ZIP.
Python requires version >=3.10; ordinary line/GIS use needs the gis extra.
The plugin uses NumPy, SciPy, Shapely, and Matplotlib in QGIS Python. Installing
them in another Python does not change QGIS. MUSA does not install dependencies
automatically. QGIS 3.44.12 was checked; the metadata range 3.34–3.99 is not a
test matrix for all versions or systems.

In QGIS, enable the plugin and open Vector > MUSA > MUSA Workbench. For the
independent assessment, open Processing Toolbox > MUSA > Lineament analysis >
Assess Renyi scaling support (experimental), identifier musa:scaling_support.

| Path | Use | Important behavior |
| --- | --- | --- |
| MUSA.run_analysis | Descriptive global spectrum | Requires at least two q values passing the triple R² filter |
| execute_analysis / Workbench | Descriptive analysis plus selected products | Always runs the global stage; a later/global failure can leave partial assessment files |
| assess_lineament_scaling / musa:scaling_support | Independent finite-range assessment and optional spatial test | Retains every requested q and its state; does not require the descriptive global filter |

For data whose descriptive spectrum fails, use the independent path. Lowering
quality thresholds after inspecting a result is not an automatic remedy.

## 2. Prepare inputs

| Input | Requirement |
| --- | --- |
| Line layer | 2D linework with positive length, valid geometry, and the correct source CRS |
| Observation polygon | Valid Polygon/MultiPolygon with positive area, representing the area actually examined; holes and clipping matter |
| Analysis CRS | Projected coordinates in meters, appropriate to the real study area |
| Resolution | Positive declared observation/mapping resolution, in the same units as box sizes |
| Scales | Explicit positive distinct box sides selected before fitting; the assessment accepts at most 64 |
| q values | Distinct finite values in [−100,100]; at most 401; include 0 and 2 for the relocation contrast |

Do not replace a mapped observation domain with an arbitrary rectangle merely
to improve results. A CRS label does not reproject coordinates. In Python,
MUSA.from_line_geometries receives already projected Shapely geometry; the
caller is responsible for CRS/units. QGIS transforms the supplied layers into
the chosen analysis CRS before the task starts.

Harmonize duplicate/coincident traces and record the effect on length.
Independent assessment rejects coincident multiplicity; it does not silently
dissolve it. Descriptive preparation and moving windows have different
contracts, described in [theory](theory.md). If a geometric union creates noded
parts, the relocation model preserves those parts rather than recovering
interpreted original fracture identities.

In Workbench, **Use selected lines only** uses the current line selection;
the boundary uses all polygon features. Temporary layers and unsaved edits
are captured. Record selections as part of provenance. For public image/model
benchmarks, retain declared pixel/model units; an m suffix is not evidence of
physical georeferencing. The tutorial's custom metric CRS is explicitly UNLOCATED.

## 3. Analysis and Quality tabs

Select **Lineaments**, **Boundary**, and **Analysis CRS**. **Mother cell** is
the mother-cell side; **Internal divisors** give child sizes as mother side /
divisor. At least four distinct integer divisors >=2 are required. Check the
finest scale against mapping resolution; four descriptive scales do not meet
the independent assessment's default eight-scale requirement.

Choose an existing output parent with **Browse**. Workbench creates a new
run subfolder. **Load spatial results into QGIS** loads spatial outputs on
completion. **Save recipe** and **Load recipe** preserve parameters, not input data.

The following are RunConfig defaults, not recommended geological values:

| Fields | Defaults | Meaning |
| --- | --- | --- |
| mother_cell_m; divisors | 4000; (2,4,6,8,16) | Mother/child-cell scales |
| q_min; q_max; q_step | −4; 4; 1 | Moment orders, not spatial dimensions |
| threshold_m | 0.01 | Descriptive per-box length threshold; changes the retained measure |
| min_r2 | 0.9 | Strict descriptive R² filter for Dq, alpha, and f_alpha |
| local; structural; network | True; True; False | Requested local/structural/network stages |
| plots; gis | True; True | Figures and GIS exports |
| bootstrap_iterations; local_bootstrap_iterations | 0; 0 | Off by default; accepted range 0–10000 |
| bootstrap_ci; seed | 0.95; 42 | Bootstrap confidence level and reproducible seed |
| negative_q_floor_fraction | 0 | Off; positive values alter the negative-q measure |
| reliable_min_zeta | 0.15 | Operational local quality threshold |
| zeta_exponents; zeta_scale_floor | (1,1,1,1); 0.25 | Occupancy, mass, scale, and entropy-balance factors |
| zeta_sensitivity | False | Optional weighting sensitivity |
| moving | False | Moving-window stage |
| window_sizes_m; window_step_m | (2000,4000,8000); 1000 | Window sides and center spacing |
| moving_divisors; origin_ensemble | (2,4,8,16); False | Internal scales; one origin unless the 16-origin option is enabled |
| proximity_radii_m | () | Off; optional exploratory search radii |
| scaling_support | False | Independent assessment within the shared workflow |
| scaling_resolution_m; scaling_scales_m | 0; () | Must supply a positive resolution when enabled; explicitly declare scales for reproducible use |
| scaling_null_replicates; scaling_window_limit | 0; 25 | Null off; limit on assessed windows, allowed 1–1000 |
| renyi_order_policy | legacy_block | Shared assessment order policy |
| scaling_null_tail | upper | Shared-workflow name for ScalingOptions.null_tail |
| scaling_coarse_trim_min_effective_q2 | 0 | Shared-workflow name for coarse-end trimming |

Bootstrap and zeta do not correct mapping uncertainty. Zeta summarizes
operational numerical support, not permeability or geological-validity
probability. Keep canonical and zeta-weighted spectra separate. Negative-q
regularization changes the measure and must be compared with the untreated
path; see [NEGATIVE_Q.md](NEGATIVE_Q.md).

## 4. All independent-assessment options

ScalingOptions is the complete Python configuration for the independent
assessment. Only a subset of its fit thresholds is exposed in Processing or
Workbench; use the Python API for the remaining options. Default thresholds
are operational criteria, not universally calibrated geological values.

| ScalingOptions field | Default | Validation and effect |
| --- | --- | --- |
| resolution_m | Required | Positive finite observation resolution; smaller boxes are excluded |
| min_scales | 8 | Integer 8–64; minimum retained scale count |
| min_decades | 1.0 | Positive minimum log10(maximum/minimum) span |
| min_effective_boxes | 2.0 | At least 2; minimum 1/sum(mu²) over scales/origins for the assessed q |
| max_box_fraction | 0.25 | In (0,1]; boxes above this fraction of the shorter domain side are excluded |
| min_coverage | 0.8 | In (0,1]; observed area / supplied nominal area |
| min_r2 | 0.98 | In [0,1); minimum linear-fit R²; distinct from descriptive min_r2 |
| slope_tolerance | 0.10 | Positive; scale/origin slope variation and finite-range/order tolerances |
| curvature_effect | 0.03 | Positive threshold for CV-RMSE gain divided by log-scale span |
| cv_ratio | 0.75 | In (0,1); alternative/linear predictive-RMSE ratio; both gain and ratio conditions must pass to flag an alternative |
| null_replicates | 0 | Off, or an integer 19–9999; requested relocations |
| seed | 42 | Nonnegative integer; controls relocation random numbers |
| max_placement_attempts | 1000 | Positive integer; maximum attempted placements per trace |
| renyi_order_policy | legacy_block | legacy_block or inform_q0_q2; the latter retains q0/q2 order warnings without that order veto, while other fit/support gates still apply |
| null_tail | upper | upper or two_sided for the D0−D2 Monte Carlo contrast |
| coarse_trim_min_effective_q2 | 0.0 | Off, or >=1; observed-map coarse-end trimming using the minimum effective q=2 boxes over four origins |

Before fitting, the tool excludes unresolved/oversized boxes. With trimming
enabled, it removes scales from the coarse end of the **observed** support
before any relocation until the q=2 threshold is met. The retained scales are
then fixed for all replicates. It does not search for the interval with the
best R². Removed scales and effective counts remain in scale_trimming. Less
than one decade after trimming prevents the null test, with status
coarse_scale_trimming_below_one_decade.

For the article policy use renyi_order_policy=inform_q0_q2,
null_tail=two_sided, and coarse_trim_min_effective_q2=4. These differ from the
backward-compatible defaults. The tutorial also declares resolution, scales,
seed, and replicate count rather than hiding them.

The assessment averages curves over four fixed shifted origins, fits against
ln(1/box size), compares linear/quadratic/segmented predictions, and retains
scale/origin sensitivity. Segmented breakpoints are reselected within each
training fold. It applies no zeta or negative-q floor.

## 5. Conditional trace-relocation test

The statistic is T = D0−D2. Both q=0 and q=2 must have compatible finite-range
support. The model translates supplied clipped trace shapes independently
and uniformly among feasible placements in the polygon. It retains count,
shape, length, orientation, and total mass, while changing positions, crossings,
and spatial dependence. It neither simulates new orientations nor reconstructs
unobserved fractures or boundary censoring.

The upper-tail p is (1 + count(T_sim >= T_obs))/(B+1). The two-sided p is
min(1, 2 min(p_upper,p_lower)), with ties counted against rejection in both
tails. Minimum raw p is 1/(B+1) or 2/(B+1), respectively. At B=999 the two-sided
minimum is 0.002. Choosing upper alone can miss departures below the null.

write_scaling_reports applies Holm over every requested support, including
untestable supports conservatively as p=1. There is one contrast per support;
repeated CSV p values beside q rows are not independent tests. For m supports,
the first possible Holm rejection at 0.05 requires 2m/(B+1) <=0.05 for a
two-sided test. The output records inadequate Monte Carlo resolution.

No simulation is selectively discarded until a fit succeeds. Failed placement,
insufficient simulated support, a degenerate null, or unsupported observed
q0/q2 yields no p value. null_replicates=0 disables the test. Missing p is not
p=1 and is not evidence of homogeneity. Rejection concerns this conditional
placement model, not proof of multifractality.

## 6. Moving windows and planar relationships

In **Moving windows**, enable analysis and declare sides, center spacing, and
internal divisors. Reducing spacing increases overlap rather than data
resolution. The optional ensemble uses 16 origins; default is one. Windows
are dependent and should not be randomly divided into training/test sets.

I/Y/X/complex nodes describe planar ends/degrees. No snapping or 3D hydraulic
connection is inferred. Optional radius-based relations do not modify traces,
join components, or turn proximity into a geological connection. Read
[moving_windows.md](moving_windows.md), [node_products.md](node_products.md),
and [candidate_scoring.md](candidate_scoring.md) for their separate contracts.

## 7. Run, cancel, and recognize abstention

**Run MUSA** starts the task. **Cancel** requests cooperative cancellation;
some stages respond between operations. Failed/cancelled runs can retain
partial files and must not be treated as completed. Analysis complete or
run_manifest.json status=complete describes execution, not scientific support.

| Assessment state | Expected interpretation |
| --- | --- |
| compatible_finite_range | Operational criteria met over the declared interval |
| not_supported | Enough observations, but fit/stability/shape criteria failed |
| insufficient_information | Inadequate coverage, resolution, span, scales, or effective support |

For example, 66.7% observed window area fails a default 80% coverage requirement.
This can leave dimensions null while other windows remain usable. It is
neither dimension zero nor engine failure. Do not lower the threshold merely
to obtain a curve. Invalid CRS/configuration/geometry can instead raise an
input error; that is distinct from a scientifically insufficient support.

## 8. Read and export results

In **Results > Spectra**, choose domain/calculation, center, size, and estimator.
analysis and assessment identify different sources; canonical and zeta identify
different estimators. The initial center selection favors available usable
points, not a scientifically preferred location; other centers remain accessible.

**Chart** selects Dq, tau(q), alpha(q), f(alpha), or four panels. Each curve
uses its own observable state. Unsupported calculated values appear gray;
a dash denotes absence, never zero. Check **Reason** and scroll through all
q values. Compatible Dq alone does not validate the whole spectrum.

Alpha at q=0, the observed maximum of f(alpha), and a fitted quadratic vertex
are different references. A fitted peak needs at least three suitable points
and further checks; exactly three points remain descriptive interpolation.
With two usable q values, do not claim a characterized spectral peak.
Unavailable is an expected result when requirements fail.

Click a spectrum for an enlarged view with zoom/pan/reset/save. Closing it
returns to the panel without rerunning analysis. **Export selected curves**
saves PNG or SVG; SVG retains vector text/lines. Verify source, support,
and estimator before export.

**Results > Figures** displays saved figures. Click a preview to enlarge it;
use Zoom +, Zoom −, Fit, Actual pixels, and dragging. Enlarging an old raster
does not increase its resolution. Results has outer vertical scrolling, while
the values table and **Run details** have their own scrolling. Scrolling over
plots/selectors does not intentionally change the selected center.

**Run details** recovers status, version, UTC dates, provenance, configuration,
and files from the manifest. Live progress is shown only when available for
the active run; a nonexistent historical progress log is not reconstructed.
**Open completed run** opens the folder containing run_manifest.json without
recalculation or loading another copy of spatial layers. **Open output folder**
opens the results location.

## 9. Files, fields, and sharing

See [OUTPUTS.md](OUTPUTS.md) for the complete output dictionary. Descriptive
runs can contain analysis_report.csv, local/moving tables, GeoPackages,
figures, recipe.json, run_manifest.json, spectrum_summary.csv, and
spectrum_curves.sqlite, depending on enabled products. Independent assessment
writes scaling_support.json/CSV and spectral products; Processing additionally
writes its run manifest. The standalone Python tutorial explicitly writes its
own protocol, recipe, inputs, and summary.

The assessment JSON uses supports; each support contains q_results, observables,
reasons, requested/used/excluded scales, margins, and null. Important CSV fields
include support_id, q, status, dimension, tau, alpha, f_alpha, their separate
states, null_status, null_p, and null_p_holm. Join by source/support_id/estimator,
plus center_id/window_m where appropriate, rather than q or coordinates alone.

Dq, tau, alpha, f(alpha), q, R², and zeta are dimensionless. Ordinary GIS
coordinates, lengths, window sides, and scales are projected meters. Retain
explicit pixel/model-unit declarations for unlocated benchmarks.

Save the QGIS project and input layers. A recipe stores parameters, not data.
Preserve the full output tree and input provenance/licenses. The workflow
does not automatically ZIP results; the installable plugin ZIP is not a
results archive. Layers may have multiple rows per q/window and default q=2
symbology: check filters and window size before comparing them.

## 10. Troubleshooting and interpretation checklist

- MUSA missing: enable the plugin and reopen Vector > MUSA > MUSA Workbench.
- Cannot start: check lines, polygon, metric CRS, parameters, and existing output parent.
- CRS error: correct the actual source CRS before reprojection; assigning an EPSG label does not fix coordinates.
- Fewer than two descriptive q values accepted: examine scales, resolution, and geometry; use independent assessment rather than automatically weakening filters.
- Empty window: check coverage, line presence, and resolution in Reason.
- No fitted peak: examine usable q count and fit conditions; do not extrapolate a maximum.
- Long details/table or small panel: use inner/outer scrolling as appropriate.
- Small figure: enlarge it; export selectable curves to SVG.
- No relocation p: read null.status and retained interval; do not replace an abstention with a numerical decision.

Before interpretation, confirm units/domain, record resolution/scales, inspect
usable q values, retain rejections/missing values, distinguish canonical/zeta/
assessment products, and preserve inputs/recipes/results. Interface checks
and numerical tests do not replace external scientific validation. See
[theory](theory.md), [validation scope](SCALING_VALIDATION_STATUS.md), and
[references](references.md).
