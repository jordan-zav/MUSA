# MUSA: Multifractal Spectrum Analyzer

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

MUSA es una herramienta Python para análisis fractal y multifractal de datos espaciales, con flujo GIS para lineamientos geológicos.

## Algoritmos listos

| Bloque | Estado | Salidas principales |
| --- | --- | --- |
| Espectro multifractal global | Listo | Dq, tau, alpha, f alpha, diagnósticos por escala |
| Chhabra Jensen local por celda madre | Listo | alpha, f alpha por ventana madre |
| Ponderación zeta multiescala | Listo | alpha_w, f_alpha_w, zeta_mean, zeta_min |
| Filtro reliable | Listo | bandera reliable por madre y q |
| Monofractal local | Listo | D0 local, D1 local, versiones ponderadas y robustas |
| Bootstrap y jackknife | Listo | intervalos y sensibilidad leave one scale out |
| Theil Sen robusto | Listo | alpha_ts, f_alpha_ts, D0_ts, D1_ts |
| Diagnósticos de leverage y Cook | Listo | CSV global y local por escala |
| Sensibilidad de zeta | Listo | perfiles baseline, coverage heavy, mass heavy, scale heavy, neff heavy y soft |
| Estadística estructural | Listo | densidad, longitud total, orientación dominante y anisotropía |
| Conectividad de lineamientos | Experimental listo | componentes, intersecciones y densidad de red |
| Export GIS | Listo | GeoPackage de celdas madre y capas reliable |
| Paquete de corrida | Listo | ZIP organizado por categorías |
| Validación sintética | Listo | resumen por escenarios controlados |

## Lectura metodológica

La contribución defendible de MUSA no es inventar la multifractalidad de lineamientos. Esa línea ya existe. La novedad está en combinar:

* Chhabra Jensen directo global y local.
* Recálculo de probabilidades dentro de cada celda madre.
* Ponderación local por zeta como confiabilidad multiescala.
* Separación explícita entre densidad estructural, complejidad multifractal y confiabilidad.
* Exportación GIS reproducible para mapas e interpretación geológica.

*Zeta debe interpretarse como peso operativo de confiabilidad, no como propiedad física directa.*

## Flujo recomendado

1. Definir lineamientos y límite de análisis en CRS métrico o permitir reproyección automática.
2. Elegir una celda madre y resoluciones hijas suficientes para regresión.
3. Ejecutar el análisis global.
4. Exportar celdas madre locales con zeta y reliable.
5. Comparar densidad, orientación, alpha, alpha_w y reliable.
6. Usar validación sintética y sensibilidad de zeta antes de sostener conclusiones geológicas fuertes.

## Documentación vigente

| Archivo | Uso |
| --- | --- |
| docs/theory.md | Definición técnica completa del método |
| docs/references.md | Referencias científicas públicas |

## Resultados y corridas

Los resultados generados se excluyen del control de versiones para evitar publicar datos de trabajo o artefactos temporales.

## Entrada y uso desde Python

El paquete expone MUSA, MUSAResult, resolutions_from_mother_cell, export_analysis_plots, export_mother_plots, export_mother_geopackage, package_run_output, run_synthetic_validation, compute_lineament_mother_structural_stats y compute_lineament_network_stats.

Para lineamientos GIS se debe usar data como capa de líneas, boundary como límite de análisis y resolutions_m en metros. El análisis por celdas madre se obtiene con export_cell_outputs usando aggregate_to_mother activado.

## Interfaz

La interfaz de escritorio se lanza con musa-ui cuando el paquete está instalado en modo editable o normal.
