# Salidas, estados y lectura de resultados

La fuente del inventario de cada ejecución es run_manifest.json, campo outputs. Los archivos dependen de las opciones habilitadas; no todas las ejecuciones producen todos los productos.

execute_analysis guarda una carpeta, sin ZIP automático. Para compartirla, conservar su estructura completa. El helper legado package_run_output solo agrupa archivos del primer nivel y no es un respaldo recursivo del workflow actual; no asumir que incluye subcarpetas, entradas originales o todos los datos necesarios para reproducirlo.

## Cómo empezar a leer una ejecución

1. Comprobar status en run_manifest.json. complete indica ejecución terminada; no significa que todos los q o ventanas tengan respaldo.
2. Consultar analysis_report.csv para el análisis descriptivo y scaling_support.json/CSV para el diagnóstico independiente, si fue solicitado.
3. Seleccionar una fuente, soporte y estimador en spectrum_summary.csv o en el visor QGIS. Revisar cuántos q son utilizables antes de interpretar un máximo o un ancho espectral.
4. Para mapas locales, comprobar cobertura, escala, calidad y definición del producto. Mantener separados intensidad estructural, confiabilidad y espectro.

## Inventario principal

| Producto | Cuándo aparece | Lectura |
| --- | --- | --- |
| recipe.json | Flujo execute_analysis | Parámetros reutilizables; no guarda los archivos de entrada |
| run_manifest.json | Flujo común | Versión, estado, procedencia disponible, outputs y hashes |
| analysis_report.csv | Ajuste global terminado | Resúmenes, q aceptados/rechazados y calidad descriptiva |
| analysis_scale_diagnostics.csv | Flujo común | Integrandos y diagnósticos de las escalas del ajuste global |
| spectrum_fit_summary.csv | Flujo común | Control cuadrático descriptivo del espectro global |
| spectrum_curves.sqlite | Productos espectrales | Índice por fuente, soporte y estimador; puntos y calidad |
| spectrum_summary.csv | Productos espectrales | Una fila por serie; referencias de singularidad, q utilizables e identidades |
| scaling_support.json / scaling_support.csv | Diagnóstico solicitado | Intervalo, exclusiones, orígenes, criterios, observables, causas y contraste nulo |
| monofractal_cells.csv / multifractal_cells.csv | local=True | Medidas e integrandos por celda hija |
| monofractal_mother_agg.csv / multifractal_mother_agg.csv | local=True | Resultados por celda madre, q y estimadores disponibles |
| musa_mother_cells.gpkg | gis=True y productos madre | Capas espaciales del flujo; las capas efectivas dependen de opciones |
| moving_windows.csv / moving_nodes.csv | moving=True | Soportes móviles y topología exacta |
| musa_moving_windows.gpkg | moving=True y gis=True | Ventanas, candidatos/controles y tablas espectrales disponibles |

Los nombres de figuras globales y locales se registran en outputs; algunas incorporan q en el nombre. Las opciones bootstrap y sensibilidad pueden añadir columnas o archivos. Los postprocesos experimentales tienen sus propios contratos en [nodos](node_products.md) y [candidatos](candidate_scoring.md).

## Cuatro estados que no deben confundirse

| Campo/contexto | Significado |
| --- | --- |
| status de ejecución | running, complete, failed o cancelled; estado del proceso |
| accepted del análisis descriptivo | Calidad según el filtro de esa ruta; no una prueba formal de fractalidad |
| reliable / reliable_w | Regla local de calidad/zeta de su estimador; no probabilidad de validez geológica |
| status del diagnóstico | compatible_finite_range, not_supported o insufficient_information, para el soporte y observable declarados |

El diagnóstico admite un Dq calculado con status=not_supported: ese número se conserva para auditoría, no se convierte en una estimación respaldada. Cuando no hay información suficiente, dimension puede ser nulo; nunca sustituirlo por cero. tau, alpha y f_alpha tienen sus propios estados en observables. El mismo q puede tener Dq compatible y alpha insuficiente.

## Diccionario de espectros y unidades

| Campo | Significado |
| --- | --- |
| q | Orden del momento; modifica el énfasis de masa, no el número de dimensiones espaciales |
| dq / dimension | Pendiente de entropía de Rényi en el intervalo; revisar estado y fuente |
| tau / tau_w | Exponente de masa de la estimación canónica/ponderada correspondiente |
| alpha / f_alpha | Estimación canónica de singularidad y dimensión espectral |
| alpha_w / f_alpha_w | Variante local ponderada por zeta, conservada por separado |
| alpha_q0 | Alpha en q=0 utilizable; no se reemplaza por un q vecino |
| observed_peak_alpha | Alpha del máximo observado de f; revisar empates y si está en un extremo |
| fit_peak_alpha | Vértice cuadrático descriptivo válido; puede estar ausente |
| delta_alpha | Rango de alpha sobre puntos utilizables; no extrapolación a q no evaluados |
| measure_sum_m | Longitud local registrada en la escala fina para líneas métricas; no dimensión multifractal |
| zeta_mean | Resumen de ponderación operacional; no conectividad ni favorabilidad |
| coverage | Fracción del soporte nominal observada, según el producto |

Dq, tau, alpha, f(alpha), q, R² y zeta son adimensionales. Coordenadas, longitudes, lado de ventana y escalas de una corrida GIS ordinaria son metros del CRS proyectado. Los ejemplos UNLOCATED de benchmark usan unidades de modelo o píxeles explícitamente declarados; no interpretar sus sufijos m como mediciones geográficas reales. En entradas de puntos normalizados, la escala es la de esa normalización.

## Fuentes y uniones

analysis y assessment son fuentes distintas; canonical y zeta son estimadores distintos. El soporte global no equivale al promedio de ventanas. Identificar una serie mediante source, support_id y estimator; para ventanas, añadir center_id y window_m según la tabla disponible. No unir solo por q ni solo por coordenadas.

La tabla window_spectrum_summary del GeoPackage móvil conserva resúmenes no espaciales cuando el flujo la exporta. El índice SQLite contiene los puntos necesarios para reconstruir las cuatro curvas. El visor carga la selección guardada; no recalcula el análisis al cambiar de ventana.

## Trazabilidad y fallos

Un flujo fallido puede dejar scaling_support.json válido y luego fallar el ajuste global. La ejecución completa sigue marcada failed y no debe abrirse como complete. Para obtener una evaluación independiente sin ese filtro global, usar assess_lineament_scaling o musa:scaling_support.

El manifiesto registra hashes de productos y, si el host aporta la información, de las geometrías transformadas. Una receta sin entradas no basta para reproducir una cartografía: conservar datos, CRS, selección, preprocesamiento, versión y licencias originales.

La [guía de espectros](SPECTRA.md) detalla empates, criterios del pico y consulta del índice. La [teoría](theory.md) explica fórmulas y diferencias de estimadores.
