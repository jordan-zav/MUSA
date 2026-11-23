# MUSA 1.3.0 user guide

MUSA measures the distribution of line length over square cells in a 2D
observation domain. It provides descriptive global/local spectra and a separate
finite-range scaling assessment. Those paths have different acceptance rules.
They do not establish permeability, geological favorability, 3D connectivity,
or a universal classification of fractality.

The illustrated walkthrough below uses the current interface and a synthetic fracture network in unlocated model metres. [Español](USER_GUIDE.es.md), [Learn](KNOWLEDGE_BASE.md), and the [workflow map](WORKFLOW.md) describe the same execution. The English controls and the bilingual learning/comparison blocks retain their own language.

## 1. Install and choose a calculation path

See [INSTALLATION.md](INSTALLATION.md) for Python dependencies and the QGIS ZIP.
Python requires version >=3.10; ordinary line/GIS use needs the gis extra.
The plugin uses NumPy, SciPy, Shapely, and Matplotlib in QGIS Python. Installing
them in another Python does not change QGIS. MUSA does not install dependencies
automatically. QGIS 3.44.12 was checked; the metadata range 3.34–3.99 is not a
test matrix for all versions or systems.

In QGIS, enable the plugin and open Vector > MUSA > MUSA Workbench. For the
independent assessment, open Processing Toolbox > MUSA > Lineament analysis >
Assess Renyi scaling support, identifier musa:scaling_support.

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
| mother_cell_m; divisors | 4000; (2,3,4,5,6,8,10,12,16,24,32) | Twelve mother/child-cell scales, all relative to mother size |
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
| scaling_support | True | Scaling diagnostic included by default |
| scaling_resolution_m; scaling_scales_m | 0; () | No assumed observation resolution: enter a positive source-specific value before running; empty scales use the relative analysis scales |
| scaling_null_replicates; scaling_window_limit | 0; 25 | Null off; limit on assessed windows, allowed 1–1000 |
| renyi_order_policy | legacy_block | Shared assessment order policy |
| scaling_null_tail | upper | Shared-workflow name for ScalingOptions.null_tail |
| scaling_coarse_trim_min_effective_q2 | 0 | Shared-workflow name for coarse-end trimming |

The panel and RunConfig enable the scaling diagnostic for new analyses. A new
configuration is incomplete until observation resolution is entered under
Quality; zero is a prompt, not an inferred or hidden resolution. Processing
analysis also requires its Observation resolution parameter. Use the source
map's measurement or mapping resolution, not the CRS units or a universal
metre value. Explicit settings in existing recipes remain unchanged.

Monte Carlo is a separate unchecked option in Quality. With the option off,
the replicate count saved in the recipe is zero, while scaling diagnostics
still run. The tooltip gives a reference timing for 1201 traces, twelve scales
and four origins: approximately five minutes for 199 replicates and 25 minutes
for 999, based on three relocation/partition timing probes. Actual runtime
depends on geometry, computer and diagnostic gates; these are estimates.

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

## 11. Illustrated synthetic walkthrough

These screenshots were regenerated with QGIS 3.44.12 on 22 November 2026. The example contains 627 clipped fractures in a seven-sided observed polygon, within a 10000 × 10000 model-metre extent. Its three orientation families have means 20°, 80° and 140°, each with 9° angular standard deviation. Units are explicitly UNLOCATED model metres. This is a synthetic teaching network generated in the repository, with no field location or external data licence to infer.

Regenerate the inputs with python scripts/tutorial_network.py --output outputs/fracture_example, then load lineaments and boundary from inputs.gpkg. The generator uses NumPy default_rng(20261122), 900 proposed centres from a four-level spatial cascade with quadrant probabilities (0.1,0.2,0.25,0.45), and Pareto-distributed lengths (shape 1.3) clipped to 150–900 m. Traces are clipped to the polygon and pieces shorter than 5 m are excluded. The retained count is 627. The generator writes provenance.json. Load [the walkthrough recipe](../examples/workbench_synthetic_recipe.json) after selecting the layers. The same generator supplies scripts/capture_user_guide_qgis.py, which executes the workflow and captures actual Qt widgets.

![Synthetic fracture network and observed domain](images/user-guide/00-map.png)

Analysis uses mother side 2000 m, divisors 2,4,8,16, q=0…4 in steps of 1, plots and GIS enabled. Mother-cell, structural and network products are off in this demonstration. Output names a new run's existing parent folder.

![Current Analysis form](images/user-guide/01-analysis.png)

Quality uses descriptive R²=0.9, length threshold 0 m, bootstrap off and default zeta settings. The independent assessment declares resolution 1 model m and 16 geometric scales from 125 to 2500 m; the complete interval wraps in its editor. Classic comparison is enabled. The order policy warns about D0–D2 order, and coarse trimming is off.

![Quality settings and complete interval](images/user-guide/02-quality.png)

The optional relocation test uses 99 replicates, seed 42 and the two-sided tail. The complete analysis with windows finishes in approximately five minutes on the walkthrough computer. Global p=0.02 and Holm p=0.46 over the 23-support family; minimum raw p=0.02. This demonstration cannot resolve the first Holm rejection at 0.05: at least 919 two-sided replicates are required, since 2 × 23 / (B + 1) ≤ 0.05. That minimum makes the threshold attainable; rejection also depends on the results. Results displays the resolution limit beside the p value.

![Scaling assessment, comparison and Monte Carlo controls](images/user-guide/02b-scaling-options.png)

Moving windows uses side 6000 m, spacing 2000 m, divisors 2,4,8,16, one origin and no proximity radii. Press Run MUSA and check Analysis complete. The descriptive fit accepts nine q values. Across global and window assessments, 61 support/q pairs are compatible, 14 are not supported and 132 have insufficient information. Eight of the 22 windows meet the 80% coverage threshold; every window retains the traces observed inside it and the diagnostic reasons.

![Moving-window setup](images/user-guide/03-moving-windows.png)

The separate classic block shows D_BC=1.59833, R²=0.994613 and global MUSA D0=1.56093, compatible on 16 scales from 125 to 2500 m. Classic counting uses one origin; assessment averages four origins. Separate JSON/CSV retain their measurement designs.

![Classic comparison, assessed D0 and test resolution](images/user-guide/14-comparison.png)

The global Dq estimates are compatible. The joint spectrum is withheld because alpha(0.5) = 1.571 < alpha(1) = 1.577 among jointly supported orders. The table also shows alpha(0) = 1.499 < alpha(0.5) = 1.571; alpha at q=0 is unsupported and remains outside that joint criterion. The message identifies the pair and its values. Window 18 below has a supported joint curve.

![Global joint-spectrum shape diagnostic](images/user-guide/14b-global-spectrum.png)

Select Moving windows — scaling assessment, Center 18, side 6000 m, Standard estimator. Coverage is 82.95%. All nine Dq values are compatible; four orders (q=0.5,1,1.5,2) also have jointly supported spectral estimates. The retained window interval is recorded separately from the global interval; it excludes boxes too large for the clipped support. Other windows show curvature, origin sensitivity or inadequate effective support.

![Window Dq at center 18](images/user-guide/04-window-dq.png)

![Per-q values, statuses and wrapped reasons](images/user-guide/07-per-q-values.png)

The joint f(alpha) curve at center 18 is visible. Its shape passes the same display checks applied to every support; values and acceptance rules are computed by the shared core. The chart's observed peak and fitted peak have separate labels; a fitted peak remains unavailable when its checks fail. This finite sample illustrates how to read a supported curve alongside abstentions elsewhere.

![Supported window spectrum](images/user-guide/05-window-spectrum.png)

Center 0 has 39.19% observed coverage, below the minimum 80%. Its estimates remain absent with the low-coverage reason. Window 11 has useful coverage (97.61%), a compatible D0, unsupported D1 from predictive curvature and insufficient q=4 effective support. The center selector preserves access to all these outcomes.

![Insufficient coverage at center 0](images/user-guide/08-low-coverage.png)

![Window with useful coverage and a curvature rejection](images/user-guide/08b-curved-window.png)

Click a spectrum to enlarge it with navigation controls; export the selected chart to PNG or SVG. The enlarged view retains the same selected supported curve.

![Enlarged supported window spectrum](images/user-guide/06-enlarged-spectrum.png)

Figures contains the saved descriptive figures. Scroll the page to see the full preview, then click to enlarge it. Descriptive Dq uses its own mother/child interval and origin; its values differ from the four-origin assessment above. The figure labels identify its descriptive calculation.

![Saved descriptive figures](images/user-guide/09-figures.png)

![Enlarged descriptive Dq figure](images/user-guide/10-enlarged-figure.png)

Results has outer vertical scrolling; its table and details have their own scroll bars. Narrow panels also allow horizontal table scrolling to access every column.

![Results in a small dock](images/user-guide/12-results-scroll.png)

Run details recovers status, version, dates, provenance, parameters and files. Open completed run loads a folder containing run_manifest.json without recalculation. Preserve the inputs and full output tree alongside the recipe and project.

![Details recovered from the saved run](images/user-guide/11-run-details.png)

Learn / Fundamentos reads the canonical chapters in either language. The sequence starts from the geological object and compares density, distance and a rose diagram on the same 627-trace network. It continues with self-similarity, multifractality, box counting and cell length. Its 13 figures use labels in the selected language and numbered captions; the reader preserves their proportions and adapts their size to the available width. Its examples include exact-length versus pixel mass and 100 random rods: 24 scales, classic R²=0.992364, MUSA D0 not supported from predictive curvature and segmentation. A shorter finite Cantor example explicitly records that classic counting obtains the correct value and MUSA abstains from four scales. The selector changes the chapter and comparison block; the remaining Workbench controls and Results blocks are consistently English.

![Learn in English](images/user-guide/15-learn-en.png)

![Fundamentos in Spanish](images/user-guide/15-learn-es.png)

Processing provides musa:analyze, musa:scaling_support and musa:run_recipe. The automated walkthrough runs their actual dialogs and checks complete manifests. Their help links to the same learning source. The [workflow map](WORKFLOW.md) connects controls to core functions and files; [five executed notebooks](../notebooks/README.md) demonstrate the API without QGIS.
