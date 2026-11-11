# Extended validation with published data

Work completed on November 2, 2026 through download scripts, adapters, analysis,
native QGIS checks, and evidence consolidation. Originals and results remain
outside the plugin and repository.

## Implemented components

- Adapters for GeoJSON/Shapefile with metric CRSs and original observation polygons, sparse MATLAB graphs, FracPaQ/HatchFrac coordinate rows, and binary masks.
- Downloads with provenance and checksum checks. FraXet selection uses supported HTTP ranges, a block cache, and HTTP429 backoff; selected members were verified without claiming the whole archive was downloaded.
- Explicit Zhang–Suen skeletonization and segments between pixel centers; isolated pixels, threshold, and cropping are recorded. A mask does not recover original fracture identity.
- Exact geometric union to remove coincident multiplicity, with lengths before/after. No snapping, coordinate rounding, or gap filling. Downloaded third-party code is not executed.
- Global/window assessment for q from −4 to 4, retaining Dq, tau, alpha, f(alpha), quality, and identities. Unsupported fits and insufficient information remain in outputs.
- Two window designs for georeferenced cases: outer-bounding-box quadrants and an overlapping interior grid. Both remain available; interior positions depend on geometry, not fitted slopes.
- Analytical comparison of the actual geometry engine with a 2D dyadic cascade of 65,536 segments; finite Cantor controls; resolution sensitivity; raster-count comparisons.
- Periodic-structure controls: apparent compatibility over one interval and rejection when it is extended across the characteristic scale. The extended follow-up is identified as exploratory.
- A declared family of three global conditional-translation tests, requesting 99 replicates per support and Holm adjustment. Untestable cases receive no invented p values.
- Separate QGIS projects by coordinates/source; viewer inspection and numerical comparison between Python and native Processing.

## Source coverage

| Source | Material used | Comparison limit |
| --- | --- | --- |
| Åland, Ovaskainen and colleagues | Fracture/lineament vectors and domains, EPSG:3067 | Multiple modalities/subsets of one territory; declared operational resolution |
| Loviisa, Ovaskainen and Nordbäck | Eight original networks/polygons, EPSG:3067 | Domains can prevent complete windows; absent coverage is not filled |
| Bristol, Kang | MATLAB coordinates/connectivity | Inferred observation rectangle; original units without physical verification |
| HatchFrac | Authors' 2D network, backbone, and three growth stages | Existing model outputs, not fractals with exact known dimension |
| Hornelen, Sahu/Roy figures | Three representations/crops explicitly identified in the article | Pixel-based figure derivatives; related maps, not independent outcrops |
| FracPaQ | Two vector examples from the authors' repository | Not attributed to Hornelen solely because they are named map1/map7 |
| FraXet | 24 preselected test masks from three families | 20 with traces, four empty; not assembled into a presumed continuous outcrop |
| GeoCrack | DataCite metadata | Harvard Dataverse returned 403/antibot checks; images were neither downloaded nor analyzed |
| Zhu, dataset 10.4121/14464893 | Metadata retained from the earlier task | Coordinates unavailable at tested endpoints; no analysis is claimed |

The archive contains 67 processable cases, including resolution variants and
controls; these are not 67 independent datasets. Four empty masks remain
not applicable. The detailed inventory records identifiers, licenses, and actual
source status; article, code, and dataset licenses are distinguished.

## What the tests support

The length-partition/canonical-calculation core recovered Dq, tau, alpha, and
f(alpha) of the exact cascade with maximum error approximately 2.09 × 10⁻¹⁴.
This uses an aligned origin and finite dyadic scales: it checks that calculation,
not geological accuracy or stability across four arbitrary origins.

The periodic grid illustrates why a stable slope does not prove fractality.
D0 was approximately 1.846 and compatible over the initial interval; extending
across its known spacing favored quadratic/segmented models. Both results
were retained without changing thresholds.

For a circle, each outer-rectangle quadrant has coverage pi/4 ≈ 0.785, below
the 0.8 minimum. Original reports remain available; interior windows permit
study of better-covered supports. Interior centers are at 3/8 and 5/8 along
each axis, with the same window side. These are not independent replicates.

Each observable in natural networks/figures has its own state. Compatible D0
does not guarantee a complete spectrum or a supported singularity peak.
Rejected estimates, resolution cutoffs, and sensitivities must accompany interpretation.

## Reproduction

Run from the repository root. Downloads use data/benchmarks or
MUSA_BENCHMARK_DATA. To repeat analysis with available originals, choose a
new output folder:

~~~text
python -m pip install -e ".[benchmarks]"
python scripts/extended_benchmark_inputs.py RESULTS
python scripts/run_extended_benchmarks.py RESULTS
python scripts/add_interior_benchmark_windows.py RESULTS
scripts/run_qgis_python.cmd scripts/qgis_extended_benchmarks.py RESULTS dist/qgis/VALIDATED_PLUGIN.zip
python scripts/report_extended_benchmarks.py RESULTS
~~~

Set MUSA_QGIS_ROOT to an existing installation before the QGIS step.
Preparation retains assumptions and inventories; the runner verifies input
hashes and refuses resumption with different parameters. The final report
retains support CSV files, spectral summaries, raster/vector comparisons,
manifests, and QGIS evidence. The verified run is the maintainer's archive
MUSA-extended-benchmarks-20261102_143812.

Primary sources and method scope are documented in that archive's README.md.
Ouillon's complete wavelet algorithms and the De Souza/Rostirolla MATLAB program
were not incorporated into MUSA; their papers inform range/sampling checks.
No release was published in that campaign.
