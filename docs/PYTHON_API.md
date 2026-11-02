# API Python: ejecutar el motor sin QGIS

Requiere la instalación de [INSTALLATION.md](INSTALLATION.md). Estos ejemplos usan la API disponible; no presuponen un comando instalado musa ni una publicación en PyPI.

## Puntos 2D en memoria

~~~python
import numpy as np
from musa import MUSA

points = np.random.default_rng(42).random((5000, 2))
analyzer = MUSA(points, q_values=np.arange(-2, 3))
result = analyzer.run_analysis(min_scale=0.01, max_scale=0.4, num_scales=20)
print(result.q)
print(result.dq)
print(result.tau)
~~~

La entrada de puntos es una matriz N × 2, con al menos diez puntos. La normalización está activada por defecto; las escalas del ejemplo son del espacio normalizado, no metros de una cartografía. Usar normalize=False y escalas coherentes cuando sea necesario conservar las coordenadas. Esta ruta cuenta puntos por caja; no mide longitud de trazas ni admite una matriz espacial 3D.

MUSAResult contiene los q aceptados, sus Dq, tau, alpha, f_alpha, R² y diagnósticos disponibles, además de los q rechazados y su calidad. Si quedan menos de dos q que superen el filtro triple del análisis descriptivo, run_analysis genera ValueError. No devuelve una aprobación de fractalidad.

## Líneas y dominio observacional

El bloque siguiente requiere dos archivos propios; los nombres son ilustrativos. Para GeoPackage con varias capas, elegir la capa mediante el argumento layer de GeoPandas.

~~~python
import geopandas as gpd
import numpy as np
from pyproj import CRS
from shapely.ops import unary_union
from musa import MUSA

lines = gpd.read_file("lineamientos.gpkg", layer="lineamientos")
area = gpd.read_file("dominio.gpkg", layer="dominio")
if lines.crs is None or area.crs is None:
    raise ValueError("Ambas entradas necesitan su CRS de origen correcto")

# Ejemplo de CRS métrico; sustituirlo por el adecuado al área real.
analysis_crs = CRS.from_user_input("EPSG:32718")
if not analysis_crs.is_projected or analysis_crs.axis_info[0].unit_conversion_factor != 1:
    raise ValueError("Se requiere una proyección en metros")
lines = lines.to_crs(analysis_crs)
area = area.to_crs(analysis_crs)
boundary = unary_union(area.geometry)

analyzer = MUSA.from_line_geometries(
    lines.geometry, boundary, analysis_crs.to_wkt(), q_values=np.arange(-2, 3))
~~~

Este adaptador recorta al polígono, rechaza líneas no válidas y no reproyecta. La etiqueta de CRS no cambia coordenadas. El constructor MUSA también acepta un GeoDataFrame o ruta vectorial y boundary, con gis_reproject_to configurable; la preparación explícita anterior facilita auditar unidades y capas.

Antes de evaluar soporte de escalamiento, armonizar duplicados y registrar el efecto sobre la longitud. El diagnóstico independiente rechaza multiplicidad coincidente; no aplica una disolución silenciosa. El flujo descriptivo y las ventanas móviles tienen contratos de preparación distintos, explicados en [teoría](theory.md).

## Ejecutar el flujo común y exportar

Continuación del analizador de líneas anterior:

~~~python
from musa.workflow import RunConfig, execute_analysis

config = RunConfig(
    mother_cell_m=4000,
    divisors=(2, 4, 8, 16),
    q_min=-2, q_max=2, q_step=1,
    local=True, structural=True, network=False,
    plots=True, gis=True)

manifest = execute_analysis(analyzer, config, "outputs/analisis_nuevo")
print(manifest["status"])
print(manifest["outputs"])
~~~

Los tamaños son ejemplos de configuración, no escalas geológicas recomendadas. Elegirlos según resolución, dominio y objetivos. La carpeta final debe no existir; no crearla antes de execute_analysis. El flujo la reserva y conserva el manifiesto incluso si después falla o se cancela. El padre puede existir.

El flujo siempre ejecuta el espectro global. Los indicadores local, structural, network, moving, plots y gis habilitan sus etapas correspondientes. La validación de RunConfig exige al menos cuatro divisores enteros distintos, mayores o iguales que dos. No impone por sí sola una década de escalamiento; esa condición pertenece al diagnóstico independiente.

Para probar esta ruta sin archivos propios:

~~~text
python examples/headless_workflow.py --output outputs/headless_demo
~~~

El ejemplo sintético se ejecutó completo sin QGIS y con exportación GIS/figuras. No es un conjunto natural ni un ejecutor general de archivos desde terminal.

## Recetas

~~~python
import json
from pathlib import Path
from musa.workflow import RunConfig

recipe_text = json.dumps(config.recipe(), indent=2)
restored = RunConfig.from_recipe(json.loads(recipe_text))

# Para leer una receta exportada por una ejecución o por QGIS:
restored_from_file = RunConfig.from_recipe(
    json.loads(Path("outputs/analisis_nuevo/recipe.json").read_text(encoding="utf-8")))
~~~

El formato es musa-analysis versión 1. Guarda los parámetros, no las rutas de entrada. La receta se pasa a execute_analysis junto con un analizador preparado. Se puede reutilizar en QGIS mediante musa:run_recipe. La equivalencia exige las mismas geometrías, CRS, escalas y versión del núcleo.

## Diagnóstico independiente de escalamiento

Continuación del mismo analizador de líneas, incluso si run_analysis no pudo ajustarlo:

~~~python
from pathlib import Path
import numpy as np
from musa import ScalingOptions, assess_lineament_scaling, write_scaling_reports

options = ScalingOptions(resolution_m=10, null_replicates=0, seed=42)
report = assess_lineament_scaling(analyzer, np.geomspace(25, 1000, 16), options)
out = Path("outputs/diagnostico_nuevo")
out.mkdir(parents=True, exist_ok=False)
write_scaling_reports(out, [report])
for row in report["q_results"]:
    print(row["q"], row["status"], row["dimension"], row["reasons"])
~~~

Resolución e intervalo son ejemplos que deben justificarse con los datos. Se excluyen escalas fuera de los límites del soporte. Puede no quedar información suficiente; eso se informa sin buscar otro intervalo que ajuste mejor. write_scaling_reports escribe archivos con nombres fijos en la carpeta indicada; por eso el ejemplo crea una carpeta nueva explícitamente.

Para un soporte local, pasar boundary con el recorte geométrico de la ventana, nominal_area con el área cuadrada antes de recortar y un support_id único. Añadir center_id, center_x, center_y y window_m a los informes de ventanas antes de exportarlos permite identificarlos en el índice espectral. La opción RunConfig.scaling_support integra este diagnóstico en el flujo común; no elimina la exigencia del ajuste global de ese flujo.

## Ventanas y lectura de resultados

La API export_moving_windows permite centros regulares o explícitos y una lista de tamaños. Ver [moving_windows.md](moving_windows.md) para su contrato y para el conjunto opcional de orígenes.

~~~python
from pathlib import Path
from musa import list_spectra, read_spectrum, spectrum_figure

cache = Path("outputs/analisis_nuevo/spectrum_curves.sqlite")
index = list_spectra(cache)
if index:
    selected = read_spectrum(cache, index[0]["series_id"])
    figure = spectrum_figure(selected)
    figure.savefig("outputs/espectro_seleccionado.png", dpi=160)
    figure.clear()
~~~

Los lectores del índice son de solo lectura y no necesitan QGIS. Seleccionar explícitamente source, support_id y estimator al comparar resultados; el primer registro no tiene un significado científico preferente.

## Parámetros operativos

Para consultar los valores y campos completos de la versión instalada:

~~~python
from dataclasses import asdict
from musa.workflow import RunConfig
from musa import ScalingOptions

print(asdict(RunConfig()))
print(asdict(ScalingOptions(resolution_m=1)))
~~~

RunConfig y ScalingOptions tienen validadores distintos porque resuelven tareas distintas. resolution_m es obligatorio para el diagnóstico; seed controla las réplicas solicitadas, no corrige errores de entrada ni selecciona una proyección.
