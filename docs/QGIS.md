# MUSA for QGIS

QGIS is the primary MUSA interface. The English dock is organised as project
inputs, analysis parameters, reproducible recipes, background execution and
mapped results.
The numerical implementation remains in src/musa and is shared with Python.
Start with [installation and distribution status](https://github.com/jordan-zav/MUSA/blob/main/docs/INSTALLATION.md) and
[architecture](https://github.com/jordan-zav/MUSA/blob/main/docs/ARCHITECTURE.md) to distinguish the Python package from the
plugin's private core snapshot. Installing the package with pip does not
register the QGIS plugin or update an already installed ZIP.

## Installation

Download musa_qgis-<version>.zip from the latest GitHub release, or build it
with python scripts/build_qgis_plugin.py from the source checkout (the archive
is written to dist/qgis). In QGIS, open Plugins > Manage and Install
Plugins > Install from ZIP and select the archive. Open
Vector > MUSA > MUSA Workbench, or use the MUSA toolbar button.

MUSA 1.1.0 is the first QGIS plugin release; the ZIP is attached to the
v1.1.0 GitHub release.
Metadata targets QGIS 3.34–3.99. The release was tested on QGIS 3.44.12;
metadata does not imply all versions have been tested. QGIS 4 is not yet supported.
The plugin bundles its own core, without changing global Python import paths.

NumPy, SciPy, Shapely and Matplotlib must be available in QGIS's Python runtime.
Mother-cell GeoPackage export uses QGIS's GDAL directly. Experimental moving
windows additionally require GeoPandas, Pandas, PyProj and a supported file
writer. The plugin does not install dependencies into the host automatically.

## Workflow

1. Load lineaments and a polygon boundary into QGIS, including temporary layers.
2. Choose both layers in Analysis and select a projected analysis CRS in metres.
   All boundary features are used. Line selection is optional and explicit.
3. Set mother-cell size, internal divisors and q range. At least four distinct
   divisors of two or greater are required; internal sizes are mother/divisor.
4. Choose products, an existing output parent folder and optional quality
   settings. Global spectra are always computed; other products are independent.
5. Run MUSA. Each run reserves a new subfolder. Results appear as a QGIS layer
   group, with figures and an execution log in Results.

Quality exposes fit R2, length threshold, bootstrap, negative-q stabilization,
zeta weights and sensitivity comparisons. The negative-q stabilization floor
changes the measure and drives every negative-q dimension towards D0; keep it
off unless you also report the unmodified run (see [negative q](NEGATIVE_Q.md)).
Moving windows are experimental and
can be expensive, especially with sixteen grid origins. Estimates and geometry
describe numerical/structural support, not permeability or geological success.

Input layers are copied to WKB and transformed through QGIS before the worker
starts. The worker receives no project layers or GUI objects. Memory layers,
unsaved edits and explicit line selection are therefore included in the snapshot.
Invalid features are rejected with their feature IDs rather than silently fixed.
No automatic UTM choice is made: the analysis CRS is an explicit user decision.

## Outputs and reproducibility

CSV reports preserve accepted and rejected q, fit quality and scale diagnostics.
Mother-cell products preserve canonical and zeta-weighted estimates separately.
GeoPackages include all-q spectra, a display q nearest two, a reliable subset,
monofractal cells and selected structural statistics. Reliability and density use
separate layers; no geological favorability score is introduced.

The run manifest records software version, timestamps, recipe, transformed input geometry hashes, CRS,
feature counts, completion status and output SHA-256 hashes. It does not store
source passwords or provider connection strings. Fault IDs and interpreted
structural orders, when present, are copied for the existing experimental
structural context and receive their own input hash. Other attributes are not
copied; this is not an archival copy of the complete inputs.

Existing run directories are rejected. Failed and cancelled runs retain partial
outputs with a failed/cancelled manifest; they are not loaded as completed runs.
Cancellation is cooperative between scales, mother cells and stages. Structural
statistics, bootstrap and experimental window stages may take time to return.
Closing the dock hides it; unloading cancels the task and detaches GUI callbacks.

Matplotlib output uses standalone Agg figures without switching QGIS's backend.
One MUSA workflow executes at a time per loaded plugin core.

## Automation

Save/load recipes in the panel. A recipe contains analysis parameters, not input
paths, so it can be applied to another explicit pair of layers.

Processing tools:

- musa:analyze — common parameters for Processing, batch and Model Designer.
- musa:run_recipe — all options from a musa-analysis version 1 JSON recipe.
- musa:scaling_support — independent finite-range Rényi Dq assessment, including
  datasets that fail the legacy spectrum-fit gate. See [SCALING_SUPPORT.md](SCALING_SUPPORT.md).

All three accept lineaments, polygon boundary, explicit metric analysis CRS and
a new output folder. Processing's selected-feature source is supported. The
first two use the same execution function as the dock; the scaling tool runs
the independent diagnostic from the same bundled core. The public Python API additionally provides
RunConfig and execute_analysis in musa.workflow, and MUSA.from_line_geometries
for already projected Shapely inputs. This adapter trusts the host to validate
metric units; the QGIS adapter performs that validation.

The former Tk interface and standalone launchers remain as legacy source for
compatibility and are excluded from the QGIS bundle. They are no longer the
recommended installation path.

## Validation sources

Results also provides global/window Dq, tau(q), alpha(q) and f(alpha) curves,
with separate q=0, observed-maximum and descriptive fitted-peak references.
Choose a center, size and estimator, then export the selected figure to PNG/SVG.
Results has separate Spectra, Figures and Run details pages. Charts resize with
the panel; click them to open an enlarged view. A per-q table explains missing
values and unsupported fits, including boundary coverage for assessment windows.
See [SPECTRA.md](SPECTRA.md) for sources, quality criteria and output formats.

Runtime tests use synthetic lineaments and an isolated QGIS profile, never
private project inputs or a user's installed plugin directory. Threading and
Processing follow the official [QGIS task guide](https://docs.qgis.org/3.40/en/docs/pyqgis_developer_cookbook/tasks.html)
and [Processing plugin guide](https://docs.qgis.org/3.40/en/docs/pyqgis_developer_cookbook/processing.html).
