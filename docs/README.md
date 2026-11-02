# Documentación de MUSA

Empieza por la ruta que necesitas: [instalación](INSTALLATION.md),
[motor y QGIS](ARCHITECTURE.md) o [API Python sin QGIS](PYTHON_API.md).
La referencia matemática vigente es [theory.md](theory.md).
El código experimental es 1.0.0; fuente publicada, paquete instalado,
release GitHub y publicación PyPI son estados distintos.

## Archivos principales

| Archivo | Rol |
| --- | --- |
| [INSTALLATION.md](INSTALLATION.md) | Instalación desde Git, ZIP QGIS, dependencias y estado de PyPI/terminal |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Responsabilidades del núcleo, flujo común e instantánea privada del plugin |
| [PYTHON_API.md](PYTHON_API.md) | Puntos, líneas, recetas, diagnóstico independiente y lectores de resultados |
| [OUTPUTS.md](OUTPUTS.md) | Archivos, columnas, unidades, estados y uniones de tablas |
| theory.md | Referencia tecnica del algoritmo global, local, zeta y salidas |
| references.md | Referencias cientificas publicas |
| DEVELOPMENT_STATUS.md | Alcance neutral del software y estado de desarrollo |
| QGIS.md | Instalación del plugin, panel en inglés, recetas y Processing |
| [SCALING_SUPPORT.md](SCALING_SUPPORT.md) | Criterios del diagnóstico independiente de escalamiento |
| [SPECTRA.md](SPECTRA.md) | Fuentes analysis/assessment y referencias de singularidad |
| [moving_windows.md](moving_windows.md) | Ventanas solapadas, orígenes y topología |
| [candidate_scoring.md](candidate_scoring.md) | Perfil experimental de contraste relativo y zeta |
| [node_products.md](node_products.md) | Postproceso de nodos; no es una regla geológica universal |
| [SCALING_VALIDATION_STATUS.md](SCALING_VALIDATION_STATUS.md) | Evidencia numérica y validación científica pendiente |
| [EXTENDED_BENCHMARKS.md](EXTENDED_BENCHMARKS.md) | Fuentes públicas, casos, resultados y límites de la suite ampliada |
| [AUTHOR_BENCHMARKS.md](AUTHOR_BENCHMARKS.md) | Primera suite de controles y mapas de autores |
| [EXTENDED_BENCHMARK_PLAN.md](EXTENDED_BENCHMARK_PLAN.md) | Registro del plan ejecutado, no manual de usuario |
| [revision_ventanas_moviles.md](revision_ventanas_moviles.md) | Diagnóstico histórico de septiembre; no contrato actual |

Los documentos históricos y planes conservados en Git describen decisiones y
evidencias; no sustituyen las guías actuales. Los borradores locales, originales
de autores, bitácoras de descarga y resultados voluminosos permanecen fuera del
paquete del plugin. La presencia de un archivo en Git no implica que el
constructor del ZIP lo incluya.

Los datos, resultados y entregas de proyectos privados se mantienen fuera
del repositorio. No son productos de MUSA ni material autorizado para ejemplos,
benchmarks o publicación del software. Esta documentación describe métodos,
interfaces, controles sintéticos y validación con fuentes públicas identificadas.
Las pruebas numéricas no convierten una inferencia geológica en validación externa.
