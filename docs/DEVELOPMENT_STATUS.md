# Software development status

MUSA is a general-purpose multifractal and structural analysis QGIS plugin with
a shared Python API. QGIS is the primary interface by the author's direction.
The working tree contains experimental development in addition to the published
release. Local changes are not a new release until they are reviewed and packaged.

## Retained generic capabilities

Current installation, packaging boundaries and runnable Python examples are documented
in [INSTALLATION.md](INSTALLATION.md), [ARCHITECTURE.md](ARCHITECTURE.md) and
[PYTHON_API.md](PYTHON_API.md). The source version is 1.0.0; the historical public
1.0.1 release is unchanged. A new PyPI publication and a general installed analysis
CLI remain pending. The existing musa-ui entry point launches the legacy Tk UI.

- Global and local multifractal spectra and operational fit diagnostics.
- Overlapping multiscale windows, conservative line-length partition and
  numerical checks for grid origin, boundaries and sampling support.
- Canonical and zeta-weighted estimates reported separately.
- Planar line topology, proximity relations, local directions and configurable
  descriptive categories; no project-specific geological favorability rule.
- English dockable QGIS workbench, Processing, Python API, GIS export and styles.
- Synthetic examples and automated numerical tests.

## Data and interpretation

The repository does not distribute private project inputs, deliverables,
production metrics or project-specific geological rule tables. Those materials
are maintained separately. Results from private studies are not included as
software validation or public benchmarks.

Model configuration and numerical quality describe the computation. They do not
establish permeability, prospectivity or a probability of geological success.
Generic numerical improvements need independent verification with synthetic
controls or appropriately licensed public data.

## Before a future release

Review the local development changes, run the automated checks and build the
application from the reviewed source. Audit the resulting distribution for
unexpected data and temporary files. No publication or version change is
authorized solely by this working-tree organization.

## Local QGIS conversion — 28 October 2026

On 28 October, experimental version 1.1.0 was packaged locally. Public release
1.0.1 remains historical. The conversion was subsequently committed and pushed
in the 1 November source reconciliation; no new QGIS plugin release was issued.
Installation and workflow details are in [QGIS.md](QGIS.md).

Implemented:

- English Analysis, Quality, Moving windows and Results tabs, project-layer
  selectors, explicit metric CRS, optional line selection and native geometry
  snapshots. Boundary always uses all features.
- Global/local spectra, density/orientation statistics, optional connectivity,
  bootstrap, zeta sensitivity, experimental windows and proximity from the
  existing numerical core.
- Recipes shared by the dock, Python workflow API and two Processing algorithms:
  musa:analyze and musa:run_recipe. Both support batch and Model Designer.
- QGIS task execution without passing project/GUI objects to the worker.
  Cooperative cancellation and safe detach on unload, with retained partial runs.
- Native GDAL mother-cell GeoPackages, result groups, reliability/density
  rendering, figure previews and execution log.
- New run folders, status manifests, geometry/structural attribute hashes,
  recipe and output hashes. Only interpreted fault IDs/orders are retained as
  optional source attributes; provider connection strings are excluded.
- Private bundled core, ZIP builder and CI packaging check. Legacy Tk source is
  retained but excluded from the QGIS ZIP. Plot rendering uses Agg figures
  without changing the host's Matplotlib backend.

Executed validation:

- 90 Python tests passed, including numerical equivalence between GIS and native
  geometry adapters, output collision protection, cancellation manifests and
  preservation of a host Matplotlib backend.
- Ruff passed for source, tests, plugin and builder.
- Installable ZIP exercised with QGIS 3.44.12 and Qt offscreen in a temporary
  profile under D:/DevResources/Sessions. No real user profile was modified.
- Processing registration/execution, recipes, output hashes, metric GeoPackage
  CRS and global spectrum values checked against the shared core.
- Memory inputs, selected lines, source reprojection and rejection of geographic
  or feet analysis CRSs; successive background tasks and result loading passed.
- Experimental windows, sixteen origins and proximity ran in the background;
  unload during an active task and provider removal passed.
- Native QGIS widget captures with synthetic data are in docs/images, in English.

Metadata supports QGIS 3.34–3.99; only 3.44.12 has been executed locally. This
validation uses synthetic controls and does not establish geological validity.
Manual interaction in a normal QGIS session and representative public datasets
remain useful before a public release. Cancellation is between scales, mother
cells and stages, not an immediate interruption of every numerical operation.


## Source reconciliation — 1 November 2026

The QGIS conversion and retained generic changes were reviewed for source-control
integration. Historical test and packaging records above retain their dates.
No tests, application runs or packages were produced during this Git-only
reconciliation. Validate this revision on the development PC before distribution.
The Windows QGIS helper requires MUSA_QGIS_ROOT to identify an existing local
installation; machine-specific installation paths are not stored in the script.
Publishing source code does not publish a QGIS catalogue release.

## Requested version and mathematical scope — 1 November 2026

The maintainer requested version 1.0.0 for the QGIS delivery. The current plugin
metadata and Python package version follow that request. Historical release tags
and older ZIPs retain their original versions; no historical release is replaced.
The current development work remains experimental.

See [scaling validation status](SCALING_VALIDATION_STATUS.md). Moving-window
fit acceptance and zeta are operational diagnostics, not calibrated tests proving
fractal or multifractal scaling. The legacy synthetic-profile report does not
execute the analysis engine and must not be used as numerical validation.

Validation repeated on this PC for the requested numbering:

- 90 Python tests passed; Ruff passed for source, tests, plugin and builder.
- Built dist/qgis/musa_qgis_1.0.0_20261101T225000923283Z.zip.
- The extracted ZIP passed QGIS 3.44.12 Processing, native GeoPackage, shared
  core comparison, selection, reprojection, background/successive tasks,
  experimental moving windows with 16 origins and proximity, and unload during
  an active task. Process exit code 0. Synthetic inputs and an isolated profile.
- GDAL emitted informational unsupported TIMESTAMP field-format warnings during
  moving-window export. The output checks passed; exact timestamp-field metadata
  preservation was not assessed by these tests.
- Evidence: D:/DevResources/Sessions/MUSA-d2fef40d2e/20261101_175006_46717c1baed54740a44dd5418f059779/qgis_smoke/validation.json.

The version change, documentation clarifications and new ZIP remain local. No
commit, push, release or replacement of the historical v1.0.0 tag was performed.

## Experimental Renyi scaling assessment — 1 November 2026

Implemented the finite-range Dq diagnostic and conditional trace-relocation null
in src/musa/scaling.py. Available in Quality, shared recipes/workflow and the
independent third Processing tool musa:scaling_support. The workflow assesses
the global domain and all moving windows within an explicit budget. Reports
retain unsuccessful q, scope, geometry/grid/scale assumptions and the complete
support family. The QGIS run group includes the diagnostic CSV table.

Linear, quadratic and segmented models use nested leave-one-scale-out prediction;
the segmented breakpoint is reselected in each training fold. Scale deletion,
end trimming, four shifted grids, resolution and box support are checked. The
conditional D0-D2 Monte Carlo contrast is separated from scaling compatibility,
uses finite-simulation tail values and Holm adjustment across requested supports.
It is not a mathematical proof or a universally calibrated multifractality test.
See [the method and limitations](SCALING_SUPPORT.md).

Validation performed:

- 120 Python tests passed, including real line/Cantor dimensions, nonlinear
  controls, cancellation, failures, null reproducibility and moving-window family
  integration. One legacy Tk test was skipped in the full suite because its Tcl
  interpreter could not initialize; the legacy UI/moving subset had separately
  passed all 14 tests. QGIS uses Qt and passed its independent native checks.
- Ruff passed for source, tests, plugin, builder and the new validation script.
- QGIS 3.44.12 ran the extracted package: independent Processing, output collision
  protection, global and per-window reports, table loading, all new recipe options,
  task execution and unload. Process exit code 0. No normal user profile modified.
- The GUI test exposed loss of precision from general-format scale strings.
  Recipe loading now uses a round-trip float representation; exact recipe
  preservation is exercised with noninteger geometric scale spacing.
- Actual synthetic controls recovered Dq close to 1 for a line, and the expected
  nonconstant Dq for a finite binomial Cantor approximation. Known quadratic and
  broken-scale curves were not classified as compatible linear scaling.
- Conditional-null pilot: 24 independently generated datasets, 39 simulations
  each, 24 testable and 1 rejection at 0.05. The 95% binomial interval was
  0.0011–0.2112; this pilot does not establish general size or detection power.

Native evidence:
D:/DevResources/Sessions/MUSA-d2fef40d2e/20261101_180752_304fe920bc784e32a4c3cab4d2c07551/qgis_smoke/validation.json.
Numerical pilot:
D:/DevResources/Sessions/MUSA-scaling-20261101_180055/validation.json.
Screenshots and a computed-control figure are in docs/images. A final package
can include updated documentation/images without changing the validated Python
runtime; its build manifest allows checking that identity.

At this validation checkpoint, development changes were local at version 1.0.0. No new publication,
historical tag replacement, private dataset reuse or claim of peer review.

## Complete spectra by window — 2 November 2026

Implemented the approved spectrum plan in the local 1.0.0 package:

- Moving-window CSV/GeoPackage rows now include tau and tau_w. The direct
  finite-range assessment also evaluates partition/CJ features for tau, alpha
  and f(alpha) on the same probabilities, scales and origins, with Dq-only bounds
  kept separate and tau(1)=0 marked as a normalization identity.
- Numerical identity residuals, q support and all three distinct singularity
  references are retained. Ties are not arbitrarily resolved; exactly three
  fitting points are explicitly descriptive interpolation. Degenerate alpha
  sets and out-of-range/nonconcave peaks remain unavailable.
- An indexed SQLite store and summary CSV separate analysis versus fixed-range
  assessment and canonical versus zeta estimates. The moving GeoPackage registers
  the summary as a nonspatial attributes table. Existing exports remain intact.
- Results offers domain/source, window center/size and estimator selection,
  four curves, selected PNG/SVG export and reopening completed workflow or
  Processing runs. Failed/cancelled runs are refused. Older completed runs
  without a cache retain their file-based access. No automatic historical migration.
- See [SPECTRA.md](SPECTRA.md), including the updated native QGIS screenshot.

Validation:

- Latest full Python run: 129 passed, 2 legacy Tk UI checks skipped because Tcl/Tk
  could not initialize. Those checks are outside the QGIS bundle. The new spectrum
  product test module separately passed all 10 checks. Ruff passed.
- Analytic controls cover straight lines and finite binomial Cantor approximants,
  canonical/zeta identities, q=0/q=1, tied/degenerate peaks, rejected gaps, missing
  q=0, numerical bounds, read-only selection and cancellation-safe cache replacement.
  Existing parallel/sequential window equivalence remains tested with tau fields.
- QGIS 3.44.12 tested the extracted ZIP with synthetic data and an isolated profile:
  Processing, global/window cache and GeoPackage table, every available source and
  estimator, PNG/SVG exports, exact recipe round trips, reopening Processing runs,
  refusing incomplete runs, old-cache absence and unload during an active task.
  The final process returned 0. No normal user profile was changed.
- Native evidence:
  D:/DevResources/Sessions/MUSA-d2fef40d2e/20261102_131840_c790f10b7409435a9a795fce561e0d6a/qgis_smoke/validation.json.
- Runtime-tested package: dist/qgis/musa_qgis_1.0.0_20261102T181840061269Z.zip.
  Final documentation/screenshot package:
  dist/qgis/musa_qgis_1.0.0_20261102T182048621537Z.zip.
  Its Python runtime was verified identical to the tested package via the build
  manifests; archive integrity and all file hashes passed. Final ZIP SHA256:
  49b620b027bb1c8a25f58b0815bf2fc99ec2bf38b9ce790f72f5a69ff0450ff9.

The numerical assessment remains experimental. No new independent significance
tests for correlated spectrum quantities were added; the existing spatial null
is still D0-D2. At that validation checkpoint, source, documentation and ZIP
were local, without commit, push, release or replacement of historical tags.

## Extended public-data validation and repository update — 2 November 2026

This repository update includes the experimental 1.0.0 scaling/spectrum work,
its QGIS integration, and reproducible public-data benchmark adapters and scripts.
The public release and historical tags are unchanged; this is a source update,
not a new plugin release. Development dependencies now include the benchmark
extra needed by the added adapter tests.

- 67 processable cases, 450 global/window supports and 4050 Dq assessments,
  retaining insufficient and unsupported outcomes. Four selected empty FraXet
  masks remain not applicable; related subsets are not independent outcrops.
- Original Åland/Loviisa vectors, a Bristol MATLAB graph, author HatchFrac and
  FracPaQ examples, identified Hornelen figure derivatives and a declared FraXet
  test subset. GeoCrack images and Zhu coordinates remain unavailable and are
  not represented as analyzed.
- An exact aligned-grid geometric cascade with 65,536 segments checks the actual
  Dq/tau/alpha/f(alpha) core to a maximum absolute error of about 2.09e-14 over
  its finite dyadic scales. This is not general geological validation.
- A periodic grid demonstrates why finite-range compatibility is not proof of
  fractality. Quarter-grid reports are preserved alongside geometry-declared
  overlapping interior windows; fit and coverage thresholds are unchanged.
- QGIS 3.44.12 reopened eight portable projects and exercised 67 saved runs.
  Two native Processing comparisons matched Python curve values within 5e-14.
  The normal user profile was not modified.
- The directed benchmark/scaling/spectrum checks passed 53 tests, with Ruff
  passing. Dataset and result-file hashes and the delivery ZIP CRC were verified.
- Before the source update, the complete local Python suite passed 144 tests
  with one unavailable-runtime test skipped. Ruff covers src, tests, qgis_plugin
  and all scripts; CI installs the benchmark dependencies and uses that scope.

See [extended benchmarks](EXTENDED_BENCHMARKS.md) and the
[executed plan](EXTENDED_BENCHMARK_PLAN.md). Original data, generated outputs,
profiles and delivery ZIPs remain outside version control and the plugin.
