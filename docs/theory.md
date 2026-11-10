# Teoría y metodología de MUSA

Referencia de MUSA 1.1.0, revisada el 2 de noviembre de 2026. El motor Python y el plugin QGIS usan estas operaciones; las rutas descriptiva y de diagnóstico aplican criterios distintos. Esta referencia sustituye las notas antiguas mezcladas con controles de la interfaz Tk.

## 1. Dominio, medida y escalas

Sea Ω el dominio observado y ε el lado de una caja de la cuadrícula. MUSA analiza datos espaciales 2D:

| Entrada | Medida mᵢ(ε) |
| --- | --- |
| Puntos | Número de puntos de la caja |
| Lineamientos | Longitud de trazas dentro de la caja y del dominio |

En el caso de líneas, las coordenadas GIS ordinarias deben estar en una proyección métrica. Cambiar la etiqueta del CRS no reproyecta coordenadas. Para puntos, la normalización por defecto escala cada eje a su intervalo observado; puede cambiar la relación de aspecto y no conserva metros ni distancias físicas. Desactivarla cuando sea necesario conservar esas coordenadas.

Para cada escala se consideran las cajas ocupadas y se normaliza:

$$
p_i(\varepsilon)=\frac{m_i(\varepsilon)}{\sum_{j:m_j>0}m_j(\varepsilon)}.
$$

Las cajas vacías no entran como probabilidades cero en los momentos negativos. Un umbral de longitud por caja del flujo descriptivo puede retirar cajas y modificar la medida; se aplica sobre la longitud acumulada completa de la caja, no sobre cada segmento. Debe registrarse y justificarse.

El tratamiento de duplicados depende de la ruta: la preparación descriptiva no garantiza una unión única de todos los segmentos; las ventanas móviles disuelven coincidencias exactas y el diagnóstico independiente rechaza multiplicidad coincidente. Comparar resultados exige armonizar y documentar ese preprocesamiento.

Un conjunto finito de segmentos rectos no vacíos tiene dimensión geométrica asintótica 1. Un Dq mayor que 1 estimado en una red de trazas describe organización en un intervalo observable; no demuestra un límite fractal de esa cartografía.

## 2. Dimensiones generalizadas de Rényi y exponente de masa

Para q distinto de 1, se define la función de partición:

$$
Z_q(\varepsilon)=\sum_i p_i(\varepsilon)^q.
$$

Si existe escalamiento en un intervalo, se estudia:

$$
Z_q(\varepsilon)\sim\varepsilon^{\tau(q)},\qquad
D_q=\frac{\tau(q)}{q-1}.
$$

MUSA estima Dq mediante la pendiente de la entropía de Rényi frente a x = ln(1/ε):

$$
H_q(\varepsilon)=\frac{\ln Z_q(\varepsilon)}{1-q}.
$$

Los casos límite se calculan sin dividir por cero:

$$
H_0(\varepsilon)=\ln N_{\rm ocupadas}(\varepsilon),
\qquad
H_1(\varepsilon)=-\sum_i p_i(\varepsilon)\ln p_i(\varepsilon).
$$

D0 es la pendiente de capacidad, D1 la de información y D2 la de correlación asociada a esta medida por cajas. No confundir este D2 de longitud por cajas con una estimación de correlación de centroides de fracturas: cambiar el objeto y la medida puede cambiar la comparación.

El exponente se exporta como τ(q) = (q−1)Dq. En q=1, τ(1)=0 es una identidad de normalización, no evidencia de una recta ajustada ni un motivo para inventar R².

| Orden q | Énfasis |
| --- | --- |
| q negativo | Cajas ocupadas con probabilidad pequeña; mayor sensibilidad a resolución y fragmentos pequeños |
| q=0 | Número de cajas ocupadas |
| q=1 | Entropía de Shannon |
| q positivo creciente | Concentración en cajas de probabilidad grande |

La familia Dq, no creciente bajo los supuestos teóricos apropiados, aporta más información que una sola dimensión. Las pendientes finitas pueden desviarse por rango, muestreo o cuadrícula; el diagnóstico registra esa incoherencia. Variar q no convierte un análisis 2D en 3D ni crea un análisis conjunto de variables diferentes.

## 3. Espectro directo de singularidades

El estimador canónico de Chhabra–Jensen utiliza probabilidades auxiliares:

$$
\mu_i(q,\varepsilon)=\frac{p_i(\varepsilon)^q}{Z_q(\varepsilon)}.
$$

Se calculan los integrandos:

$$
A_q(\varepsilon)=\sum_i\mu_i\ln p_i,\qquad
F_q(\varepsilon)=\sum_i\mu_i\ln\mu_i.
$$

Alpha(q) y f(alpha(q)) son las pendientes de A y F frente a ln ε, respectivamente. De forma equivalente, se pueden cambiar los signos de ambos integrandos y usar ln(1/ε). El flujo descriptivo usa la primera convención para alpha/f; el diagnóstico usa la segunda. No cambiar solamente el signo del eje.

El cálculo directo evita estimar alpha como una derivada numérica de τ. La relación de Legendre alpha = dτ/dq requiere los supuestos de una misma medida y regularidad; no es el algoritmo utilizado para obtener alpha en MUSA.

Para cálculos consistentes se comprueban:

$$
\tau(q)=(q-1)D_q,\qquad f(\alpha(q))=q\alpha(q)-\tau(q).
$$

Estas identidades algebraicas ayudan a detectar inconsistencias de implementación. Cumplirlas no prueba que los datos tengan escalamiento. Dq se contrasta con el soporte planar en el diagnóstico; no se impone automáticamente la misma cota a alpha ni se rechaza un τ negativo por su signo.

Los pesos se evalúan en dominio logarítmico para evitar desbordamientos. El número efectivo de cajas enfatizadas por un q se calcula como:

$$
N_{\rm eff}(q,\varepsilon)=\frac{1}{\sum_i\mu_i^2}.
$$

Si casi todo el peso corresponde a una sola caja, el diagnóstico de soporte puede resultar insuficiente aunque el ajuste aparente tenga R² alto.

## 4. Tres referencias de singularidad distintas

| Referencia | Definición |
| --- | --- |
| Alpha en q=0 | Valor evaluado y utilizable en q=0; no se interpola desde un q vecino |
| Máximo observado | Alpha correspondiente al mayor f entre puntos utilizables; conserva empates y marca extremos |
| Pico cuadrático | Vértice de un ajuste descriptivo sobre f(alpha), sujeto a rango, concavidad y degeneración |

El término modo no debe usarse sin especificar cuál de esas referencias se está mostrando. Un vértice cuadrático no es la moda de un histograma de alpha. Con exactamente tres puntos, la parábola se etiqueta como interpolación descriptiva. Si el ajuste no es cóncavo, es degenerado o deja el vértice fuera del intervalo observado, el pico se conserva ausente.

Delta alpha es el rango observado de alpha sobre q utilizables. No equivale al ancho de un espectro extrapolado hasta q infinitos. El orden de conexión de las curvas es el de q y se interrumpe en puntos rechazados; ordenar alpha no debe ocultar retornos o huecos. Ver [SPECTRA.md](SPECTRA.md).

## 5. Dos rutas de cálculo y dos contratos de calidad

| Aspecto | analysis: flujo descriptivo | assessment: diagnóstico independiente |
| --- | --- | --- |
| Entrada principal | run_analysis / execute_analysis | assess_lineament_scaling / musa:scaling_support |
| Objetivo | Estimar y exportar espectros y productos locales | Evaluar compatibilidad en un intervalo declarado |
| Orígenes | Global descriptivo: origen de la partición; ventanas: uno u opción de 16 | Cuatro orígenes desplazados fijos |
| Filtro global | R² de Dq, alpha y f superior a min_r2 | Resolución, escalas, cobertura, soporte, estabilidad y modelos |
| Zeta | Disponible en estimadores locales separados | No se aplica |
| Piso de probabilidad | Opcional para q negativos | No se aplica |
| Q rechazados | Se registran; el flujo puede fallar si quedan menos de dos aceptados | Se conservan todos los q y sus causas, aunque ninguno tenga respaldo |

run_analysis usa el filtro triple de R² con desigualdad estricta. Su valor predeterminado es 0,9. RunConfig exige al menos cuatro divisores internos; ese requisito técnico no certifica un intervalo de escalamiento suficiente.

El diagnóstico de ScalingOptions aplica, por defecto:

- Resolución observacional positiva, declarada por quien conoce los datos.
- Escalas no menores que esa resolución ni mayores que un cuarto del lado menor del soporte.
- Al menos ocho escalas restantes y una década de amplitud.
- Al menos 80 % del área nominal observada y dos cajas efectivas.
- R² lineal al menos 0,98; variación máxima de pendiente de 0,10 ante exclusión/recorte de escalas y cambios de origen.
- Comparación con modelos cuadrático y segmentado mediante predicción leave-one-scale-out. El punto de cambio se vuelve a seleccionar dentro de cada entrenamiento, sin usar el valor retenido.

Se marca una alternativa si mejora suficientemente la predicción con los criterios registrados; no se busca después un subintervalo favorable. Las curvas se promedian entre los cuatro orígenes antes del ajuste y se conserva la sensibilidad por origen.

| Estado | Alcance |
| --- | --- |
| compatible_finite_range | Cumple los criterios operativos en ese intervalo |
| not_supported | Hay observaciones suficientes, pero fallan criterios de ajuste, estabilidad o forma |
| insufficient_information | No alcanza resolución, cobertura, rango, número de escalas o soporte efectivo |

Cada observable tiene su propio estado. Un Dq compatible no asegura alpha o f(alpha) respaldados. Los números calculados y rechazados pueden conservarse para auditoría; los ausentes no son cero.

Una malla periódica puede parecer compatible en un intervalo finito. El control ampliado detectó su cambio de régimen al incluir su separación característica. Por ello estos estados no equivalen a una clasificación universal de fractal/no fractal. Detalles en [SCALING_SUPPORT.md](SCALING_SUPPORT.md).

## 6. Celdas madre, ventanas móviles y cobertura

Las celdas madre forman la partición local del flujo descriptivo. Su lado es la resolución máxima de ese flujo; las hijas estrictamente menores alimentan la regresión. Las probabilidades se normalizan dentro de cada madre.

La ruta histórica asigna hijas a madres por centroide. Si se suministran manualmente escalas no compatibles con la madre, una hija puede cruzar una frontera y su masa no equivaler a un recorte exacto de esa madre. El constructor de resoluciones madre/divisor ayuda a definir una cuadrícula compatible.

Las ventanas móviles separan lado L, paso entre centros y tamaños internos ε = L/divisor. Recortan líneas al soporte observado y calculan probabilidades dentro de cada ventana. Pueden conservar orígenes múltiples y estimaciones canónicas/ponderadas separadas. Son experimentales y no requieren que cada q pase el ajuste global para calcular sus estimaciones propias; el flujo execute_analysis, sin embargo, debe terminar antes su etapa global.

La cobertura de área es área(ventana ∩ Ω)/L². No equivale al porcentaje de cajas ocupadas utilizado dentro de zeta. Un cuadrante de un círculo inscrito tiene cobertura π/4 ≈ 0,785, inferior al mínimo 0,8. Es una razón geométrica de insuficiencia, no un fallo a corregir llenando datos fuera del dominio.

Los benchmarks conservan cuadrantes y añaden centros interiores declarados geométricamente. Las ventanas solapadas comparten información: no son réplicas independientes ni pueden repartirse sin control espacial entre entrenamiento y prueba. Ver [moving_windows.md](moving_windows.md).

## 7. Ponderación operacional zeta

Zeta pondera escalas locales; no reemplaza las probabilidades de la medida ni es una nueva dimensión multifractal. La forma operacional del código es:

$$
\zeta(\varepsilon)=C^{a}R^{b}S^{c}E^{d}.
$$

| Factor | Cálculo |
| --- | --- |
| C | Cajas ocupadas / cajas posibles del soporte a esa escala |
| R | Masa local a esa escala / masa local en la escala más fina |
| S | Piso + (1−piso) × ln(ε_gruesa/ε) / ln(ε_gruesa/ε_fina), con posición acotada a [0,1] |
| E | exp(H1) / número de cajas ocupadas, acotado a [0,1] |

Los exponentes predeterminados son (1,1,1,1) y el piso de escala es 0,25. E mide dispersión de la masa mediante Shannon y no es el mismo N_eff(q) de los pesos auxiliares. Si se conserva toda la longitud, R debe ser aproximadamente 1; umbrales o preparación pueden modificarlo.

Para celdas madre alineadas, las cajas posibles se calculan con el cuadrado del divisor redondeado. Las ventanas con orígenes desplazados usan su conteo de cajas posibles correspondiente; las cajas parciales no se convierten automáticamente en exposiciones de igual área. La sensibilidad de borde debe revisarse por separado.

La regresión ponderada conserva alpha_w, f_alpha_w y Dq ponderado cuando está disponible, separados de los canónicos. La condición reliable añade los umbrales de zeta y R² de su producto; no es una probabilidad calibrada. La [guía de candidatos](candidate_scoring.md) describe el perfil experimental, sin introducir un puntaje de prospectividad.

## 8. Estabilización, robustez e incertidumbre

El piso opcional para q negativos modifica p antes del cálculo descriptivo. Para N cajas ocupadas y fracción configurada η, el código usa:

$$
p_{\min}=\min\left(\frac{0.5}{N},\frac{\eta\max(|q|,1)}{N}\right),\qquad
p'_i=\frac{\max(p_i,p_{\min})}{\sum_j\max(p_j,p_{\min})}.
$$

Con η=0 no se aplica. Al depender de q, esta regularización no representa estrictamente la misma medida sin modificar en todos los momentos; debe reportarse y compararse con la ruta sin piso. El diagnóstico independiente conserva la medida original y controla dominancia en lugar de aplicar ese piso.

Con cualquier η > 0 y q < 0, Hq(p′) − ln N queda acotada por una constante independiente de la escala. Si existe un régimen de escalamiento, la pendiente regularizada tiende entonces a D0: el piso no puede conservar un espectro negativo distinto de D0. Ver la derivación y la evaluación con verdad conocida en [q negativos](NEGATIVE_Q.md).

Bootstrap de escalas, jackknife, Theil–Sen, leverage y Cook evalúan sensibilidad del ajuste. No representan por sí solos errores de levantamiento, incertidumbre de trazado ni independencia espacial. El valor p de pendiente del ajuste descriptivo tampoco equivale al contraste nulo espacial ni a una probabilidad de fractalidad.

## 9. Contraste espacial condicional

Cuando se solicita, el diagnóstico compara T = D0−D2 con traslaciones uniformes independientes de las formas de traza suministradas, contenidas en el mismo polígono. Conserva forma, longitud, orientación, número y masa; cambia posiciones, cruces y dependencia espacial.

Si las entradas ya se nodificaron por una unión geométrica, las unidades conservadas son esas partes, no necesariamente las fracturas interpretadas originales. Declarar ese inventario.

Con B réplicas válidas y cola superior:

$$
p=\frac{1+\#\{T_{\rm sim}\ge T_{\rm obs}\}}{B+1}.
$$

No se descartan simulaciones incómodas hasta obtener un resultado favorable. Si no se puede colocar una realización o falta respaldo de q0/q2, no se inventa un valor p. Holm corrige la familia de soportes del informe; una familia adicional de benchmarks debe identificarse por separado. Los q correlacionados no se cuentan como pruebas independientes nuevas.

El contraste estudia heterogeneidad condicional bajo ese modelo de traslación. Un rechazo no demuestra multifractalidad y un no rechazo no prueba homogeneidad o ausencia de estructura. La calibración y potencia generales siguen pendientes.

## 10. Descriptores espaciales y topología

La longitud registrada en la escala fina permite obtener intensidad estructural sobre el área observada. No se suman longitudes de la misma red repetidas en varias escalas como si fueran masa adicional.

El índice histórico d_local_index = −ln(pᵢ)/ln(L/ε) es un cociente local a una escala; no reemplaza una regresión Dq ni una dimensión física demostrada.

La topología móvil obtiene nodos únicos de la unión planar exacta: I extremo, Y grado 3, X grado 4 y complejo de grado superior. El grafo histórico de network.py cuenta líneas y pares relacionados: no es el mismo inventario de nodos geográficos. Sin snapping, los casi cruces continúan separados. Ni un cruce planar ni una proximidad verifican conectividad hidráulica 3D.

## 11. Evidencia y límites de interpretación

El núcleo de partición/cálculo canónico se contrastó con una cascada 2D de 65.536 segmentos y pesos diádicos: error máximo Dq/τ/alpha/f de aproximadamente 2,09 × 10⁻¹⁴ en una cuadrícula alineada y escalas finitas. Esa prueba algebraico-geométrica no certifica precisión para cualquier origen, resolución o cartografía.

La validación ampliada incluye 67 casos procesables de fuentes públicas, modelos, variantes y controles; no son 67 afloramientos independientes. Se conservaron máscaras vacías y fuentes no descargadas con sus estados reales. Las comparaciones entre figuras rasterizadas, centroides, líneas y medidas ponderadas necesitan correspondencia de dominio y medida.

Los tres niveles de afirmación deben permanecer separados:

1. Fórmulas, conservación y coherencia numérica comprobadas en controles definidos.
2. Compatibilidad de datos con un modelo en un intervalo resoluble, con calidad y sensibilidad explícitas.
3. Interpretación física o geológica validada mediante evidencia externa.

MUSA integra cálculos y diagnósticos de los dos primeros niveles. No convierte automáticamente sus salidas en permeabilidad, favorabilidad, conexión 3D ni una prueba universal de multifractalidad.

## Guías relacionadas

- [Arquitectura](ARCHITECTURE.md): núcleo compartido e instantánea privada del plugin.
- [API Python](PYTHON_API.md): ejemplos y contratos de ejecución sin QGIS.
- [Salidas](OUTPUTS.md): archivos, campos, unidades y estados.
- [Espectros por soporte](SPECTRA.md): fuentes y referencias de singularidad.
- [Alcance de validación](SCALING_VALIDATION_STATUS.md) y [benchmarks públicos](EXTENDED_BENCHMARKS.md).
- [Referencias científicas](references.md): distinguir métodos implementados de antecedentes y fuentes de datos.
