# Python API: run the engine without QGIS

Install as described in [INSTALLATION.md](INSTALLATION.md). These examples use
the available API; they assume neither an installed musa analysis command nor
a PyPI publication.

## In-memory 2D points

~~~python
import numpy as np
from musa import MUSA

points = np.random.default_rng(42).random((5000, 2))
analyzer = MUSA(points, q_values=np.arange(-2, 3))
result = analyzer.run_analysis(min_scale=0.01, max_scale=0.4, num_scales=20)
print(result.q)
print(result.dq)
print(result.tau)
~~~

Point input is an N × 2 array with at least ten points. Normalization is on by
default; these scales belong to normalized space, not map meters. Use
normalize=False and consistent scales to preserve coordinates. This path
counts points per box; it does not measure trace length or accept a spatial 3D array.

MUSAResult contains accepted q values, their Dq, tau, alpha, f_alpha, R²,
available diagnostics, and rejected q values with quality information. If fewer
than two q values pass the descriptive triple filter, run_analysis raises
ValueError. It does not return an approval of fractality.

## Lines and observation domain

The following block requires your own two files; filenames are illustrative.
For multilayer GeoPackages, choose layers explicitly with GeoPandas' layer argument.

~~~python
import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.ops import unary_union
from musa import MUSA

lines = gpd.read_file("lineaments.gpkg", layer="lineaments")
area = gpd.read_file("domain.gpkg", layer="domain")
if lines.crs is None or area.crs is None:
    raise ValueError("Both inputs need their correct source CRS")

# Example metric CRS: replace it with one appropriate to the actual study area.
analysis_crs = CRS.from_user_input("EPSG:32718")
if not analysis_crs.is_projected or analysis_crs.axis_info[0].unit_conversion_factor != 1:
    raise ValueError("A projection in meters is required")
lines = lines.to_crs(analysis_crs)
area = area.to_crs(analysis_crs)
boundary = unary_union(area.geometry)

analyzer = MUSA.from_line_geometries(
    lines.geometry, boundary, analysis_crs.to_wkt(), q_values=np.arange(-2, 3))
~~~

This adapter clips to the polygon, rejects invalid lines, and does not reproject.
A CRS label does not change coordinates. The MUSA constructor also accepts a
GeoDataFrame/vector path and boundary, with configurable gis_reproject_to;
explicit preparation makes units and layers easier to audit.

Before assessing scaling support, harmonize duplicates and record the effect
on length. The independent assessment rejects coincident multiplicity rather
than silently dissolving it. Descriptive and moving-window preparation have
different contracts; see [theory](theory.md).

## Shared workflow and exports

Continue from the line analyzer above:

~~~python
from musa.workflow import RunConfig, execute_analysis

config = RunConfig(
    mother_cell_m=4000,
    divisors=(2, 4, 8, 16),
    q_min=-2, q_max=2, q_step=1,
    local=True, structural=True, network=False,
    plots=True, gis=True)

manifest = execute_analysis(analyzer, config, "outputs/new_analysis")
print(manifest["status"])
print(manifest["outputs"])
~~~

These sizes illustrate configuration; they are not recommended geological
scales. Choose them from resolution, domain, and objectives. The final folder
must not exist: do not create it before execute_analysis. The workflow reserves
it and retains a manifest on later failure/cancellation. Its parent may exist.

The workflow always runs the global spectrum. local, structural, network,
moving, plots, and gis enable their respective stages. RunConfig requires at
least four distinct integer divisors >=2. It does not itself establish a decade
of scaling; that is a separate assessment criterion.

A synthetic example without your own files is available:

~~~text
python examples/headless_workflow.py --output outputs/headless_demo
~~~

This example ran without QGIS, including GIS/figure exports. It is neither a
natural dataset nor a general command-line file-analysis tool.

## Recipes

~~~python
import json
from pathlib import Path
from musa.workflow import RunConfig

recipe_text = json.dumps(config.recipe(), indent=2)
restored = RunConfig.from_recipe(json.loads(recipe_text))
restored_from_file = RunConfig.from_recipe(
    json.loads(Path("outputs/new_analysis/recipe.json").read_text(encoding="utf-8")))
~~~

The format is musa-analysis version 1. It stores parameters, not input paths.
Pass the recipe to execute_analysis with a prepared analyzer. QGIS can reuse it
through musa:run_recipe. Equivalence requires the same geometries, CRS, scales,
and core version.

## Independent scaling assessment

Continue with the same line analyzer, even if run_analysis could not fit it:

~~~python
from pathlib import Path
import numpy as np
from musa import ScalingOptions, assess_lineament_scaling, write_scaling_reports

options = ScalingOptions(
    resolution_m=10, null_replicates=99, seed=42,
    renyi_order_policy="inform_q0_q2", null_tail="two_sided",
    coarse_trim_min_effective_q2=4)
report = assess_lineament_scaling(analyzer, np.geomspace(25, 1000, 16), options)
out = Path("outputs/new_assessment")
out.mkdir(parents=True, exist_ok=False)
write_scaling_reports(out, [report])
for row in report["q_results"]:
    print(row["q"], row["status"], row["dimension"], row["reasons"])
~~~

Resolution and interval are examples to justify from the data. Unsupported
scales are excluded. Information can remain insufficient; this is reported
without searching afterward for a better-fitting interval. write_scaling_reports
uses fixed filenames, so the example explicitly reserves a new folder.
The [user guide](USER_GUIDE.md) lists all ScalingOptions and the
[tutorial](TUTORIAL.md) executes a complete synthetic case with the article policy.

For local support, pass boundary as the clipped window, nominal_area as the
unclipped square's area, and a unique support_id. Add center_id, center_x,
center_y, and window_m to window reports before exporting to identify them in
the spectral index. RunConfig.scaling_support integrates the assessment into
the shared workflow without removing its global-fit requirement.

## Windows and result readers

export_moving_windows accepts regular or explicit centers and a list of sizes.
See [moving_windows.md](moving_windows.md) for its contract and optional origins.

~~~python
from pathlib import Path
from musa import list_spectra, read_spectrum, spectrum_figure

cache = Path("outputs/new_analysis/spectrum_curves.sqlite")
index = list_spectra(cache)
if index:
    selected = read_spectrum(cache, index[0]["series_id"])
    figure = spectrum_figure(selected)
    figure.savefig("outputs/selected_spectrum.png", dpi=160)
    figure.clear()
~~~

Index readers are read-only and need no QGIS. Select source, support_id, and
estimator explicitly for comparisons; the first record has no preferred scientific meaning.

## Operational parameters

Inspect complete fields/defaults in the installed version:

~~~python
from dataclasses import asdict
from musa.workflow import RunConfig
from musa import ScalingOptions

print(asdict(RunConfig()))
print(asdict(ScalingOptions(resolution_m=1)))
~~~

RunConfig and ScalingOptions have different validators because they solve
different tasks. resolution_m is mandatory for assessment; seed controls the
requested replicates, not input errors or projection selection.
