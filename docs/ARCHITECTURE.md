# Python engine and QGIS integration

MUSA maintains a shared numerical core. QGIS provides controls, geometry capture, and visualization; the shared calculations reside in the Python package.

~~~text
QGIS: layers and CRS -> WKB snapshot -> task -> bundled core -> outputs -> layers/viewer
Python: geometry/data              -> MUSA + RunConfig -> same workflow -> files
~~~

## Responsibilities

| Component | Code | Responsibility |
| --- | --- | --- |
| Basic API | src/musa/core.py | Point/line preparation, measure partitioning, global analysis, and mother cells |
| Measure and partition | partition.py and mass_partition.py | Length per box and optional acceleration |
| Shared workflow | workflow.py | RunConfig, recipes, stages, cancellation, manifest, and exports |
| Independent assessment | scaling.py | Rényi scaling over a declared interval and a conditional spatial test |
| Moving windows | moving.py | Clipped supports, local spectra, origins, and planar topology |
| Spectra | spectrum.py and spectrum_products.py | Peak diagnostics, identities, SQLite index, and support queries |
| Python GIS | geomatics.py and gis_styles.py | Input/output with optional dependencies and styles |
| QGIS adapter | qgis_plugin/inputs.py and native_gis.py | Geometry capture, CRS transformation, and native QGIS output |
| QGIS interface | workbench.py and provider.py | Dock panel and Processing algorithms |
| Legacy | src/musa/interface.py and older launchers | Tk compatibility; not the recommended interface |

Filenames without a directory in this table belong to src/musa, except for the QGIS components.

## What sharing the engine means

The ZIP builder copies src/musa into musa_qgis/_core/musa. The plugin imports that bundled copy through runtime.py. It does not depend on another package called musa being installed in QGIS Python, avoiding accidental mixing with an external version.

The source is shared; each ZIP contains a snapshot. Editing the source or installing a newer package with pip does not update an installed plugin. Rebuild and reinstall its ZIP. The build manifest records file hashes for comparing the copies.

## Geometry, CRS, and threads

In QGIS, the adapter validates geometry type and a projected CRS in meters, transforms coordinates, and copies WKB before starting the task. The task receives no project layers or interface objects. Temporary layers, unsaved edits, and explicit line selections are included. Copied attributes are those supported by the structural context; this is not a complete backup of the original data.

In Python, MUSA.from_line_geometries receives already projected Shapely objects: it does not transform coordinates or verify that a CRS label matches their values. The caller must check the actual CRS and units. The MUSA constructor accepting a GeoDataFrame/file has its own GIS preparation; explicit reprojection is recommended for reproducibility.

The shared workflow reserves a new folder, writes a recipe/manifest, and executes stages. A lock permits one run per loaded copy of the core. Cancellation is cooperative; an ongoing operation may take time to reach the next cancellation point. A failure retains partial results and marks the manifest; it is not loaded as a completed run.

## Two calculation paths

1. execute_analysis always runs the descriptive global analysis and adds the requested products. Its triple R² filter can leave fewer than two accepted q values and fail the workflow, even if a partial assessment was written earlier.
2. assess_lineament_scaling and Processing musa:scaling_support run the independent assessment. They do not require passing that global filter. Use this path to examine data whose descriptive spectrum could not be fitted.

In the viewer, analysis and assessment identify these sources. Do not average them or confuse their criteria, scales, stabilization, or number of origins. See [theory](theory.md) and [spectra](SPECTRA.md).

## Distribution and automation

The Python package supports scripts and notebooks without QGIS. The plugin requires QGIS and its dependencies. A Python package distribution channel would not install QGIS or automatically register the plugin.

Automation is currently available through Python and Processing. An executable API example is examples/headless_workflow.py. There is no general musa command for analyzing files or running recipes. The [installation guide](INSTALLATION.md) records distribution and command-line availability.

## Reproducibility

Record the version/commit or ZIP hash, parameters, actual CRS, inputs, and provenance. recipe.json saves parameters, not input paths. run_manifest.json records geometry hashes supplied by the host when available, and output hashes. Also retain the original data inventory and its license.

Verified Python/Processing equivalence concerns matching inputs, scales, and parameters; it does not establish equivalence with another ZIP version or preprocessing method. The [validation status](SCALING_VALIDATION_STATUS.md) describes the evidence and scientific limits.
