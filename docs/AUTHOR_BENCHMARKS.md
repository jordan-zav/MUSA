# Controles analíticos y mapas publicados

Prueba local del 2 de noviembre de 2026. Los datos y resultados se conservan fuera del código y del ZIP del plugin.

Se procesaron 20 casos: una línea uniforme, dos aproximaciones finitas de Cantor (pesos uniformes y binomiales), tres reconstrucciones independientes de la construcción de Roy, ocho imágenes originales del suplemento de Sahu y Roy y seis variantes de umbral de sus imágenes 6–8. Cada caso incluye el diagnóstico global y cuatro ventanas fijas; cada soporte solicita q = −2, −1, 0, 1, 2. No se ejecutaron simulaciones nulas en esta suite.

Los originales publicados son imágenes BMP, no coordenadas vectoriales. Los vectores derivados son centros de corridas horizontales/verticales de píxeles, con umbral declarado y unión geométrica explícita para eliminar multiplicidad coincidente. Se conservan originales, hashes, longitudes antes/después, conteo ráster y decisiones de aceptación. No se rellenan huecos ni se interpretan fracturas automáticamente.

Los resultados usan un plano UNLOCATED normalizado a anchura 10000. Las columnas del software que terminan en m representan aquí unidades del modelo; no son ubicaciones reales ni mediciones de afloramientos georreferenciados.

## Resultados y alcance

La línea recuperó D0 = 0,997335 frente a 1. El Cantor uniforme dio 0,641731 y el binomial 0,634066 frente al objetivo de capacidad log(2)/log(3) = 0,630930. El informe compara también Dq, tau, alpha y f(alpha) con los objetivos analíticos correspondientes a cada medida; los errores no se sustituyen por indicadores de aprobación.

Para las imágenes originales 6, 7 y 8 vectorizadas con umbral 128, D0 fue 1,592721; 1,594612; 1,593810 frente al límite teórico log(3)/log(2) = 1,584963. Las imágenes 1–5 no tienen intervalo suficiente según los criterios declarados. Las variantes de umbral muestran sensibilidad de rasterización y no deben confundirse con coordenadas originales. El objetivo teórico de Roy se compara solamente con D0, sin atribuir objetivos exactos a sus otros Dq.

Las escalas se fijan antes del ajuste considerando resolución, corte inferior de la construcción finita y límite superior de un cuarto de la anchura del dominio. Cada ventana aplica además su propio límite superior. La compatibilidad en ese intervalo no demuestra fractalidad ni garantiza precisión: en el Cantor binomial, alpha para q = −1 presenta error absoluto de aproximadamente 0,137. Se conservan los q rechazados y sus motivos. Esta prueba no constituye validación geológica ni calibración general del contraste estadístico.

## Fuentes

- Sahu, A. K. y Roy, A. (2020), [Clustering, Connectivity and Flow Responses of Deterministic Fractal-Fracture Networks](https://adgeo.copernicus.org/articles/54/149/2020/), Adv. Geosci. 54, 149–156. El artículo declara CC BY 4.0. Se conserva íntegro su [suplemento original](https://adgeo.copernicus.org/articles/54/149/2020/adgeo-54-149-2020-supplement.zip), con atribución y derivados identificados.
- Zhu y colaboradores, [dataset 10.4121/14464893](https://doi.org/10.4121/14464893): los metadatos públicos indican CC BY-NC 4.0. La descarga de coordenadas quedó pendiente por timeout/502/504; se archivaron solamente los metadatos y los intentos. No se afirma haber analizado sus 80 afloramientos naturales.

## Reproducción y entrega

Ejecutar desde la raíz del repositorio. Los originales se descargan en data/benchmarks (o en la carpeta indicada por MUSA_BENCHMARK_DATA); RESULTADOS es una carpeta nueva:

~~~text
python scripts/fetch_fractal_benchmarks.py --root data/benchmarks
python scripts/run_author_benchmarks.py --output RESULTADOS
python scripts/package_author_benchmarks.py RESULTADOS
scripts/run_qgis_python.cmd scripts/qgis_author_benchmarks.py RESULTADOS dist/qgis/ZIP_VALIDADO.zip
~~~

Para el último comando, definir MUSA_QGIS_ROOT con la instalación existente de QGIS. Si Zhu no está accesible, el primer comando conserva el suplemento verificado de Sahu/Roy y termina con error explícito; los siguientes comandos usan el suplemento disponible sin inventar datos de Zhu.

Entrega comprobada: sesión MUSA-author-benchmarks-20261102_135150, archivada por el mantenedor. Incluye GeoPackage combinado, archivos por caso, proyecto QGIS con rutas relativas, resultados globales/ventanas, cachés de espectros, comparación analítica, originales y atribución. Los archivos físicos por caso evitan la consulta de subconjuntos compartidos de GeoPackage que falló en el proveedor de esta instalación de QGIS; no se cambiaron las geometrías para resolverlo.

El proyecto se creó y reabrió en QGIS 3.44.12: 60 capas válidas, CRS de modelo aceptado y visor del plugin cargando una ejecución completada. Se utilizó estado temporal aislado sin modificar el perfil normal del usuario. Esto comprueba la carga y visualización nativa; no implica que se haya repetido la suite entera mediante Processing.

Las pruebas del generador verifican la construcción de Roy, el CRS sin georreferencia, la vectorización de un patrón controlado y las referencias analíticas. Los datos no se publicaron ni se añadieron al paquete instalable del plugin.
