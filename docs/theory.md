# MUSA theory and methodology

Reference for MUSA 1.2.0, revised November 10, 2026. The Python engine and QGIS
plugin use these operations; descriptive and assessment paths apply different
criteria. This reference replaces older notes mixed with Tk-interface controls.

## 1. Domain, measure, and scales

Let Ω be the observed domain and ε the side of a grid box. MUSA analyzes
spatial 2D data:

| Input | Measure mᵢ(ε) |
| --- | --- |
| Points | Number of points in the box |
| Lineaments | Trace length inside both the box and domain |

Ordinary GIS line coordinates must use a metric projection. Changing a CRS
label does not reproject coordinates. Default point normalization scales each
axis to its observed range; it can change aspect ratio and preserves neither
meters nor physical distances. Disable it when those coordinates must be retained.

At each scale, occupied boxes are normalized:

$$
p_i(\varepsilon)=\frac{m_i(\varepsilon)}{\sum_{j:m_j>0}m_j(\varepsilon)}.
$$

Empty boxes do not enter negative moments as zero probabilities. A descriptive
per-box length threshold can remove boxes and change the measure; it applies
to total accumulated box length, not each segment. Record and justify it.

Duplicate handling differs by path: descriptive preparation does not guarantee
a single union of all segments; moving windows dissolve exact coincidences;
independent assessment rejects coincident multiplicity. Harmonize and document
preprocessing before comparing results.

A finite nonempty collection of straight segments has asymptotic geometric
dimension 1. A network's estimated Dq >1 describes organization over an
observable interval, not proof of a fractal map limit.

## 2. Generalized Rényi dimensions and mass exponent

For q other than 1, the partition function is:

$$
Z_q(\varepsilon)=\sum_i p_i(\varepsilon)^q.
$$

If scaling exists over an interval:

$$
Z_q(\varepsilon)\sim\varepsilon^{\tau(q)},\qquad
D_q=\frac{\tau(q)}{q-1}.
$$

MUSA estimates Dq as the slope of Rényi entropy against x = ln(1/ε):

$$
H_q(\varepsilon)=\frac{\ln Z_q(\varepsilon)}{1-q}.
$$

Limiting cases avoid division by zero:

$$
H_0(\varepsilon)=\ln N_{\rm occupied}(\varepsilon),
\qquad
H_1(\varepsilon)=-\sum_i p_i(\varepsilon)\ln p_i(\varepsilon).
$$

D0 is the capacity slope, D1 information, and D2 correlation associated with
this box measure. Do not confuse length-per-box D2 with a fracture-centroid
correlation estimate: changing the object/measure can change the comparison.

The exported exponent is τ(q) = (q−1)Dq. At q=1, τ(1)=0 is a normalization
identity, not evidence of a fitted line or a reason to invent R².

| Order q | Emphasis |
| --- | --- |
| Negative q | Low-probability occupied boxes; greater resolution/small-fragment sensitivity |
| q=0 | Number of occupied boxes |
| q=1 | Shannon entropy |
| Increasing positive q | Concentration in high-probability boxes |

Dq is nonincreasing under the appropriate theoretical assumptions and conveys
more than a single dimension. Finite slopes can depart from this ordering
through interval, sampling, or grid effects; assessment records inconsistencies.
Varying q neither makes a 2D analysis 3D nor jointly analyzes different variables.

## 3. Direct singularity spectrum

The canonical Chhabra–Jensen estimator uses auxiliary probabilities:

$$
\mu_i(q,\varepsilon)=\frac{p_i(\varepsilon)^q}{Z_q(\varepsilon)}.
$$

Its integrands are:

$$
A_q(\varepsilon)=\sum_i\mu_i\ln p_i,\qquad
F_q(\varepsilon)=\sum_i\mu_i\ln\mu_i.
$$

Alpha(q) and f(alpha(q)) are the respective slopes of A and F against ln ε.
Equivalently, negate both integrands and use ln(1/ε). Descriptive analysis uses
the former convention for alpha/f; assessment uses the latter. Do not change
only the axis sign.

Direct calculation avoids a numerical derivative of τ for alpha. The Legendre
relation alpha = dτ/dq requires the same measure and regularity assumptions;
it is not MUSA's alpha-estimation algorithm.

Consistent calculations are checked against:

$$
\tau(q)=(q-1)D_q,\qquad f(\alpha(q))=q\alpha(q)-\tau(q).
$$

These algebraic identities help detect implementation inconsistencies; satisfying
them does not establish scaling in data. Assessment checks Dq against planar
support; it neither automatically imposes the same bound on alpha nor rejects
negative τ solely because of its sign.

Weights are evaluated in the log domain to prevent overflow. The effective
number of boxes emphasized by q is:

$$
N_{\rm eff}(q,\varepsilon)=\frac{1}{\sum_i\mu_i^2}.
$$

If nearly all weight belongs to one box, support can be insufficient despite
an apparently high R².

## 4. Three different singularity references

| Reference | Definition |
| --- | --- |
| Alpha at q=0 | Evaluated, usable q=0 value; no interpolation from a neighboring q |
| Observed maximum | Alpha at largest f among usable points; retains ties and flags endpoints |
| Quadratic peak | Vertex of a descriptive f(alpha) fit, subject to range, concavity, and degeneracy checks |

Do not use mode without specifying the reference. A quadratic vertex is not
the mode of an alpha histogram. With exactly three points, the parabola is
labeled descriptive interpolation. A nonconcave/degenerate fit or an out-of-range
vertex leaves the peak absent.

Delta alpha is the observed range across usable q, not an extrapolated width
at infinite q. Curves connect in q order and break at rejected points; sorting
alpha must not hide reversals or gaps. See [SPECTRA.md](SPECTRA.md).

## 5. Two calculation paths and quality contracts

| Aspect | analysis: descriptive workflow | assessment: independent assessment |
| --- | --- | --- |
| Main entry | run_analysis / execute_analysis | assess_lineament_scaling / musa:scaling_support |
| Goal | Estimate/export spectra and local products | Assess compatibility over a declared interval |
| Origins | Descriptive global partition origin; windows: one or optional 16 | Four fixed shifted origins |
| Global filter | R² of Dq, alpha, and f above min_r2 | Resolution, scales, coverage, support, stability, and models |
| Zeta | Separate local estimators | Not applied |
| Probability floor | Optional at negative q | Not applied |
| Rejected q | Recorded; workflow can fail with fewer than two accepted | All q/reasons retained even when none are supported |

run_analysis uses strict inequalities in its triple R² filter; the default is
0.9. RunConfig requires at least four internal divisors, a technical condition
that does not certify a sufficient scaling interval.

ScalingOptions applies these defaults:

- Positive observation resolution declared by the person who knows the data.
- Scales at least that resolution and at most one quarter of the support's shorter side.
- At least eight remaining scales and a one-decade span.
- At least 80% observed nominal area and two effective boxes.
- Linear R² >=0.98; maximum slope variation 0.10 under scale omission/end trimming and origin changes.
- Quadratic/segmented comparisons through leave-one-scale-out prediction, reselecting the breakpoint inside every training fold without the held-out value.

An alternative is flagged when its predictive improvement meets the recorded
criteria. No favorable subinterval is searched afterward. Curves are averaged
across four origins before fitting; per-origin sensitivity is retained.

| State | Scope |
| --- | --- |
| compatible_finite_range | Meets operational criteria over that interval |
| not_supported | Sufficient observations, but fit/stability/shape criteria fail |
| insufficient_information | Inadequate resolution, coverage, span, scale count, or effective support |

Each observable has its own state. Compatible Dq does not assure supported
alpha/f(alpha). Rejected numerical values can remain for audit; absent values
are not zero.

A periodic grid can appear compatible over a finite interval. An extended
control detected its crossover after including characteristic spacing. These
states are not universal fractal/nonfractal classifications. See
[SCALING_SUPPORT.md](SCALING_SUPPORT.md).

## 6. Mother cells, moving windows, and coverage

Mother cells form the descriptive local partition. Their side is that
workflow's maximum resolution; strictly smaller children feed the regression.
Probabilities normalize within each mother cell.

The historical path assigns children by centroid. With manually supplied
incompatible scales, a child can cross a mother boundary and its mass need
not equal an exact mother-cell clip. Mother/divisor resolution construction
helps define a compatible grid.

Moving windows separate side L, center spacing, and internal ε = L/divisor.
They clip lines to observed support and calculate probabilities within each
window. Multiple origins and separate canonical/weighted estimates can be
retained. They are experimental and do not require each q to pass the global
fit to calculate their own estimates; execute_analysis still must finish its
earlier global stage.

Area coverage is area(window ∩ Ω)/L². It is not the occupied-box proportion
within zeta. A quadrant of an inscribed circle has coverage π/4 ≈0.785, below
the 0.8 minimum. This geometric insufficiency is not resolved by filling data
outside the domain.

Benchmarks retain quadrants and add geometrically declared interior centers.
Overlapping windows share information: they are neither independent replicates
nor suitable for uncontrolled training/test partitioning. See
[moving_windows.md](moving_windows.md).

## 7. Operational zeta weighting

Zeta weights local scales; it replaces neither measure probabilities nor
constitutes another multifractal dimension. The code's operational form is:

$$
\zeta(\varepsilon)=C^{a}R^{b}S^{c}E^{d}.
$$

| Factor | Calculation |
| --- | --- |
| C | Occupied boxes / possible support boxes at that scale |
| R | Local mass at that scale / local mass at the finest scale |
| S | Floor + (1−floor) × ln(ε_coarse/ε) / ln(ε_coarse/ε_fine), with position clipped to [0,1] |
| E | exp(H1) / occupied-box count, clipped to [0,1] |

Default exponents are (1,1,1,1); the scale floor is 0.25. E measures mass
dispersion through Shannon entropy, not the auxiliary weights' N_eff(q).
With full length conservation, R should be approximately 1; thresholds or
preparation can change it.

Aligned mother cells use the squared rounded divisor for possible boxes.
Offset moving windows use their corresponding possible-box count; partial
boxes are not automatically equal-area exposures. Examine boundary sensitivity
separately.

Weighted regression retains alpha_w, f_alpha_w, and weighted Dq where available,
separately from canonical values. reliable adds its product's zeta/R² thresholds;
it is not a calibrated probability. The [candidate guide](candidate_scoring.md)
describes the experimental profile without introducing a prospectivity score.

## 8. Stabilization, robustness, and uncertainty

The optional negative-q floor changes p before descriptive calculation.
For N occupied boxes and configured fraction η, the code uses:

$$
p_{\min}=\min\left(\frac{0.5}{N},\frac{\eta\max(|q|,1)}{N}\right),\qquad
p'_i=\frac{\max(p_i,p_{\min})}{\sum_j\max(p_j,p_{\min})}.
$$

η=0 disables it. Because it depends on q, this regularization does not strictly
preserve one unchanged measure across all moments; report it and compare with
the untreated path. Independent assessment keeps the original measure and
checks dominance instead.

For any η >0 and q <0, Hq(p′) − ln N is bounded by a scale-independent constant.
If a scaling regime exists, the regularized slope therefore tends to D0: the
floor cannot preserve a negative-order spectrum distinct from D0. See the
derivation and known-truth evaluation in [negative q](NEGATIVE_Q.md).

Scale bootstrap, jackknife, Theil–Sen, leverage, and Cook's distance examine
fit sensitivity. They do not themselves represent mapping/tracing uncertainty
or spatial independence. A descriptive slope p value is neither the spatial
null test nor a probability of fractality.

## 9. Conditional spatial test

When requested, assessment compares T = D0−D2 with independent uniform
translations of supplied trace shapes contained in the same polygon.
Shape, length, orientation, count, and mass are preserved; positions,
crossings, and spatial dependence change.

If input was noded through geometric union, the preserved units are those
parts, not necessarily originally interpreted fractures. Declare that inventory.

With B valid replicates and the upper tail:

$$
p=\frac{1+\#\{T_{\rm sim}\ge T_{\rm obs}\}}{B+1}.
$$

null_tail="two_sided" reports p = min(1, 2 min(p_upper, p_lower)), where p_lower
counts T_sim ≤ T_obs; ties count against rejection and minimum p is 2/(B+1).
coarse_trim_min_effective_q2 is disabled at 0. Otherwise it removes scales from
the coarse end on the observed map only, before any replicate, until the
coarsest retained scale has at least that many effective q=2 boxes. With less
than a decade remaining, the test is not calculated.

Uncomfortable simulations are not discarded until a favorable result appears.
Failed placement or unsupported q0/q2 produces no invented p value. Holm adjusts
the report's support family; an additional benchmark family must be declared
separately. Correlated q values are not additional independent tests.

The test concerns conditional heterogeneity under that translation model.
Rejection does not prove multifractality; nonrejection proves neither homogeneity
nor absence of structure. General calibration and power remain outstanding.

## 10. Spatial descriptors and topology

Length recorded at the finest scale supports structural intensity over observed
area. Lengths of the same network repeated over scales are not additional mass.

Historical d_local_index = −ln(pᵢ)/ln(L/ε) is a one-scale local quotient, not a
Dq regression or an established physical dimension.

Moving topology obtains unique nodes from exact planar union: I=end,
Y=degree 3, X=degree 4, complex=higher degree. The historical network.py graph
counts lines/related pairs, not the same geographic-node inventory. Without
snapping, near crossings stay separate. Neither a planar crossing nor proximity
verifies 3D hydraulic connectivity.

## 11. Evidence and interpretation limits

The partition/canonical-calculation core was compared with a 2D dyadic-weight
cascade of 65,536 segments: maximum Dq/τ/alpha/f error approximately
2.09 × 10⁻¹⁴ on an aligned grid at finite scales. This algebraic/geometric
test does not certify accuracy for every origin, resolution, or map.

Extended validation includes 67 processable public-source cases, models,
variants, and controls, not 67 independent outcrops. Empty masks and unavailable
sources retain their actual states. Raster-figure, centroid, line, and weighted-
measure comparisons require matching domains and measures.

Three levels of claim must stay separate:

1. Formulas, conservation, and numerical consistency checked on defined controls.
2. Compatibility with a model over a resolvable interval, with explicit quality/sensitivity.
3. Physical/geological interpretation validated through external evidence.

MUSA integrates calculations and diagnostics at the first two levels. It does
not automatically convert outputs into permeability, favorability, 3D
connection, or a universal multifractality test.

## Related guides

- [Architecture](ARCHITECTURE.md): shared core and bundled plugin snapshot.
- [Python API](PYTHON_API.md): headless examples and execution contracts.
- [Outputs](OUTPUTS.md): files, fields, units, and states.
- [Support spectra](SPECTRA.md): sources and singularity references.
- [Validation scope](SCALING_VALIDATION_STATUS.md) and [public benchmarks](EXTENDED_BENCHMARKS.md).
- [Scientific references](references.md): distinguish implemented methods, related work, and data sources.
