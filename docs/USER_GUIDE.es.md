# Guía de usuario de MUSA 1.3.1

MUSA mide la distribución de longitud de líneas en celdas cuadradas dentro de un dominio de observación 2D. Proporciona espectros descriptivos globales y locales, junto con un diagnóstico separado del escalamiento en un intervalo finito. Estas rutas tienen reglas de aceptación distintas. Sus resultados describen la medida cartografiada; las interpretaciones de permeabilidad, favorabilidad geológica, conectividad 3D o una clasificación universal de fractalidad requieren evidencia externa.

El recorrido ilustrado utiliza la interfaz vigente y una red sintética de fracturas en metros de modelo sin ubicación geográfica. [English](USER_GUIDE.md), [Fundamentos](KNOWLEDGE_BASE.es.md) y el [mapa del flujo](WORKFLOW.es.md) describen la misma ejecución. El selector de idioma en la cabecera del panel cambia en vivo todo el Entorno (pestañas, controles, visor de espectros, resúmenes y Fundamentos) entre español e inglés; las capturas históricas del recorrido muestran la disposición en inglés.

## 1. Instalar y elegir una ruta de cálculo

Consulta [INSTALLATION.md](INSTALLATION.md) para las dependencias de Python y el ZIP de QGIS. Python requiere una versión >=3.10; el uso habitual con líneas y SIG necesita el extra gis. El plugin utiliza NumPy, SciPy, Shapely y Matplotlib en el Python de QGIS. Instalarlos en otro Python deja intacto el entorno de QGIS. MUSA requiere instalar las dependencias por separado. Se comprobó QGIS 3.44.12; el intervalo 3.34–3.99 de los metadatos expresa el rango declarado, cuya comprobación depende de la versión y el sistema.

En QGIS, habilita el plugin y abre Vector > MUSA > MUSA Workbench. Para el diagnóstico independiente, abre Processing Toolbox > MUSA > Lineament analysis > Assess Renyi scaling support, identificador musa:scaling_support.

| Ruta | Uso | Comportamiento importante |
| --- | --- | --- |
| MUSA.run_analysis | Espectro descriptivo global | Requiere al menos dos valores q que superen el triple filtro R² |
| execute_analysis / Workbench | Análisis descriptivo y productos seleccionados | Siempre ejecuta la etapa global; un fallo global o posterior puede dejar archivos parciales del diagnóstico |
| assess_lineament_scaling / musa:scaling_support | Diagnóstico independiente del intervalo finito y prueba espacial opcional | Conserva todos los q solicitados y su estado; se ejecuta independientemente del filtro descriptivo global |

Para datos cuyo espectro descriptivo falla, utiliza la ruta independiente. Modificar los umbrales de calidad tras inspeccionar un resultado requiere justificar y registrar la decisión.

## 2. Preparar las entradas

| Entrada | Requisito |
| --- | --- |
| Capa de líneas | Líneas 2D de longitud positiva, geometría válida y CRS de origen correcto |
| Polígono de observación | Polygon/MultiPolygon válido de área positiva, que represente el área realmente examinada; importan los huecos y el recorte |
| CRS de análisis | Coordenadas proyectadas en metros, adecuadas al área real de estudio |
| Resolución | Resolución positiva declarada de observación o cartografía, en las mismas unidades que las cajas |
| Escalas | Lados de caja explícitos, positivos y distintos, elegidos antes del ajuste; el diagnóstico admite hasta 64 |
| Valores q | Valores finitos distintos en [−100,100]; hasta 401; incluir 0 y 2 para el contraste de recolocación |

Conserva el dominio de observación cartografiado; cualquier modificación para mejorar el resultado requiere justificación. Asignar una etiqueta de CRS conserva las coordenadas originales. En Python, MUSA.from_line_geometries recibe geometrías Shapely ya proyectadas; el llamante responde por el CRS y las unidades. QGIS transforma las capas al CRS de análisis elegido antes de iniciar la tarea.

Armoniza las trazas duplicadas o coincidentes y registra el efecto sobre la longitud. El diagnóstico independiente rechaza la multiplicidad coincidente y exige resolverla explícitamente. La preparación descriptiva y las ventanas móviles tienen contratos distintos, descritos en [la teoría](theory.md). Si una unión geométrica crea partes divididas en nodos, el modelo de recolocación conserva esas partes como unidades, con las identidades de fracturas interpretadas originales fuera de ese cálculo.

En Workbench, **Use selected lines only** utiliza la selección actual de líneas; el límite utiliza todos los polígonos. Se capturan las capas temporales y los cambios sin guardar. Registra la selección en la procedencia. Para referencias públicas de imágenes o modelos, conserva las unidades declaradas de píxel o modelo; el sufijo m por sí solo expresa unidades. El CRS métrico personalizado del tutorial se denomina explícitamente UNLOCATED.

## 3. Pestañas Analysis y Quality

Selecciona **Lineaments**, **Boundary** y **Analysis CRS**. **Mother cell** es el lado de la celda madre; **Internal divisors** da tamaños hijos como lado madre / divisor. Se requieren al menos cuatro divisores enteros distintos >=2. Comprueba la escala más fina frente a la resolución cartográfica; cuatro escalas descriptivas quedan por debajo del mínimo de ocho del diagnóstico independiente por defecto.

Elige una carpeta padre existente con **Browse**. Workbench crea una subcarpeta nueva por ejecución. **Load spatial results into QGIS** carga los productos espaciales al terminar. **Save recipe** y **Load recipe** conservan los parámetros; los datos de entrada se guardan por separado.

Los siguientes son valores por defecto de RunConfig, cuya aplicación geológica requiere justificación:

| Campos | Valores por defecto | Significado |
| --- | --- | --- |
| mother_cell_m; divisors | 4000; (2,3,4,5,6,8,10,12,16,24,32) | Doce escalas de celda madre e hijas, relativas al tamaño madre |
| q_min; q_max; q_step | −4; 4; 1 | Órdenes de momento, no dimensiones espaciales |
| threshold_m | 0.01 | Umbral descriptivo de longitud por caja; modifica la medida retenida |
| min_r2 | 0.9 | Filtro descriptivo estricto de R² para Dq, alpha y f_alpha |
| local; structural; network | True; True; False | Etapas locales, estructurales y de red solicitadas |
| plots; gis | True; True | Figuras y exportaciones SIG |
| bootstrap_iterations; local_bootstrap_iterations | 0; 0 | Desactivado por defecto; intervalo admitido 0–10000 |
| bootstrap_ci; seed | 0.95; 42 | Nivel de confianza bootstrap y semilla reproducible |
| negative_q_floor_fraction | 0 | Desactivado; los valores positivos modifican la medida de q negativos |
| reliable_min_zeta | 0.15 | Umbral operacional de calidad local |
| zeta_exponents; zeta_scale_floor | (1,1,1,1); 0.25 | Factores de ocupación, masa, escala y equilibrio de entropía |
| zeta_sensitivity | False | Sensibilidad opcional a la ponderación |
| moving | False | Etapa de ventanas móviles |
| window_sizes_m; window_step_m | (2000,4000,8000); 1000 | Lados de ventana y separación de centros |
| moving_divisors; origin_ensemble | (2,4,8,16); False | Escalas internas; un origen salvo al activar los 16 orígenes |
| proximity_radii_m | () | Desactivado; radios opcionales de búsqueda exploratoria |
| scaling_support | True | Diagnóstico de escalamiento incluido por defecto |
| scaling_resolution_m; scaling_scales_m | 0; () | Introducir una resolución de observación positiva de la fuente antes de ejecutar; escalas vacías utilizan las escalas relativas del análisis |
| scaling_null_replicates; scaling_window_limit | 0; 25 | Prueba nula desactivada; límite de ventanas diagnosticadas, admite 1–1000 |
| renyi_order_policy | legacy_block | Política de orden compartida del diagnóstico |
| scaling_null_tail | upper | Nombre compartido de ScalingOptions.null_tail |
| scaling_coarse_trim_min_effective_q2 | 0 | Nombre compartido del recorte del extremo grueso |

El panel y RunConfig activan el diagnóstico para análisis nuevos. Una configuración nueva queda incompleta hasta introducir la resolución de observación positiva en Quality; el cero solicita ese dato. El análisis de Processing también exige Observation resolution. Utiliza la resolución de medición o cartografía de la fuente. Las unidades del CRS y un valor universal de un metro cumplen funciones distintas. Las recetas existentes conservan sus parámetros explícitos.

Monte Carlo tiene una opción separada, desmarcada en Quality. Cuando está desactivada, la receta guarda cero réplicas y el diagnóstico de escalamiento sigue ejecutándose. La ayuda emergente da un tiempo de referencia para 1201 trazas, doce escalas y cuatro orígenes: aproximadamente cinco minutos para 199 réplicas y 25 minutos para 999, basado en tres ensayos de recolocación y partición. El tiempo real depende de la geometría, el equipo y los requisitos del diagnóstico; son estimaciones.

Bootstrap y zeta describen aspectos numéricos condicionales; la incertidumbre cartográfica requiere evaluación propia. Zeta resume respaldo numérico operacional; su valor no representa una probabilidad de permeabilidad ni de validez geológica. Conserva separados los espectros canónicos y ponderados por zeta. La regularización de q negativos cambia la medida y exige compararla con el cálculo sin tratamiento; consulta [NEGATIVE_Q.md](NEGATIVE_Q.md).

## 4. Todas las opciones del diagnóstico independiente

ScalingOptions es la configuración completa de Python para el diagnóstico independiente. Processing y Workbench exponen una parte de sus umbrales de ajuste; los restantes se configuran mediante la API Python. Los umbrales por defecto son criterios operacionales cuya calibración geológica depende del contexto.

| Campo de ScalingOptions | Valor por defecto | Validación y efecto |
| --- | --- | --- |
| resolution_m | Obligatorio | Resolución positiva finita en metros; se excluyen cajas menores |
| min_scales | 8 | Entero 8–64; mínimo de escalas retenidas |
| min_decades | 1.0 | Amplitud mínima positiva de log10(máximo/mínimo) |
| min_effective_boxes | 2.0 | Al menos 2; mínimo de 1/sum(mu²) entre escalas y orígenes para el q evaluado |
| max_box_fraction | 0.25 | En (0,1]; se excluyen cajas mayores que esta fracción del lado corto del dominio |
| min_coverage | 0.8 | En (0,1]; área observada / área nominal suministrada |
| min_r2 | 0.98 | En [0,1); R² mínimo del ajuste lineal; distinto del min_r2 descriptivo |
| slope_tolerance | 0.10 | Positivo; variación de pendiente por escalas y orígenes, y tolerancias de intervalo finito y orden |
| curvature_effect | 0.03 | Umbral positivo de mejora del RMSE predictivo dividido por la amplitud logarítmica |
| cv_ratio | 0.75 | En (0,1); razón de RMSE predictivo alternativo/lineal; la mejora y la razón deben cumplir ambas condiciones para señalar una alternativa |
| null_replicates | 0 | Desactivado, o entero 19–9999; recolocaciones solicitadas |
| seed | 42 | Entero no negativo; controla los números aleatorios de recolocación |
| max_placement_attempts | 1000 | Entero positivo; máximo de intentos por traza |
| renyi_order_policy | legacy_block | legacy_block o inform_q0_q2; esta última conserva advertencias de orden q0/q2 sin ese veto y mantiene los demás requisitos de ajuste y soporte |
| null_tail | upper | upper o two_sided para el contraste Monte Carlo D0−D2 |
| coarse_trim_min_effective_q2 | 0.0 | Desactivado, o >=1; recorte grueso del mapa observado mediante el mínimo de cajas efectivas q=2 entre cuatro orígenes |

Antes del ajuste, la herramienta excluye cajas sin resolución o demasiado grandes. Al activar el recorte, elimina escalas del extremo grueso del soporte **observado** antes de cualquier recolocación, hasta cumplir el umbral q=2. El intervalo retenido queda fijo para todas las réplicas. La selección se basa en soporte efectivo. Las escalas retiradas y los conteos efectivos permanecen en scale_trimming. Una amplitud menor de una década tras el recorte impide la prueba nula y produce coarse_scale_trimming_below_one_decade.

Para la política del artículo, utiliza renyi_order_policy=inform_q0_q2, null_tail=two_sided y coarse_trim_min_effective_q2=4. Difieren de los valores por defecto conservados por compatibilidad. El tutorial declara también resolución, escalas, semilla y réplicas.

El diagnóstico promedia las curvas sobre cuatro orígenes desplazados fijos, ajusta frente a ln(1/tamaño de caja), compara predicciones lineales, cuadráticas y segmentadas, y conserva la sensibilidad a escalas y orígenes. Los quiebres segmentados se seleccionan de nuevo dentro de cada conjunto de entrenamiento. La medida del diagnóstico conserva la longitud sin ponderación zeta ni piso para q negativos.

## 5. Prueba condicional de recolocación de trazas

El estadístico es T = D0−D2. Ambos órdenes deben tener respaldo compatible en el intervalo finito. El modelo traslada las formas de traza recortadas suministradas de forma independiente y uniforme entre posiciones factibles dentro del polígono. Conserva cantidad, forma, longitud, orientación y masa total, mientras cambia posiciones, cruces y dependencia espacial. Las orientaciones quedan fijas; las fracturas fuera de la observación y el efecto del borde sobre su registro requieren modelos adicionales.

El p de cola superior es (1 + count(T_sim >= T_obs))/(B+1). El bilateral es min(1, 2 min(p_upper,p_lower)), contando los empates contra el rechazo en ambas colas. El mínimo p bruto es 1/(B+1) o 2/(B+1), respectivamente. Con B=999, el mínimo bilateral es 0,002. Utilizar solo la cola superior puede omitir desviaciones por debajo del modelo nulo.

write_scaling_reports aplica Holm a todos los soportes solicitados, incluidos los que carecen de prueba mediante p=1 conservador. Hay un contraste por soporte; los p repetidos junto a filas q del CSV corresponden a ese mismo contraste. Para m soportes, el primer rechazo posible de Holm a 0,05 exige 2m/(B+1) <=0,05 en una prueba bilateral. La salida registra la resolución Monte Carlo insuficiente.

Se conservan también los intentos fallidos de simulación. Un fallo de colocación, soporte simulado insuficiente, modelo nulo degenerado o q0/q2 observado sin respaldo produce ausencia de p. null_replicates=0 desactiva la prueba. La ausencia de p conserva la abstención y deja sin evaluar la homogeneidad. El rechazo concierne a este modelo condicional de posiciones; una afirmación de multifractalidad exige más evidencia.

## 6. Ventanas móviles y relaciones planas

En **Moving windows**, activa el análisis y declara lados, separación de centros y divisores internos. Reducir la separación aumenta el solapamiento; la resolución sigue procediendo de la fuente. El conjunto opcional utiliza 16 orígenes; el valor por defecto es uno. Las ventanas son dependientes y requieren particiones de entrenamiento y prueba que respeten esa dependencia.

Los nodos I/Y/X/complex describen extremos y grados planos. El cálculo conserva la geometría suministrada, sin ajuste automático de extremos ni inferencia de conexión hidráulica 3D. Las relaciones opcionales por radio mantienen las trazas y sus componentes; la proximidad sirve como medida exploratoria, sin convertirla en una conexión geológica. Consulta [moving_windows.md](moving_windows.md), [node_products.md](node_products.md) y [candidate_scoring.md](candidate_scoring.md) para sus contratos separados.

## 7. Ejecutar, cancelar y reconocer la abstención

**Run MUSA** inicia la tarea. **Cancel** solicita cancelación cooperativa; algunas etapas responden entre operaciones. Las ejecuciones fallidas o canceladas pueden conservar archivos parciales y deben identificarse como tales. Analysis complete o status=complete en run_manifest.json describe la finalización del cálculo; el respaldo científico se conserva en los diagnósticos.

| Estado del diagnóstico | Interpretación esperada |
| --- | --- |
| compatible_finite_range | Criterios operacionales satisfechos en el intervalo declarado |
| not_supported | Observaciones suficientes, con criterios de ajuste, estabilidad o forma incumplidos |
| insufficient_information | Cobertura, resolución, amplitud, escalas o soporte efectivo insuficientes |

Por ejemplo, un 66,7% de área observada incumple el mínimo de cobertura del 80%. Esto puede dejar dimensiones ausentes mientras otras ventanas siguen siendo utilizables. Conserva esa ausencia y su motivo; cualquier cambio del umbral requiere justificación. Un CRS, configuración o geometría inválidos puede producir un error de entrada, que constituye un caso distinto del soporte científicamente insuficiente.

## 8. Leer y exportar resultados

En **Results > Spectra**, elige dominio o cálculo, centro, tamaño y estimador. analysis y assessment identifican fuentes distintas; canonical y zeta identifican estimadores distintos. La selección inicial del centro favorece los puntos disponibles utilizables, con los demás centros siempre accesibles. La preferencia inicial es operativa.

**Chart** selecciona Dq, tau(q), alpha(q), f(alpha) o cuatro paneles. Cada curva utiliza el estado de su propio observable. Los valores calculados sin respaldo aparecen grises; un guion denota ausencia. Revisa **Reason** y todos los q mediante desplazamiento. La evaluación de Dq y la de la forma conjunta del espectro conservan sus criterios propios.

Alpha en q=0, el máximo observado de f(alpha) y el vértice cuadrático ajustado son referencias diferentes. Un pico ajustado necesita al menos tres puntos adecuados y comprobaciones adicionales; exactamente tres puntos permiten interpolación descriptiva. Con dos q utilizables, el pico queda por caracterizar. Unavailable es un resultado esperado cuando faltan requisitos.

Haz clic en un espectro para ampliarlo con controles de zoom, desplazamiento, reinicio y guardado. Cerrarlo devuelve al panel con el mismo análisis. **Export selected curves** guarda PNG o SVG; SVG conserva texto y líneas vectoriales. Comprueba fuente, soporte y estimador antes de exportar.

**Results > Figures** muestra las figuras guardadas. Haz clic en una vista previa para ampliarla; utiliza Zoom +, Zoom −, Fit, Actual pixels y arrastre. La ampliación de un ráster conserva su resolución original. Results tiene desplazamiento vertical exterior, y la tabla de valores y **Run details** tienen el suyo propio. El desplazamiento sobre gráficos y selectores conserva deliberadamente el centro elegido.

**Run details** recupera estado, versión, fechas UTC, procedencia, configuración y archivos del manifiesto. El progreso en vivo aparece cuando está disponible en la ejecución activa; los registros históricos se muestran si existen. **Open completed run** abre la carpeta que contiene run_manifest.json y recupera la ejecución sin recalcular ni cargar otra copia de las capas espaciales. **Open output folder** abre la ubicación de los resultados.

## 9. Archivos, campos y uso compartido

Consulta [OUTPUTS.md](OUTPUTS.md) para el diccionario completo de salidas. Según los productos activados, una ejecución descriptiva puede contener analysis_report.csv, tablas locales o móviles, GeoPackages, figuras, recipe.json, run_manifest.json, spectrum_summary.csv y spectrum_curves.sqlite. El diagnóstico independiente escribe scaling_support.json/CSV y productos espectrales; Processing añade su manifiesto. El tutorial Python independiente escribe expresamente su protocolo, receta, entradas y resumen.

El JSON del diagnóstico utiliza supports; cada soporte contiene q_results, observables, motivos, escalas solicitadas, utilizadas y excluidas, márgenes y null. Los campos CSV importantes incluyen support_id, q, status, dimension, tau, alpha, f_alpha, sus estados separados, null_status, null_p y null_p_holm. Une mediante source/support_id/estimator, además de center_id/window_m cuando corresponda; q o las coordenadas por sí solos resultan insuficientes.

Dq, tau, alpha, f(alpha), q, R² y zeta son adimensionales. Las coordenadas SIG habituales, longitudes, lados de ventana y escalas están en metros proyectados. Conserva declaraciones explícitas de unidades de píxel o modelo para referencias sin ubicación geográfica.

Guarda el proyecto QGIS y las capas de entrada. La receta conserva parámetros; los datos se guardan aparte. Conserva el árbol completo de salidas y la procedencia y licencias de las entradas. El flujo requiere preparar la compresión de resultados por separado; el ZIP instalable del plugin contiene el software. Las capas pueden contener varias filas por q o ventana y simbología por defecto q=2: comprueba filtros y tamaño de ventana antes de compararlas.

## 10. Resolución de problemas y lista de interpretación

- MUSA ausente: habilita el plugin y vuelve a abrir Vector > MUSA > MUSA Workbench.
- Ejecución bloqueada: comprueba líneas, polígono, CRS métrico, parámetros y carpeta padre existente.
- Error de CRS: corrige el CRS de origen real antes de reproyectar; asignar una etiqueta EPSG conserva las coordenadas.
- Menos de dos q descriptivos aceptados: examina escalas, resolución y geometría; utiliza el diagnóstico independiente y justifica cualquier modificación de filtros.
- Ventana vacía: comprueba cobertura, presencia de líneas y resolución en Reason.
- Pico ajustado ausente: examina la cantidad de q utilizables y las condiciones del ajuste; conserva la ausencia del máximo.
- Detalles o tabla largos, o panel pequeño: utiliza el desplazamiento interior y exterior correspondiente.
- Figura pequeña: amplíala; exporta las curvas seleccionables a SVG.
- p de recolocación ausente: lee null.status y el intervalo retenido; conserva la abstención registrada.

Antes de interpretar, confirma unidades y dominio, registra resolución y escalas, inspecciona los q utilizables, conserva rechazos y ausencias, distingue productos canónicos, zeta y de diagnóstico, y conserva entradas, recetas y resultados. Las pruebas de interfaz y numéricas acompañan una validación científica externa que debe realizarse por separado. Consulta [la teoría](theory.md), [el alcance de validación](SCALING_VALIDATION_STATUS.md) y [las referencias](references.md).

## 11. Recorrido sintético ilustrado

Estas capturas se regeneraron con QGIS 3.44.12 el 22 de noviembre de 2026. El ejemplo contiene 627 fracturas recortadas en un polígono observado de siete lados, dentro de una extensión de 10000 × 10000 m de modelo. Sus tres familias de orientación tienen medias de 20°, 80° y 140°, cada una con desviación angular de 9°. Las unidades son explícitamente metros de modelo UNLOCATED. Es una red sintética pedagógica generada en el repositorio, con procedencia sintética y sin ubicación de campo ni licencia de datos externos que atribuir.

Regenera las entradas con python scripts/tutorial_network.py --output outputs/fracture_example y carga lineaments y boundary de inputs.gpkg. El generador utiliza NumPy default_rng(20261122), 900 centros propuestos mediante una cascada espacial de cuatro niveles con probabilidades de cuadrante (0,1;0,2;0,25;0,45) y longitudes Pareto (parámetro de forma 1,3) limitadas a 150–900 m. Las trazas se recortan al polígono y se excluyen las partes menores de 5 m. Se conservan 627 trazas. El generador escribe provenance.json. Carga [la receta del recorrido](../examples/workbench_synthetic_recipe.json) después de seleccionar las capas. El mismo generador suministra los datos a scripts/capture_user_guide_qgis.py, que ejecuta el flujo y captura widgets Qt reales.

![Red sintética de fracturas y dominio observado](images/user-guide/00-map.png)

Analysis utiliza lado madre de 2000 m, divisores 2,4,8,16, q=0…4 con paso 0,5, figuras y SIG activados. Los productos por celda madre, estructurales y de red están desactivados en esta demostración. Output indica la carpeta padre existente de una ejecución nueva.

![Formulario vigente de Analysis](images/user-guide/01-analysis.png)

Quality utiliza R² descriptivo=0,9, umbral de longitud de 0 m, bootstrap desactivado y zeta por defecto. El diagnóstico independiente declara resolución de 1 m de modelo y 16 escalas geométricas de 125 a 2500 m; el intervalo completo se ajusta en el editor. La comparación clásica está activada. La política de orden advierte sobre el orden D0–D2 y el recorte grueso está desactivado.

![Calidad e intervalo declarado completo](images/user-guide/02-quality.png)

La prueba opcional de recolocación utiliza 99 réplicas, semilla 42 y cola bilateral. El análisis completo con ventanas termina en aproximadamente cinco minutos en el equipo del recorrido. El p global=0,02 y el p de Holm=0,46 en la familia de 23 soportes; el mínimo p bruto=0,02. Esta demostración carece de resolución para el primer rechazo de Holm a 0,05: se requieren al menos 919 réplicas bilaterales, pues 2 × 23 / (B + 1) ≤ 0,05. Ese mínimo permite alcanzar el umbral; el rechazo depende también de los resultados. Results muestra el límite de resolución junto al p.

![Controles de diagnóstico, comparación y Monte Carlo](images/user-guide/02b-scaling-options.png)

Moving windows utiliza lado de 6000 m, separación de 2000 m, divisores 2,4,8,16, un origen y radios de proximidad vacíos. Pulsa Run MUSA y comprueba Analysis complete. El ajuste descriptivo acepta nueve q. Entre los diagnósticos global y de ventanas, 61 pares soporte/q son compatibles, 14 son no respaldados y 132 tienen información insuficiente. Ocho de las 22 ventanas cumplen el umbral de cobertura del 80%; cada ventana conserva las trazas observadas dentro de ella y los motivos diagnósticos.

![Configuración de ventanas móviles](images/user-guide/03-moving-windows.png)

El bloque clásico separado muestra D_BC=1,59833, R²=0,994613 y D0 global de MUSA=1,56093, compatible en 16 escalas de 125 a 2500 m. El conteo clásico utiliza un origen; el diagnóstico promedia cuatro. Los JSON/CSV separados conservan sus diseños de medida.

![Comparación clásica, D0 evaluado y resolución de la prueba](images/user-guide/14-comparison.png)

Los Dq globales son compatibles. El espectro conjunto se retiene porque alpha(0,5) = 1,571 < alpha(1) = 1,577 entre los órdenes con estimaciones conjuntas respaldadas. La tabla también muestra alpha(0) = 1,499 < alpha(0,5) = 1,571; alpha en q=0 tiene diagnóstico no respaldado y queda fuera de ese criterio conjunto. El mensaje inglés identifica el par y sus valores. La ventana 18 siguiente tiene una curva conjunta respaldada.

![Diagnóstico de la forma conjunta del espectro global](images/user-guide/14b-global-spectrum.png)

Selecciona Moving windows — scaling assessment, Center 18, lado de 6000 m, Standard estimator. La cobertura es 82,95%. Los nueve Dq son compatibles; cuatro órdenes (q=0,5;1;1,5;2) tienen además estimaciones espectrales conjuntamente respaldadas. El intervalo retenido de la ventana se registra por separado del global; excluye cajas demasiado grandes para el soporte recortado. Otras ventanas muestran curvatura, sensibilidad al origen o soporte efectivo insuficiente.

![Dq de la ventana en el centro 18](images/user-guide/04-window-dq.png)

![Valores por q, estados y motivos con ajuste de línea](images/user-guide/07-per-q-values.png)

La curva conjunta f(alpha) del centro 18 es visible. Su forma supera los mismos controles de visualización aplicados a cada soporte; el núcleo compartido calcula los valores y las reglas de aceptación. El máximo observado y el ajustado tienen rótulos separados; el máximo ajustado permanece ausente cuando incumple sus controles. Esta muestra finita ilustra la lectura de una curva respaldada junto a abstenciones en otros lugares.

![Espectro respaldado de la ventana](images/user-guide/05-window-spectrum.png)

El centro 0 tiene 39,19% de cobertura observada, por debajo del mínimo 80%. Sus estimaciones permanecen ausentes con el motivo de cobertura baja. La ventana 11 tiene cobertura útil (97,61%), D0 compatible, D1 no respaldado por curvatura predictiva y soporte efectivo insuficiente en q=4. El selector de centro conserva acceso a todos estos resultados.

![Cobertura insuficiente en el centro 0](images/user-guide/08-low-coverage.png)

![Ventana con cobertura útil y rechazo por curvatura](images/user-guide/08b-curved-window.png)

Haz clic en un espectro para ampliarlo con navegación; exporta el gráfico seleccionado a PNG o SVG. La vista ampliada conserva la misma curva respaldada seleccionada.

![Espectro respaldado de ventana ampliado](images/user-guide/06-enlarged-spectrum.png)

Figures contiene las figuras descriptivas guardadas. Desplaza la página para ver la vista previa completa y haz clic para ampliarla. Dq descriptivo utiliza su propio intervalo de celda madre e hijas y su origen; sus valores difieren del diagnóstico de cuatro orígenes anterior. Los rótulos identifican el cálculo descriptivo.

![Figuras descriptivas guardadas](images/user-guide/09-figures.png)

![Figura descriptiva de Dq ampliada](images/user-guide/10-enlarged-figure.png)

Results tiene desplazamiento vertical exterior; su tabla y los detalles tienen sus propias barras. Los paneles estrechos permiten además desplazamiento horizontal de tabla para acceder a todas las columnas.

![Results en un panel pequeño](images/user-guide/12-results-scroll.png)

Run details recupera estado, versión, fechas, procedencia, parámetros y archivos. Open completed run carga la carpeta que contiene run_manifest.json sin recalcular. Conserva las entradas y el árbol completo de resultados junto con la receta y el proyecto.

![Detalles recuperados de la ejecución guardada](images/user-guide/11-run-details.png)

Learn / Fundamentos lee los capítulos canónicos en ambos idiomas. El recorrido empieza con el objeto geológico y compara densidad, distancia y rosa sobre la misma red de 627 trazas. Continúa con autosimilitud, multifractalidad, conteo de cajas y longitud por celda. Sus 13 figuras tienen etiquetas del idioma elegido y pies numerados; el visor conserva sus proporciones y adapta el tamaño al ancho disponible. Sus ejemplos incluyen longitud exacta frente a masa de píxeles y 100 segmentos aleatorios: 24 escalas, R² clásico=0,992364, D0 de MUSA no respaldado por curvatura predictiva y segmentación. Un ejemplo breve del Cantor finito declara expresamente que el clásico obtiene el valor correcto y MUSA se abstiene por contar con cuatro escalas. El único selector de idioma en la cabecera superior cambia simultáneamente el capítulo, el bloque comparativo, todas las pestañas y controles del Entorno y los paneles de Resultados entre español e inglés.

![Learn en inglés](images/user-guide/15-learn-en.png)

![Fundamentos en español](images/user-guide/15-learn-es.png)

Processing proporciona musa:analyze, musa:scaling_support y musa:run_recipe. El recorrido automatizado ejecuta sus diálogos reales y comprueba manifiestos completos. Su ayuda enlaza la misma fuente de aprendizaje. El [mapa del flujo](WORKFLOW.es.md) conecta controles, funciones del núcleo y archivos; [cinco cuadernos ejecutados](../notebooks/README.md) demuestran la API sin QGIS.

Las capturas del recorrido se hicieron con la versión 1.3.0.
