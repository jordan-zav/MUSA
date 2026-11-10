# Instalación y formas de ejecución

Referencia de MUSA 1.1.0, la primera release del plugin de QGIS. Las releases de escritorio 1.0.0 y 1.0.1 siguen en el historial de GitHub.

## Elegir una ruta

| Objetivo | Instalar | Ejecutar |
| --- | --- | --- |
| Trabajar con mapas y ventanas desde QGIS | ZIP del plugin, construido desde el repositorio actual | Vector > MUSA > MUSA Workbench o herramientas Processing |
| Usar el motor en scripts o notebooks | Paquete Python desde el repositorio, en un entorno virtual | Importar MUSA y las funciones de musa.workflow |
| Reproducir los benchmarks | Fuente y dependencias opcionales benchmarks | Scripts de validación, con originales y resultados externos |

El nombre de distribución es musa-multifractal; la importación Python es musa. El identificador del plugin construido es musa_qgis. Son nombres de distribución distintos para un mismo núcleo numérico.

## Python desde GitHub

Python 3.10 o superior. Crear y activar un entorno virtual propio; no usar el Python de QGIS para esta ruta.

~~~text
python -m venv .venv
~~~

En Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
~~~

En Linux/macOS:

~~~sh
source .venv/bin/activate
~~~

Instalación directa del código actual publicado en main:

~~~text
python -m pip install "musa-multifractal[gis] @ git+https://github.com/jordan-zav/MUSA.git@main"
~~~

Requiere Git. Para una ejecución reproducible sustituir main por el hash del commit elegido. Para trabajar con los ejemplos y modificar la fuente:

~~~text
git clone https://github.com/jordan-zav/MUSA.git
cd MUSA
python -m pip install -e ".[gis]"
~~~

Los comandos siguientes presuponen ese directorio del repositorio y el entorno activado.

| Extra | Uso y dependencia |
| --- | --- |
| Sin extra | API de puntos y cálculos con NumPy, SciPy y Matplotlib |
| gis | Shapely, GeoPandas y PyProj para líneas, archivos vectoriales y exportación GIS |
| fast | Aceleración opcional Numba; el motor conserva la alternativa Python |
| benchmarks | Adaptadores GIS actuales, Pyogrio, Pillow, requests y PyMuPDF para las fuentes de validación |

Para benchmarks o desarrollo:

~~~text
python -m pip install -e ".[benchmarks]"
python -m pip install -r requirements-dev.txt
~~~

La segunda orden instala también pytest y Ruff. No descarga los conjuntos de datos de autores. Consultar [validación ampliada](EXTENDED_BENCHMARKS.md) para esas descargas, licencias y límites.

## Ejecutar sin QGIS

La [API Python](PYTHON_API.md) describe la entrada real de líneas, puntos y recetas. Existe un ejemplo sintético ejecutable desde la fuente:

~~~text
python examples/headless_workflow.py --output outputs/headless_demo
~~~

La carpeta de salida debe ser nueva. El ejemplo no abre ventanas ni necesita QGIS. Produce una receta, manifiesto, CSV, caché espectral, figuras y productos GIS. Su plano sintético no tiene ubicación real.

## QGIS

El código declara compatibilidad con QGIS 3.34–3.99; la versión comprobada en esta revisión es 3.44.12. Ese rango de metadatos no equivale a haber probado todas las versiones y sistemas.

1. Obtener el repositorio y construir el ZIP con el Python de desarrollo:

~~~text
python scripts/build_qgis_plugin.py
~~~

2. En QGIS: Complementos > Administrar e instalar complementos > Instalar a partir de ZIP. Elegir el archivo nuevo de dist/qgis.
3. Abrir Vector > MUSA > MUSA Workbench. El panel actual está en inglés.

El ZIP lleva una copia privada del núcleo, sin la interfaz Tk. NumPy, SciPy, Shapely y Matplotlib deben estar disponibles en el Python de QGIS; el plugin no ejecuta pip automáticamente. Para módulos ausentes, usar el gestor de dependencias de la distribución de QGIS y reiniciar QGIS. Instalar el paquete en un entorno virtual externo no instala módulos dentro de QGIS.

Ver [guía QGIS](QGIS.md) para selección de capas, CRS, tareas, cancelación, recetas y resultados.

## Estado de distribución

| Vía | Estado al 2 de noviembre de 2026 |
| --- | --- |
| Fuente GitHub / instalación pip desde Git | Disponible |
| Wheel Python desde pyproject.toml | Construido e instalado en un destino separado; ejemplo de puntos ejecutado sin QGIS |
| PyPI, nombre musa-multifractal | Consulta pública sin proyecto disponible en esta revisión; publicación pendiente |
| ZIP del plugin 1.1.0 | Publicado en la release v1.1.0 de GitHub; probado en QGIS 3.44.12 |
| Catálogo oficial de complementos QGIS para este nuevo paquete | No se afirma una publicación en el catálogo |
| Comando de análisis musa o python -m musa | No implementado |
| Comando musa-ui | Lanzador Tk legado; no es la interfaz QGIS ni un ejecutor de recetas |

No usar una instalación pip desde PyPI como instrucción disponible hasta publicar y comprobar el proyecto. La falta de un comando general de terminal no impide usar el motor sin QGIS mediante la API o scripts propios.

La construcción debe respetar el aislamiento de pip y el requisito setuptools >=77 declarado en pyproject.toml. Un setuptools antiguo con --no-build-isolation puede rechazar la licencia SPDX. La prueba de instalación del wheel utilizó dependencias científicas ya disponibles en Windows/Python 3.11; no constituye una matriz de instalaciones limpias en todos los sistemas.

## Entorno local del mantenedor

En el workspace Windows del mantenedor, anteponer DEVRESOURCES_RUN.cmd a las órdenes de desarrollo. Ese lanzador administra recursos y bloqueos de esa PC; no es una dependencia de usuarios de MUSA. Los scripts de comprobación nativa usan scripts/run_qgis_python.cmd y MUSA_QGIS_ROOT, exclusivamente para desarrollo.
