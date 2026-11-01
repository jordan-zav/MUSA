# Software development status

MUSA is a general-purpose multifractal and structural analysis QGIS plugin with
a shared Python API. QGIS is the primary interface by the author's direction.
The working tree contains experimental development in addition to the published
release. Local changes are not a new release until they are reviewed and packaged.

## Retained generic capabilities

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

Experimental version 1.1.0 is packaged locally. Public release 1.0.1 remains
historical; this conversion has not been committed, pushed or published.
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
