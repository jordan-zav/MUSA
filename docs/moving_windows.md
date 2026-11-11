# Multiscale moving windows (experimental)

The backend also produces trap_candidates with components, an exploratory
score, separate quality information, and symbology. See the
[formula and intersection angles](candidate_scoring.md).

In the QGIS **Moving windows** tab, enable windows. Enter window sides in
meters, center spacing, and at least four integer internal divisors. The older
mode remains available and also runs for comparison. q values come from the
interface; windows are not removed because a q fails global analysis.

Initial values 2000,4000,8000 m, spacing 1000 m, and divisors 2,4,8,16 are
editable examples, not universal geological scales. Each window L uses boxes
of side L/divisor: check the finest scale against mapping resolution. Reducing
spacing adds no data detail. Harmonize provenance/geometry before combining
layers that repeat the same faults.

The default is one origin per scale. The origin ensemble enables 16; it does
not automatically replace chosen divisors with the research profile's seven.
Four scales do not meet the independent assessment's minimum of eight: declare
another resolvable list and examine its span. See [theory](theory.md).

## Method and controls

- Overlapping square windows clipped to the actual domain, probabilities renormalized within each window, and an unweighted Chhabra–Jensen spectrum.
- Unique trace length: exactly coincident segments are dissolved. Nearby but geometrically different traces are not deduplicated.
- Projected CRS in meters required. Observations are not extended outside the boundary. Default minimum coverage: 80% of the square.
- At least four internal scales and two occupied boxes per scale.
- Dq, alpha, f_alpha, and their R² are reported; default minimum R² is 0.9.
- Log-domain weights. min_effective_boxes is the minimum across scales of 1/sum(mu²); at least two effective boxes are required by default. max_box_weight exposes excessive concentration.
- Rejected estimates retain accepted=false and reason: low_coverage, insufficient_support, dominant_box, or poor_scaling. Constant fits are not evidence of scaling.
- accepted_window_sizes counts sizes with an accepted estimate for each center/q; it does not measure anomaly persistence or success probability.
- Nodes are computed on the whole domain-clipped network: I=end, Y=degree 3, X=degree 4, complex=higher degree. Degree 2 is not exported. Local counts include crossings strictly inside the window and exclude domain-edge nodes. Clipping windows creates no new crossings.
- No automatic snapping. A planar crossing does not prove a 3D connection.
- Default limit: 10000 windows; increase spacing if exceeded.

The experimental profile retains canonical and zeta-weighted estimates with
separate diagnostics. See candidate_scoring.md for factors, parameters, and
support criteria. Zeta is neither a physical property nor geological-validity
probability. No permeability index or hydraulic uncertainty is produced.
Neighboring windows are dependent; do not randomly split them into training/test sets.

## Outputs

- moving_windows.csv: results per center, size, and q, with coverage/crossings.
- moving_nodes.csv: coordinates/degrees of unique nodes.
- moving_windows_config.json: parameters, centers, CRS, and limits.
- musa_moving_windows.gpkg with GIS enabled: window_spectra polygons, structural_candidates (interior crossings), and topology_controls (ends/boundary cuts). The workflow writes a results folder, not an automatic ZIP. Read OUTPUTS.md before packaging it.

The GeoPackage includes QGIS layer_styles: orange triangles for Y, blue diamonds
for X, and purple stars for complex nodes. Controls are small gray crosses.
Windows have no fill; default outlines display q=2 by quality. Change rule
filters for other q values. Also filter window_m to avoid superimposed sizes.
Layer visibility is saved in a QGIS project, not in the GeoPackage.

Candidates include max_branch_angle_deg (largest axial branch-tangent
separation, 0–90°; not tectonic-family identification) and context from containing
windows: context_windows_q2, accepted_context_q2, accepted_sizes_q2, and
context_status_q2. These are not a node-centered spectrum, prospectivity score,
or geological persistence. If q=2 was not assessed, status is not_evaluated.
A geological crossing is not discarded because surrounding windows lack accepted
fits. interpretation records that planar geometry is unvalidated for prospecting.

## Python: regular centers or selected nodes

### Potential interactions by radius

Enable potential radius-based interactions in QGIS **Moving windows**. Radii
100,250,500 m are editable exploratory examples, not verified mapping tolerances
or hydraulic distances. The backend creates potential_relations.csv and, with
GIS enabled, styled potential_relations (dashed connectors by type) and
interaction_search_zones (unfilled dotted outlines).

Pairs of disjoint line parts are examined within the largest radius. One nearest
relation per pair records distance, local tangent axial separation,
end–end/end–trace/trace–trace type, and the first tested radius detecting it.
Geometry is unchanged. Exact-intersection pairs, boundary contacts, and
connectors crossing outside the AOI are excluded. part_a/part_b index prepared
input parts, not independent geological faults. Segmentation/mapping can affect
them; review before interpretation.

matching_radii_m records distance inclusion, not independent persistence or a
score. Zones are midpoint buffers at the first compatible radius, clipped to
the AOI; they represent search, not damage zones. Angles do not establish 3D
connectivity, permeability, or tectonic families. Components are not joined and
proximity does not fabricate connections. An explicit error enforces a limit
of 100000 relations.

In Python, pass proximity_radii_m=[100,250,500] to export_moving_windows.

~~~python
from musa import MUSA, export_moving_windows

musa = MUSA('faults.gpkg', boundary='boundary.gpkg', q_values=[0, 1, 2, 4, 8])
outputs = export_moving_windows(
    musa, 'outputs/windows', window_sizes_m=[2000, 4000, 8000], step_m=1000,
    divisors=[2, 4, 8, 16],
)
# For specific node neighborhoods, pass centers=[(x1, y1), (x2, y2)].
# Coordinates must use the analyzer's active metric CRS.
~~~

Automated checks cover a line's known dimension, exact-duplicate removal,
equal-density networks with different connectivity, translation/segmentation
invariance, boundaries, extreme q, and GIS export. Extended validation includes
public data and identified derivatives; see
[EXTENDED_BENCHMARKS.md](EXTENDED_BENCHMARKS.md). Independent application-specific
evidence is still required before interpreting nodes as favorable for flow.
