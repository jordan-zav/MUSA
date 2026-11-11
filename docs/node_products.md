# Nodes and Pathway: usage contract

node_classes is the descriptive node product. node_class distinguishes
1-1, 1-2, 1-3, 2-2, 2-3, and 3-3 by participating interpreted orders.
node_kind separates planar intersections from noncrossing proximity.
Multiple pairs remain multiple_pairs; shared orders remain
ambiguous_classification. The most favorable pair is not selected automatically.
participant_faults_json recovers participating faults and original records.

node_weight comes from node_weights.json: w(n) = w[class(n)]. Every pair
initially has weight 1: a neutral reference, not calibration. Ambiguous,
multiple, or unknown classes have null weight, not zero. Filter crossings and
proximities separately when using weights. Any pair can receive another explicit
weight under a justified external policy; MUSA assigns no universal geological
priority to a pair. No multiplication by angle, ζ, or multifractal score is applied.

structural_trap_class is a reserved, unevaluated field. Additional geological
rules require independent context/validation explicitly supplied by the user.
Class 1-2 alone proves neither dilation nor permeability. No project-specific
geological rule is included.

pathway_multifractal retains continuous window contrast:

- pᵢ(r) = lengthᵢ(r) / total window length.
- μᵢ(q,r) = pᵢ(r)^q / Σⱼpⱼ(r)^q, over occupied boxes.
- α(q) = slope of origin_average[Σᵢ μᵢ ln(pᵢ)] against ln(r/L).
- H = α(0) − α(2), field multifractal_contrast.

Configured window sizes remain separate through window_m; no universal set of
three sizes suits every map. Do not sum them as independent observations.
contrast_usable and support_reason accompany H; negative values remain
diagnostics, not unfavorable evidence or zero. Coverage is provisional.
This is a window product, not a validated 500 m RF raster. ζ weights numerical
fit reliability in weighted diagnostics, not geological favorability, and does
not replace origin sensitivity.

trap_candidates retains historical results for compatibility. Its score is a
relative rank: S = 100 × median(percentiles against comparable background).
evidence_class and relative_class are not geological node classes. Experimental
KDE intensity uses those scores by distance and remains a separate Pathway
variable; it is not multiplied by a geological node weight.

| Product | Use | Status |
| --- | --- | --- |
| node_class + node_kind | Structural categories and explicit weights | Descriptive |
| structural_trap_class | Reserved for externally validated rules | Unevaluated |
| pathway_multifractal | Continuous window H with support | Experimental |
| candidate_contrast_intensity | Relative-rank KDE | Experimental; requires coverage and spatial validation |

To update classes/weights without rerunning multifractal calculation, use
export_products from musa.node_classes on your own compatible GeoPackage with
an explicit weight policy. The function modifies that file: work on an output
copy, not a closed deliverable. Project-specific launchers, data, and rules
remain outside the general software distribution.

A high R² for a parabola on f(α) does not replace evaluating slopes across box
sizes. High q emphasizes concentrated mass, not prospectivity. See
candidate_scoring.md for the full mathematics and limits.
