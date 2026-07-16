# MUSA: Multifractal Spectrum Analyzer

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

MUSA is a Python tool for fractal and multifractal analysis of spatial data, with a GIS workflow for geological lineaments.

## Available algorithms

| Component | Status | Main outputs |
| --- | --- | --- |
| Global multifractal spectrum | Ready | Dq, tau, alpha, f alpha, and per-scale diagnostics |
| Local Chhabra Jensen by mother cell | Ready | alpha and f alpha by mother window |
| Multiscale zeta weighting | Ready | alpha_w, f_alpha_w, zeta_mean, and zeta_min |
| Reliability filter | Ready | reliable flag by mother cell and q |
| Local monofractal analysis | Ready | Local D0 and D1, including weighted and robust versions |
| Bootstrap and jackknife | Ready | Confidence intervals and leave-one-scale-out sensitivity |
| Robust Theil Sen estimation | Ready | alpha_ts, f_alpha_ts, D0_ts, and D1_ts |
| Leverage and Cook diagnostics | Ready | Global and local per-scale CSV outputs |
| Zeta sensitivity | Ready | Baseline, coverage-heavy, mass-heavy, scale-heavy, neff-heavy, and soft profiles |
| Structural statistics | Ready | Density, total length, dominant orientation, and anisotropy |
| Lineament connectivity | Experimental | Components, intersections, and network density |
| GIS export | Ready | Mother-cell GeoPackage and reliable layers |
| Run packaging | Ready | ZIP archive organized by category |
| Synthetic validation | Ready | Summary across controlled scenarios |

## Methodological scope

MUSA does not claim to introduce multifractal analysis of lineaments. Its contribution is the integration of:

* Direct global and local Chhabra Jensen analysis.
* Probability recalculation within each mother cell.
* Local zeta weighting as a measure of multiscale reliability.
* Explicit separation of structural density, multifractal complexity, and reliability.
* Reproducible GIS export for mapping and geological interpretation.

*Zeta should be interpreted as an operational reliability weight, not as a direct physical property.*

## Recommended workflow

1. Define the lineaments and analysis boundary in a metric CRS, or enable automatic reprojection.
2. Select a mother-cell size and enough child resolutions for regression.
3. Run the global analysis.
4. Export local mother cells with zeta and reliable values.
5. Compare density, orientation, alpha, alpha_w, and reliable.
6. Use synthetic validation and zeta sensitivity before drawing strong geological conclusions.

## Documentation

| File | Purpose |
| --- | --- |
| docs/theory.md | Complete technical definition of the method |
| docs/references.md | Public scientific references |

## Generated results

Generated results are excluded from version control to prevent working data and temporary artifacts from being published.

## Python API

The package exposes MUSA, MUSAResult, resolutions_from_mother_cell, export_analysis_plots, export_mother_plots, export_mother_geopackage, package_run_output, run_synthetic_validation, compute_lineament_mother_structural_stats, and compute_lineament_network_stats.

For GIS lineaments, use data as the line layer, boundary as the analysis boundary, and resolutions_m in meters. Mother-cell analysis is produced through export_cell_outputs with aggregate_to_mother enabled.

## Desktop interface

Launch the desktop interface with musa-ui after installing the package in editable or standard mode.
