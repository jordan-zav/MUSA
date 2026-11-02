# Referencias cientificas

Esta lista separa fundamentos, antecedentes y validación de MUSA. Citar un trabajo no significa que se haya implementado cada algoritmo de ese artículo ni que sus resultados se reproduzcan automáticamente.

## Fundamentos y correspondencia con el código

- Hentschel, H. G. E. y Procaccia, I. (1983). The infinite number of generalized dimensions of fractals and strange attractors. [DOI](https://doi.org/10.1016/0167-2789(83)90235-X). Base de la familia de dimensiones generalizadas Dq; en MUSA se estiman a escalas finitas.
- Halsey, T. C. y colaboradores (1986). Fractal measures and their singularities: The characterization of strange sets. [DOI](https://doi.org/10.1103/PhysRevA.33.1141). Formalismo de singularidades y relación entre tau, alpha y f(alpha), sujeto a las hipótesis indicadas en la teoría.
- Chhabra y Jensen (1989), referencia 1: medida auxiliar y estimación directa de alpha(q) y f(q). Es la correspondencia principal con los integrandos canónicos del motor; no implica que una curva finita pruebe multifractalidad.

El peso zeta, los umbrales del diagnóstico, los controles de origen y las reglas de clasificación son decisiones operacionales documentadas en [teoría](theory.md), [diagnóstico de escalamiento](SCALING_SUPPORT.md) y [estado de validación](SCALING_VALIDATION_STATUS.md). No se atribuyen como una certificación científica de los artículos anteriores.

## Antecedentes de aplicaciones y métodos relacionados

Los trabajos sobre redes ponderadas ofrecen contexto. El análisis geométrico de longitud en cajas no debe identificarse con un algoritmo sandbox sobre distancias de grafo.

1. Chhabra, A. y Jensen, R. V. 1989. Direct determination of the f alpha singularity spectrum. Physical Review Letters. DOI: https://doi.org/10.1103/PhysRevLett.62.1327
2. Liebovitch, L. S. y Toth, T. 1992. Estimation of the f alpha spectrum from simulated and measured time series. Chaos, Solitons and Fractals. DOI: https://doi.org/10.1016/0960-0779(92)90023-G
3. Liu, Z. y colaboradores. 2021. Fractal and Multifractal Characteristics of Lineaments in the Qianhe Graben and Its Tectonic Significance Using Remote Sensing Images. Remote Sensing. DOI: https://doi.org/10.3390/rs13040587
4. Ni, C. y colaboradores. 2017. Mapping the Spatial Distribution and Characteristics of Lineaments Using Fractal and Multifractal Models. Scientific Reports. DOI: https://doi.org/10.1038/s41598-017-11027-0
5. Casas, A. M. y colaboradores. 2000. LINDENS: A program for lineament length and density analysis. Computers and Geosciences. DOI: https://doi.org/10.1016/S0098-3004(00)00017-0
6. Mondragon-Nava, H. y colaboradores. 2023. Fractal Features of Fracture Networks and Key Attributes of Their Models. Fractal and Fractional. DOI: https://doi.org/10.3390/fractalfract7070509
7. Fractal and multifractal analysis of fractured geological media: surface-subsurface correlation. 1999. Computers and Geosciences. Fuente: https://www.sciencedirect.com/science/article/pii/S0098300499000692
8. Zhu, W. y colaboradores. 2022. Fractal and multifractal characterization of stochastic fracture networks and real outcrops. Journal of Structural Geology. DOI: https://doi.org/10.1016/j.jsg.2021.104508
9. Xue, Y. y Bogdan, P. 2017. Reliable Multi-Fractal Characterization of Weighted Complex Networks: Algorithms and Implications. Scientific Reports. DOI: https://doi.org/10.1038/s41598-017-07209-5
10. Wei, D. y colaboradores. 2014. Multi-fractal analysis of weighted networks. arXiv. DOI: https://doi.org/10.48550/arXiv.1402.7246
11. Song, Y. Q. y colaboradores. 2015. Multifractal analysis of weighted networks by a modified sandbox algorithm. Scientific Reports. DOI: https://doi.org/10.1038/srep17628

## Datos públicos y reproducción

La procedencia, licencias, adaptaciones y límites efectivos de las fuentes están en [benchmarks de autores](AUTHOR_BENCHMARKS.md) y [validación ampliada](EXTENDED_BENCHMARKS.md). Son la referencia para saber qué se descargó y procesó; un artículo citado no garantiza que sus coordenadas originales estén disponibles.

La cascada sintética prueba identidades numéricas en una construcción conocida. Los afloramientos publicados permiten contrastar comportamiento sobre cartografía real. Son evidencias diferentes y ninguna demuestra por sí sola validez universal o conectividad hidráulica.
