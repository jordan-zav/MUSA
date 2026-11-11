# Scientific references

This list separates foundations, related work, and MUSA validation. Citing a
paper does not mean every algorithm in it is implemented or its results
automatically reproduced.

## Foundations and correspondence with the code

- Hentschel, H. G. E., and Procaccia, I. (1983). The infinite number of generalized dimensions of fractals and strange attractors. [DOI](https://doi.org/10.1016/0167-2789(83)90235-X). Foundation for generalized dimensions Dq; MUSA estimates them at finite scales.
- Halsey, T. C., and colleagues (1986). Fractal measures and their singularities: The characterization of strange sets. [DOI](https://doi.org/10.1103/PhysRevA.33.1141). Singularity formalism and tau/alpha/f(alpha) relationships under the assumptions stated in theory.
- Chhabra and Jensen (1989), reference 1: auxiliary measure and direct alpha(q)/f(q) estimation. This is the main correspondence with the core's canonical integrands; a finite curve is not proof of multifractality.

Zeta weights, assessment thresholds, origin controls, and classification rules
are operational decisions documented in [theory](theory.md),
[scaling assessment](SCALING_SUPPORT.md), and
[validation status](SCALING_VALIDATION_STATUS.md). They are not attributed as
scientific certification by the foundational papers.

## Applications and related methods

Weighted-network studies provide context. Geometric box-based length analysis
is not a sandbox algorithm on graph distances.

1. Chhabra, A., and Jensen, R. V. 1989. Direct determination of the f alpha singularity spectrum. Physical Review Letters. DOI: https://doi.org/10.1103/PhysRevLett.62.1327
2. Liebovitch, L. S., and Toth, T. 1992. Estimation of the f alpha spectrum from simulated and measured time series. Chaos, Solitons and Fractals. DOI: https://doi.org/10.1016/0960-0779(92)90023-G
3. Liu, Z., and colleagues. 2021. Fractal and Multifractal Characteristics of Lineaments in the Qianhe Graben and Its Tectonic Significance Using Remote Sensing Images. Remote Sensing. DOI: https://doi.org/10.3390/rs13040587
4. Ni, C., and colleagues. 2017. Mapping the Spatial Distribution and Characteristics of Lineaments Using Fractal and Multifractal Models. Scientific Reports. DOI: https://doi.org/10.1038/s41598-017-11027-0
5. Casas, A. M., and colleagues. 2000. LINDENS: A program for lineament length and density analysis. Computers and Geosciences. DOI: https://doi.org/10.1016/S0098-3004(00)00017-0
6. Mondragon-Nava, H., and colleagues. 2023. Fractal Features of Fracture Networks and Key Attributes of Their Models. Fractal and Fractional. DOI: https://doi.org/10.3390/fractalfract7070509
7. Fractal and multifractal analysis of fractured geological media: surface-subsurface correlation. 1999. Computers and Geosciences. Source: https://www.sciencedirect.com/science/article/pii/S0098300499000692
8. Zhu, W., and colleagues. 2022. Fractal and multifractal characterization of stochastic fracture networks and real outcrops. Journal of Structural Geology. DOI: https://doi.org/10.1016/j.jsg.2021.104508
9. Xue, Y., and Bogdan, P. 2017. Reliable Multi-Fractal Characterization of Weighted Complex Networks: Algorithms and Implications. Scientific Reports. DOI: https://doi.org/10.1038/s41598-017-07209-5
10. Wei, D., and colleagues. 2014. Multi-fractal analysis of weighted networks. arXiv. DOI: https://doi.org/10.48550/arXiv.1402.7246
11. Song, Y. Q., and colleagues. 2015. Multifractal analysis of weighted networks by a modified sandbox algorithm. Scientific Reports. DOI: https://doi.org/10.1038/srep17628

## Public data and reproduction

Provenance, licenses, adaptations, and actual source limits are documented in
[author benchmarks](AUTHOR_BENCHMARKS.md) and
[extended validation](EXTENDED_BENCHMARKS.md). Those documents identify what
was downloaded and processed; a citation does not guarantee original
coordinates are available.

The synthetic cascade tests numerical identities for a known construction.
Published outcrops test behavior on real mapping. These are different forms of
evidence; neither alone establishes universal validity or hydraulic connectivity.
