# Motor Python e integración con QGIS

MUSA mantiene un núcleo numérico común. QGIS aporta controles, captura de geometría y visualización; los cálculos compartidos residen en el paquete Python.

~~~text
QGIS: capas y CRS -> snapshot WKB -> tarea -> núcleo privado -> salidas -> capas/visor
Python: geometrías/datos         -> MUSA + RunConfig -> mismo flujo -> archivos
~~~

## Responsabilidades

| Componente | Código | Responsabilidad |
| --- | --- | --- |
| API básica | src/musa/core.py | Preparación de puntos/líneas, partición de medida, análisis global y celdas madre |
| Medida y partición | partition.py y mass_partition.py | Longitudes por caja y aceleración opcional |
| Flujo común | workflow.py | RunConfig, recetas, etapas, cancelación, manifiesto y exportaciones |
| Diagnóstico independiente | scaling.py | Escalamiento de Rényi en intervalo declarado y contraste espacial condicional |
| Ventanas móviles | moving.py | Soportes recortados, espectros locales, orígenes y topología planar |
| Espectros | spectrum.py y spectrum_products.py | Diagnóstico del pico, identidades, índice SQLite y consulta por soporte |
| GIS Python | geomatics.py y gis_styles.py | Entrada/salida con dependencias opcionales y estilos |
| Adaptador QGIS | qgis_plugin/inputs.py y native_gis.py | Captura, transformación de CRS y salida mediante QGIS |
| Interfaz QGIS | workbench.py y provider.py | Panel acoplable y algoritmos Processing |
| Legado | src/musa/interface.py y lanzadores antiguos | Tk; conserva compatibilidad, no es la ruta recomendada |

Los nombres de archivo sin directorio en la tabla pertenecen a src/musa salvo los componentes QGIS.

## Qué significa compartir el motor

El constructor del ZIP copia src/musa a musa_qgis/_core/musa. El plugin importa esa copia privada mediante runtime.py. No depende de que el usuario haya instalado otro paquete llamado musa en el Python de QGIS, y evita mezclar accidentalmente versiones con un paquete externo.

El código fuente es común; cada ZIP contiene una instantánea. Cambiar la fuente o instalar una versión nueva por pip no actualiza un plugin ya instalado. Hay que reconstruir e instalar su ZIP. El manifiesto de construcción registra hashes de archivos para comparar las copias.

## Geometría, CRS e hilos

En QGIS, el adaptador valida tipo de geometría y CRS proyectado en metros, transforma las coordenadas y copia WKB antes de iniciar la tarea. La tarea no recibe capas del proyecto ni objetos de la interfaz. También se incluyen capas temporales, ediciones sin guardar y selección explícita de líneas. Los atributos copiados son los admitidos para el contexto estructural; no es un respaldo completo de los datos originales.

En la API Python, MUSA.from_line_geometries recibe Shapely ya proyectado: no transforma coordenadas ni verifica que una etiqueta de CRS corresponda a sus valores. El llamador debe comprobar el CRS real y las unidades antes. El constructor MUSA con GeoDataFrame/archivo tiene su propia preparación GIS; para reproducibilidad se recomienda reproyectar explícitamente.

El flujo compartido reserva una carpeta nueva, escribe receta/manifiesto y ejecuta etapas. Mantiene un bloqueo para una ejecución por copia cargada del núcleo. La cancelación es cooperativa; un cálculo en curso puede tardar en volver al siguiente punto de cancelación. Un fallo conserva resultados parciales y marca el manifiesto; no se carga como una ejecución completa.

## Dos rutas de cálculo que deben distinguirse

1. execute_analysis ejecuta siempre el análisis descriptivo global y añade los productos solicitados. Su filtro triple de R² puede dejar menos de dos q aceptados y hacer fallar el flujo, aunque se haya generado previamente un diagnóstico parcial.
2. assess_lineament_scaling y Processing musa:scaling_support ejecutan el diagnóstico independiente. No requieren pasar el filtro global anterior. Es la ruta adecuada para examinar datos cuyo espectro descriptivo no pudo ajustarse.

En el visor, analysis y assessment identifican esas fuentes. No deben promediarse ni confundirse sus criterios, escalas, estabilización o cantidad de orígenes. Ver [teoría](theory.md) y [espectros](SPECTRA.md).

## Distribución y automatización

El paquete Python permite scripts y notebooks sin QGIS. El plugin necesita el runtime QGIS y sus dependencias. PyPI sería un canal de distribución del paquete Python; no instalaría la aplicación QGIS ni registraría automáticamente el complemento.

La automatización instalada actualmente se ofrece mediante Python y Processing. Hay un ejemplo ejecutable de la API en examples/headless_workflow.py. Todavía no existe un comando general musa para analizar archivos o ejecutar recetas. La [guía de instalación](INSTALLATION.md) mantiene la tabla de disponibilidad y el estado de PyPI.

## Reproducibilidad

Registrar versión/commit o hash del ZIP, parámetros, CRS real, entradas y su procedencia. recipe.json guarda parámetros; no contiene rutas de entrada. run_manifest.json registra los hashes de geometría copiados por el host cuando están disponibles y los hashes de salidas. Debe conservarse además el inventario original de datos y su licencia.

La equivalencia comprobada entre Python y Processing corresponde a las mismas entradas, escalas y parámetros; no implica equivalencia con una versión diferente del ZIP o con otro preprocesamiento. El [estado de validación](SCALING_VALIDATION_STATUS.md) describe la evidencia y los límites científicos.
