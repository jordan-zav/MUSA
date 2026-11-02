# Validación ampliada con datos publicados

Trabajo local del 2 de noviembre de 2026. El [plan](EXTENDED_BENCHMARK_PLAN.md) se implementa mediante scripts de descarga, adaptadores, análisis, comprobación nativa en QGIS y consolidación de evidencias. Los originales y resultados permanecen fuera del plugin y del repositorio.

## Qué se implementó

- Adaptadores para GeoJSON y Shapefile con CRS métrico y polígonos de observación originales, grafos MATLAB dispersos, filas de coordenadas de FracPaQ/HatchFrac y máscaras binarias.
- Descargas con procedencia y verificación de checksums. La selección FraXet usa rangos HTTP que el servidor admite, caché de bloques y espera ante HTTP429; se verifican los miembros seleccionados, sin afirmar haber descargado todo el archivo.
- Esqueletización explícita Zhang–Suen y segmentos entre centros de píxeles; registro de píxeles aislados, umbral y recorte. No se recupera la identidad de las fracturas originales desde una máscara.
- Unión geométrica exacta para retirar multiplicidad coincidente, con longitudes antes/después. Sin snapping, redondeo de coordenadas ni relleno de huecos. No se ejecuta código de terceros descargado.
- Evaluación global y por ventanas para q de −4 a 4, con Dq, tau, alpha, f(alpha), calidad e identidades. Los ajustes no respaldados y la información insuficiente permanecen en las salidas.
- Dos diseños de ventanas para los casos georreferenciados: cuadrantes del rectángulo exterior y una cuadrícula interior solapada. Se conservan ambos; la posición interior depende de la geometría y no de las pendientes obtenidas.
- Comparación analítica del núcleo geométrico real con una cascada diádica 2D de 65.536 segmentos; controles Cantor finitos; sensibilidad de resolución y contraste con conteo ráster.
- Controles de una estructura periódica: compatibilidad aparente en un intervalo y rechazo al extenderlo a través de su escala característica. El seguimiento de intervalo ampliado se identifica como exploratorio.
- Familia declarada de tres contrastes globales de traslación condicional, con 99 réplicas solicitadas por soporte y corrección Holm. Los casos no contrastables no reciben valores p inventados.
- Proyectos QGIS separados por coordenadas y fuente; inspección del visor y comparación numérica entre Python y Processing nativo.

## Cobertura de fuentes

| Fuente | Material utilizado | Límite de la comparación |
| --- | --- | --- |
| Åland, Ovaskainen y colaboradores | Vectores de fracturas/lineamientos y dominios, EPSG:3067 | Varias modalidades y subconjuntos del mismo territorio; resolución operacional declarada |
| Loviisa, Ovaskainen y Nordbäck | Ocho redes y polígonos originales, EPSG:3067 | El dominio puede impedir ventanas completas; no se rellena la cobertura ausente |
| Bristol, Kang | Coordenadas y conectividad MATLAB | Rectángulo de observación inferido; unidades originales sin verificación física |
| HatchFrac | Red 2D, backbone y tres etapas de crecimiento de los autores | Salidas originales existentes; no representan fractales de dimensión exacta conocida |
| Hornelen, figuras de Sahu y Roy | Tres representaciones/recortes con identificación explícita en el artículo | Derivados de figuras en píxeles; mapas relacionados, no afloramientos independientes |
| FracPaQ | Dos ejemplos vectoriales del repositorio de autores | No se atribuyen a Hornelen solo por el nombre map1/map7 |
| FraXet | 24 máscaras de prueba preseleccionadas de tres familias | 20 con trazas y cuatro vacías; no se ensamblan en un supuesto afloramiento continuo |
| GeoCrack | Metadatos de DataCite | Harvard Dataverse devolvió 403 y una verificación antibot; imágenes no descargadas ni analizadas |
| Zhu, dataset 10.4121/14464893 | Metadatos conservados de la tarea anterior | Coordenadas no disponibles en los endpoints probados; no se afirma su análisis |

La entrega contiene 67 casos procesables, incluidas variantes de resolución y controles. No equivale a 67 conjuntos independientes. Las cuatro máscaras vacías se conservan como no aplicables. El inventario detallado registra identificadores, licencias y estado efectivo de cada fuente; las licencias del artículo, código y dataset se distinguen.

## Qué permiten concluir las pruebas

El núcleo de partición de longitud y cálculo canónico recuperó Dq, tau, alpha y f(alpha) de la cascada exacta con error máximo de aproximadamente 2,09 × 10⁻¹⁴. Esta comprobación usa un origen alineado y escalas diádicas finitas: valida ese cálculo, no la precisión geológica ni la estabilidad frente a cuatro orígenes arbitrarios.

La malla periódica mostró por qué una pendiente estable no demuestra fractalidad. D0 fue aproximadamente 1,846 y compatible en el intervalo inicial; al ampliar el intervalo a través de su separación conocida aparecieron mejores modelos cuadrático y segmentado. Se conservaron ambos resultados sin modificar umbrales.

En un círculo, cada cuadrante del rectángulo exterior tiene cobertura pi/4 ≈ 0,785, menor que el mínimo 0,8. Los informes iniciales se conservan y las ventanas interiores permiten estudiar soportes mejor cubiertos. Los centros interiores están a 3/8 y 5/8 de cada eje, con el mismo lado de ventana. No son réplicas independientes.

En redes naturales y figuras, cada observable tiene su propio estado. Que D0 sea compatible no garantiza un espectro completo ni un máximo de singularidad respaldado. Las estimaciones rechazadas, cortes de resolución y sensibilidades deben acompañar cualquier interpretación.

## Reproducción

Ejecutar los comandos mediante DEVRESOURCES_RUN.cmd. Las descargas usan D:/DevResources/Shared/MUSA-benchmarks. Para repetir el análisis con los originales disponibles, elegir una carpeta nueva:

~~~text
python -m pip install -e ".[benchmarks]"
python scripts/extended_benchmark_inputs.py D:/DevResources/Sessions/NUEVA_SESION
python scripts/run_extended_benchmarks.py D:/DevResources/Sessions/NUEVA_SESION
python scripts/add_interior_benchmark_windows.py D:/DevResources/Sessions/NUEVA_SESION
scripts/run_qgis_python.cmd scripts/qgis_extended_benchmarks.py D:/DevResources/Sessions/NUEVA_SESION dist/qgis/ZIP_VALIDADO.zip
python scripts/report_extended_benchmarks.py D:/DevResources/Sessions/NUEVA_SESION
~~~

Definir MUSA_QGIS_ROOT con la instalación existente antes del paso QGIS. La preparación conserva supuestos e inventarios; el ejecutor verifica hashes de entrada y rechaza reanudar con parámetros diferentes. El informe final conserva CSV de soportes, resúmenes espectrales, comparación ráster/vector, manifiestos y evidencias QGIS. La ruta de la ejecución comprobada es D:/DevResources/Sessions/MUSA-extended-benchmarks-20261102_143812.

Ver fuentes primarias y alcance de cada método en README.md de la entrega. Los algoritmos completos de wavelets de Ouillon y el programa MATLAB de De Souza/Rostirolla no se incorporaron a MUSA; sus artículos orientan las comprobaciones de rango y muestreo. No se publicó una release.
