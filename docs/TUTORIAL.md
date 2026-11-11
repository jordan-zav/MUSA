# Reproducible scaling assessment in Python and QGIS

This tutorial uses one synthetic line and a square observation domain. No
field data, external downloads, or redistribution permission is needed.
Coordinates are unlocated model meters in a custom projected CRS. They are
not measurements from a real site.

The line runs from (1000,1500) to (9000,6500); the domain is [0,10000]².
The generator fixes 16 geometric box sizes from 10 to 1000 before fitting.
The article policy is renyi_order_policy=inform_q0_q2, null_tail=two_sided,
and coarse_trim_min_effective_q2=4. The example declares resolution 1, q=0,1,2,
seed 42, and 999 relocation replicates. All other ScalingOptions remain at
their defaults. A finite line has asymptotic geometric dimension 1; the
reported values are estimates over the declared finite interval.

## Case A: Python assessment and relocation test

### Install and run

Use a source checkout containing examples/scaling_tutorial.py and its
scaling_tutorial_expected.json reference. These documentation/example additions
postdate the v1.2.0 tag and retain its 1.2.0 numerical core; installing the tagged
package alone does not supply this newer example. Follow
[INSTALLATION.md](INSTALLATION.md) for dependencies, then run from that
checkout's root:

~~~text
python -m pip install -e ".[gis]"
python examples/scaling_tutorial.py --output outputs/scaling_tutorial --check
~~~

The output folder must not exist. Use a different name for another run; the
example refuses to overwrite an existing folder. No QGIS installation is
required. --check compares the portable numerical summary with
examples/scaling_tutorial_expected.json at absolute tolerance 1e-10.

The script generates:

| File | Contents |
| --- | --- |
| inputs.gpkg | lineaments and boundary layers in the custom metric CRS |
| crs.wkt | Explicit CRS definition; no inferred geographic location |
| protocol.json | Requested scales/options, stable geometry hash, file hash, and Processing parameters |
| recipe.json | RunConfig parameter recipe; not a container for inputs |
| assessment/scaling_support.json | Full assessment, observables, margins, and all saved null contrasts |
| assessment/scaling_support.csv | One row per support/q, including separate observable states and null fields |
| assessment/spectrum_curves.sqlite | Saved spectrum data by source/support/estimator |
| assessment/spectrum_summary.csv | Spectrum summaries and singularity references |
| summary.json | Portable outcomes checked against the committed reference |

GeoPackage metadata can contain creation times, so a regenerated binary file
need not have the same SHA-256. protocol.json records its actual file hash
and separately hashes the fixed geometry/CRS definition. Numerical comparison
does not depend on filenames or timestamps.

### Core API call

The executable example performs this calculation after generating the inputs:

~~~python
import numpy as np
from musa import MUSA, ScalingOptions, assess_lineament_scaling, write_scaling_reports
from shapely.geometry import LineString, box

# Use the CRS saved by the generator, not a new geographic interpretation.
from pathlib import Path
crs = Path("outputs/scaling_tutorial/crs.wkt").read_text(encoding="utf-8")
lines = [LineString([(1000, 1500), (9000, 6500)])]
analyzer = MUSA.from_line_geometries(
    lines, box(0, 0, 10000, 10000), crs, q_values=[0, 1, 2])
options = ScalingOptions(
    resolution_m=1, null_replicates=999, seed=42,
    renyi_order_policy="inform_q0_q2", null_tail="two_sided",
    coarse_trim_min_effective_q2=4)
report = assess_lineament_scaling(
    analyzer, np.geomspace(10, 1000, 16), options, support_id="global")
# Choose a new folder if executing this block separately.
write_scaling_reports("outputs/separate_assessment", [report])
~~~

### Documented result

| q | Dq | tau(q) | State |
| --- | --- | --- | --- |
| 0 | 0.986590392615 | −0.986590392615 | compatible_finite_range |
| 1 | 0.991085087024 | 0 | compatible_finite_range |
| 2 | 0.993307136312 | 0.993307136312 | compatible_finite_range |

All 16 requested scales are retained. The minimum effective-q2 threshold is
checked, but it removes no scale in this case. The relocation status is
complete with 999 valid contrasts. Observed D0−D2 is −0.006716743697;
two-sided p = 0.944 and p_Holm = 0.944 for this one-support family. Minimum
raw p is 0.002. The decision at 0.05 is nonrejection.

The small negative D0−D2 is retained rather than clipped. The selected order
policy permits that finite-range contrast with its recorded order diagnostics;
it does not disable fit, curvature, or support checks. Nonrejection says only
that this case did not reject the specified conditional relocation model.
It is not proof of homogeneity or of monofractality.

### Recognize an abstention

Using the same analyzer/options but requesting only [100,150,200,250] gives
too few scales and less than one decade. The expected Dq state is
insufficient_information with no dimension, and the null receives no p value.
This example can be checked without running a relocation ensemble:

~~~python
short = assess_lineament_scaling(analyzer, [100, 150, 200, 250], options)
for row in short["q_results"]:
    assert row["status"] == "insufficient_information"
    assert row["dimension"] is None
assert short["null"]["p_value"] is None
~~~

Keep that outcome; do not change an interval after seeing a result merely to
obtain a supported curve. See [USER_GUIDE.md](USER_GUIDE.md) for all options,
states, and relocation-failure conditions.

## Case B: the same assessment in QGIS Processing

Use the MUSA 1.2.0 plugin with QGIS 3.44.12, the checked runtime. This is the
independent Processing tool, not the descriptive Workbench's Run MUSA workflow.

1. Install/enable the matching plugin ZIP as described in
   [INSTALLATION.md](INSTALLATION.md).
2. Reuse inputs.gpkg generated in Case A. To generate inputs without running
   Python assessment, use a new directory:

~~~text
python examples/scaling_tutorial.py --output outputs/scaling_inputs_only --prepare-only
~~~

3. In QGIS, add both lineaments and boundary from the generated GeoPackage.
   Set the project CRS from the lineaments layer. Retain its custom
   **MUSA synthetic UNLOCATED tutorial** projected CRS; do not assign a real
   geographic location to this example.
4. Open Processing Toolbox and search **Assess Renyi scaling support
   (experimental)** under MUSA. Its identifier is musa:scaling_support.
5. Enter the following values. Copy the exact SCALES string from protocol.json,
   field processing.SCALES, to avoid manual rounding differences.

| Processing field / parameter key | Value |
| --- | --- |
| Lineaments / LINES | Generated lineaments layer |
| Analysis boundary / BOUNDARY | Generated boundary layer |
| Analysis CRS / CRS | Same projected CRS as the generated layers |
| Fixed box sizes / SCALES | 16 values from 10 to 1000, exactly as protocol.json |
| Observation resolution / RESOLUTION | 1 |
| q minimum / Q_MIN | 0 |
| q maximum / Q_MAX | 2 |
| q step / Q_STEP | 1 |
| Conditional trace-relocation replicates / NULL_REPLICATES | 999 |
| Renyi order policy / RENYI_ORDER_POLICY | Inform q=0,2: warning without order veto (index 1) |
| Monte Carlo tail / NULL_TAIL | Two-sided (index 1) |
| Coarse-end trimming / COARSE_TRIM | 4 |
| Random seed / SEED | 42 |
| New output folder / OUTPUT | A new folder, for example outputs/scaling_qgis |

6. Run the tool. Check its progress and completion. The standalone tool does
   not require the descriptive global spectrum to pass its filter.
7. Inspect run_manifest.json status=complete and scaling_support.json. Read
   supports[0].q_results and supports[0].null. Expect the same states,
   Dq/tau values, 999 saved null contrasts, and p = 0.944 as Case A, within
   the documented numerical tolerance. The manifest and host provenance differ
   between execution routes and should not be compared byte-for-byte.
8. Open scaling_support.csv and the saved spectral index/summary. Check each
   observable's state rather than interpreting a Dq state as approval of the
   entire spectrum. Keep outputs and generated inputs together.

### Optional QGIS Python-console equivalent

Set repository to your checkout and generated to the input directory you chose.
These paths are illustrative and contain no machine-specific drive names:

~~~python
import json
from pathlib import Path
import processing
from qgis.core import QgsCoordinateReferenceSystem

repository = Path("path/to/MUSA").resolve()
generated = repository / "outputs/scaling_tutorial"
parameters = json.loads((generated / "protocol.json").read_text(encoding="utf-8"))["processing"]
parameters.update(
    LINES=str(generated / "inputs.gpkg") + "|layername=lineaments",
    BOUNDARY=str(generated / "inputs.gpkg") + "|layername=boundary",
    CRS=QgsCoordinateReferenceSystem((generated / "crs.wkt").read_text(encoding="utf-8")),
    OUTPUT=str(repository / "outputs/scaling_qgis_console"),
)
result = processing.run("musa:scaling_support", parameters)
print(result["REPORT"])
~~~

Select a new output folder on each execution. For your own maps, replace the
synthetic geometry, CRS, observation polygon, resolution, and scale design
with justified inputs before analysis. Retain the null's shape inventory and
the complete requested-support family. This tutorial demonstrates execution
and reproducibility, not a universal interpretation of fracture maps.
