# Documentación de MUSA

Empieza por la ruta que necesitas: [instalación](INSTALLATION.md),
[motor y QGIS](ARCHITECTURE.md) o [API Python sin QGIS](PYTHON_API.md).
La referencia matemática vigente es [theory.md](theory.md).
Versión actual: MUSA 1.2.0. La publicación en PyPI sigue pendiente.

## Archivos principales

| Archivo | Rol |
| --- | --- |
| [USER_GUIDE.es.md](USER_GUIDE.es.md) | Manual ilustrado en español: instalación, ejemplo, resultados, scroll y exportación |
| [INSTALLATION.md](INSTALLATION.md) | Instalación desde Git, ZIP QGIS, dependencias y estado de PyPI/terminal |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Responsabilidades del núcleo, flujo común e instantánea privada del plugin |
| [PYTHON_API.md](PYTHON_API.md) | Puntos, líneas, recetas, diagnóstico independiente y lectores de resultados |
| [OUTPUTS.md](OUTPUTS.md) | Archivos, columnas, unidades, estados y uniones de tablas |
| [theory.md](theory.md) | Referencia técnica del algoritmo global, local, zeta y salidas |
| [references.md](references.md) | Referencias científicas públicas |
| [QGIS.md](QGIS.md) | Instalación del plugin, panel en inglés, recetas y Processing |
| [SCALING_SUPPORT.md](SCALING_SUPPORT.md) | Criterios del diagnóstico independiente de escalamiento |
| [SPECTRA.md](SPECTRA.md) | Fuentes analysis/assessment y referencias de singularidad |
| [moving_windows.md](moving_windows.md) | Ventanas solapadas, orígenes y topología |
| [candidate_scoring.md](candidate_scoring.md) | Perfil experimental de contraste relativo y zeta |
| [node_products.md](node_products.md) | Postproceso de nodos; no es una regla geológica universal |
| [SCALING_VALIDATION_STATUS.md](SCALING_VALIDATION_STATUS.md) | Evidencia numérica y validación científica pendiente |
| [EXTENDED_BENCHMARKS.md](EXTENDED_BENCHMARKS.md) | Fuentes públicas, casos, resultados y límites de la suite ampliada |
| [NEGATIVE_Q.md](NEGATIVE_Q.md) | Evaluación de q negativos con verdad conocida; el piso lleva los q negativos a D0 |
| [GRID_GEOMETRY.md](GRID_GEOMETRY.md) | Experimento: celdas cuadradas frente a hexagonales y rotación de la malla; prototipo fuera del motor |
| [AUTHOR_BENCHMARKS.md](AUTHOR_BENCHMARKS.md) | Primera suite de controles y mapas de autores |

Los borradores locales, originales
de autores, bitácoras de descarga y resultados voluminosos permanecen fuera del
paquete del plugin. La presencia de un archivo en Git no implica que el
constructor del ZIP lo incluya.

Los datos, resultados y entregas de proyectos privados se mantienen fuera
del repositorio. No son productos de MUSA ni material autorizado para ejemplos,
benchmarks o publicación del software. Esta documentación describe métodos,
interfaces, controles sintéticos y validación con fuentes públicas identificadas.
Las pruebas numéricas no convierten una inferencia geológica en validación externa.
