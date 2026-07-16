# Teoría y metodología de MUSA

Este documento describe con precisión cómo MUSA calcula descriptores fractales y multifractales en su implementación actual. Está alineado con `src/musa/core.py` y con los CSV exportados por `export_cell_outputs`.

MUSA trabaja con dos niveles complementarios:

1. **Análisis global** (`run_analysis`): espectro multifractal del dominio completo.
2. **Análisis espacial local** (`export_cell_outputs`): descriptores por celda hija y por celda madre.

Ambos usan el método directo de **Chhabra y Jensen** para estimar `alpha` y `f(alpha)`. El exponente de masa `tau(q)` se reporta como magnitud derivada de `Dq`, pero **no** se usa para calcular el espectro mediante derivada numérica.

---

## 1. Objetos geométricos y medida

### 1.1 Grilla y escalas

MUSA construye una grilla regular de celdas cuadradas de lado `epsilon` (metros en flujo GIS, o unidades normalizadas en arrays).

Las escalas se definen como:

- **GIS:** `resolutions_m`, por ejemplo `[4000, 2000, 1000, 500, 250]`.
- **Arrays normalizados:** `logspace` entre `min_scale` y `max_scale`.

Requisitos de validación:

- Al menos **3 escalas** distintas y positivas.
- Escalas ordenadas de gruesa a fina.

En flujo GIS con celda madre:

- `mother_scale = max(resolutions_m)` (p. ej. 4000 m).
- `finest_scale = min(resolutions_m)` (p. ej. 250 m).
- Las escalas de regresión local son las hijas: `epsilon < mother_scale`.

### 1.2 Medida por celda `m_i`

| Tipo de dato     | Medida `m_i`                                          |
| ---------------- | ----------------------------------------------------- |
| Puntos           | conteo de puntos en la celda                          |
| Lineamientos GIS | longitud total de línea intersectada con la celda (m) |

Un umbral `cell_length_threshold_m` puede excluir celdas cuya longitud intersectada sea demasiado pequeña. Esas celdas no entran en el diccionario de medidas.

### 1.3 Probabilidad `P_i`

En cada escala `epsilon`, sobre un conjunto de celdas con medida positiva:

```
P_i(epsilon) = m_i / sum_j m_j
```

**Importante:** el dominio de normalización depende del flujo.

| Flujo                         | Dominio de normalización                             |
| ----------------------------- | ---------------------------------------------------- |
| Global (`run_analysis`)       | todas las celdas ocupadas del **boundary completo**  |
| Local (`export_cell_outputs`) | solo las celdas hijas dentro de **cada celda madre** |

Esta distinción es central: el mapa local no repite el espectro global restringido mecánicamente; recalcula `P_i` y `mu_i` en cada ventana madre.

---

## 2. Función de partición y dimensiones de Rényi

### 2.1 Función de partición

```
Z(q, epsilon) = sum_i P_i(epsilon)^q
```

### 2.2 Exponente de masa

```
tau(q) = (q - 1) * D_q
```

MUSA calcula `tau` **después** de estimar `Dq` aceptados. Se exporta en `analysis_report.csv` como descriptor derivado.

### 2.3 Dimensión generalizada `D_q`

Definición teórica para `q != 1`:

```
D_q = (1 / (q - 1)) * lim_{epsilon->0} [ ln Z(q, epsilon) / ln epsilon ]
```

#### Implementación numérica global

Para cada `q` y cada escala, MUSA construye una feature escalar:

**Caso `q != 0` y `q != 1`:**

```
phi_q(epsilon) = - ln( sum_i P_i^q ) / (q - 1)
```

**Caso `q = 0` (dimensión de capacidad):**

```
phi_0(epsilon) = ln( N_boxes )
```

donde `N_boxes` es el número de celdas con medida positiva.

**Caso `q = 1` (dimensión de información):**

```
phi_1(epsilon) = - sum_i P_i ln P_i     (entropía de Shannon)
```

Luego regresiona:

```
D_q = slope( phi_q  vs  ln(1/epsilon) )
```

Convención de signo: el eje usa `ln(1/epsilon)` para recuperar dimensiones positivas en patrones uniformes 2D (`D_q = 2`).

---

## 3. Medida de soporte `mu_i(q, epsilon)`

Para el espectro de singularidad, en cada escala y cada `q`, MUSA define pesos `mu_i`.

### 3.1 Rango de `q` en MUSA

Por defecto en la interfaz GIS:

```
q in {-4, -3, -2, -1, 0, 1, 2, 3, 4}
```

Es decir, **sí puede ir de −4 a 4** (paso 1). El usuario puede cambiar `q-min`, `q-max` y `q-step` en la UI o pasar `q_values` en código.

MUSA **evalúa todos los `q` solicitados**, pero el filtro de calidad puede **eliminar** algunos (sobre todo negativos extremos) si no alcanzan `R² > min_r2` en `Dq`, `alpha` y `f(alpha)`.

| `q` probado          | Fórmula de `mu_i`                    |
| -------------------- | ------------------------------------ |
| `q = -4, -3, -2, -1` | caso general (`P_i^q / sum P_j^q`) |
| `q = 0`              | caso especial capacidad              |
| `q = 1`              | caso especial información            |
| `q = 2, 3, 4`        | caso general                         |

Los casos `q = 0` y `q = 1` son **límites matemáticos**, no un límite del rango permitido.

### 3.2 Fórmulas de `mu_i`

**Caso general (`q != 0` y `q != 1`), incluye `q` negativos:**

```
mu_i = P_i^q / sum_j P_j^q
```

Para `q < 0`, celdas con `P_i` muy pequeño reciben peso alto en `mu_i`. Por eso los `q` negativos extremos son numéricamente sensibles y a menudo se rechazan en datos geológicos reales.

La implementación actual permite aplicar `negative_q_floor_fraction` como piso adaptativo opcional sobre `P_i` antes de calcular `mu_i` cuando `q < 0`.

**Caso `q = 0`:**

```
mu_i = 1 / N_boxes
```

sobre celdas ocupadas.

**Caso `q = 1`:**

```
mu_i = P_i
```

Estos casos están implementados en `_mu_for_q`.

### 3.3 Qué se exporta según el filtro

- `analysis_report.csv`: incluye `q` aceptados y eliminados, con sus métricas de ajuste.
- `multifractal_mother_agg.csv`: un bloque de filas por cada `q` aceptado.
- **Gráficos locales:** se generan para todos los `q` aceptados; el gráfico inicial conserva un `q` de referencia próximo a 2.

Ejemplo típico en lineamientos GIS:

- probados: −4, −3, −2, −1, 0, 1, 2, 3, 4
- aceptados: −1, 0, 1, 2, 3, 4
- eliminados: −4, −3, −2

---

## 4. Espectro de singularidad: método de Chhabra y Jensen

### 4.1 Integrandos por escala

Para cada escala `epsilon` y cada `q`:

```
A_q(epsilon) = sum_i mu_i(q, epsilon) * ln P_i(epsilon)
F_q(epsilon) = sum_i mu_i(q, epsilon) * ln mu_i(q, epsilon)
```

En el flujo local por celda, la suma recorre solo celdas hijas de una madre y `P_i`, `mu_i` son locales a esa madre.

### 4.2 Regresión de `alpha` y `f(alpha)`

MUSA estima:

```
alpha(q) = slope( A_q(epsilon)  vs  ln epsilon )
f(alpha(q)) = slope( F_q(epsilon)  vs  ln epsilon )
```

Eje horizontal: `ln epsilon` (no `ln(1/epsilon)`).

### 4.3 Descomposición por celda hija

En `multifractal_cells.csv`, cada celda exporta:

```
alpha_integrand_contrib_i = mu_i * ln P_i
f_integrand_contrib_i     = mu_i * ln mu_i
```

Estas contribuciones son **aditivas** dentro de una madre y escala:

```
sum_i alpha_integrand_contrib_i = A_q(epsilon)
sum_i f_integrand_contrib_i     = F_q(epsilon)
```

No son dimensiones puntuales; son la descomposición espacial del integrando multifractal.

### 4.4 Método alternativo no implementado: transformada de Legendre

En la literatura clásica también aparece:

```
alpha(q) = d tau / d q
f(alpha) = q * alpha - tau(q)
```

Esa vía exige estimar `tau(q)` en muchos valores de `q` y derivar numéricamente. MUSA **no** usa este camino. La implementación actual sigue Chhabra–Jensen directo porque:

- permite regresión independiente por `q`;
- evita derivadas numéricas de `tau`;
- admite control de calidad separado para `Dq`, `alpha` y `f(alpha)`.

Ambos enfoques son teóricamente relacionados en condiciones ideales; con pocos `q` o pocas escalas pueden divergir numéricamente.

---

## 5. Análisis global (`run_analysis`)

### 5.1 Entrada

- Dominio completo (boundary o array normalizado).
- Lista de escalas `epsilon`.
- Lista de momentos `q`.

### 5.2 Salida principal

Archivo `analysis_report.csv`:

| Campo                          | Significado                              |
| ------------------------------ | ---------------------------------------- |
| `dq`                           | dimensión generalizada `D_q`             |
| `tau`                          | `(q-1)*D_q`                              |
| `alpha`                        | exponente de singularidad por CJ         |
| `f_alpha`                      | dimensión del soporte asociada           |
| `r2`, `alpha_r2`, `f_alpha_r2` | calidad de ajuste por `q`               |
| `*_ci_low`, `*_ci_high`        | intervalos bootstrap, cuando se activan |
| `alpha_ts`, `f_alpha_ts`       | pendientes robustas Theil–Sen            |
| `*_jackknife_std`              | sensibilidad leave-one-scale-out         |

### 5.3 Filtro de calidad

Un `q` se **acepta** solo si:

```
R2(D_q) > min_r2
R2(alpha) > min_r2
R2(f_alpha) > min_r2
```

Por defecto `min_r2 = 0.9`. Los `q` rechazados se listan en el mismo reporte.

Si quedan menos de 2 `q` aceptados, el análisis falla con error explícito.

### 5.4 Diagnóstico global por escala

`analysis_scale_diagnostics.csv` exporta resultados leave-one-scale-out, leverage y distancia de Cook para detectar escalas dominantes o inestables.

---

## 6. Análisis espacial local por celda madre

### 6.1 Jerarquía madre–hija

- **Celda madre:** ventana cuadrada de lado `mother_scale`.
- **Celdas hijas:** celdas de resoluciones más finas contenidas en la madre.
- Cada celda hija se asigna a una madre por índice `(mother_ix, mother_iy)`.

### 6.2 Escalas usadas en la regresión local

| Escala                                   | Uso                                                  |
| ---------------------------------------- | ---------------------------------------------------- |
| `epsilon = mother_scale`                 | no entra en regresión local (`ln(mother/epsilon)=0`) |
| `mother_scale > epsilon >= finest_scale` | sí entra en regresión                                |

### 6.3 Procedimiento por madre `M` y escala hija `epsilon`

1. Agrupar celdas hijas ocupadas en la madre.
2. Calcular `m_total(M, epsilon) = sum_i m_i`.
3. Calcular probabilidades locales `P_i = m_i / m_total`.
4. Calcular `mu_i(q)` con las reglas de la sección 3.
5. Acumular integrandos `A_q`, `F_q`.
6. Tras recorrer todas las escalas hijas, regredir `A_q` y `F_q` contra `ln epsilon`.

Resultado por `(mother_ix, mother_iy, q)`:

| Estimador                | Método                                  |
| ------------------------ | --------------------------------------- |
| `alpha`, `f_alpha`       | mínimos cuadrados ordinarios (OLS)      |
| `alpha_w`, `f_alpha_w`   | mínimos cuadrados ponderados por `zeta` |
| `alpha_ts`, `f_alpha_ts` | regresión robusta Theil–Sen             |

El agregado local también puede exportar intervalos bootstrap, sensibilidad jackknife y el indicador `reliable`.

---

## 7. Peso de confiabilidad `zeta` (ζ)

`zeta` cuantifica qué tan confiable es cada punto `(M, epsilon)` de la regresión local. Se exporta en:

- `multifractal_cells.csv` / `monofractal_cells.csv`: columna `zeta` por celda y escala.
- agregados madre: `zeta_mean`, `zeta_min`.

### 7.1 Definición

Para una celda madre `M`, escala hija `epsilon`, masa total `m_total(M, epsilon)`, masa fina `m_finest(M) = m_total(M, epsilon_fino)` y `N_ocup` celdas hijas ocupadas:

**Cobertura**

```
c = N_ocup / N_posible
N_posible = (mother_scale / epsilon)^2
```

**Masa relativa**

```
m_r = m_total(M, epsilon) / m_finest(M)
```

**Factor de escala**

```
s = ln(epsilon_grueso / epsilon) / ln(epsilon_grueso / epsilon_fino)
```

donde `epsilon_grueso` y `epsilon_fino` son la escala hija más gruesa y más fina usadas en la regresión local.

**Peso total baseline**

```
zeta(M, epsilon) = c * m_r * s
```

La implementación actual permite variar exponentes:

```
zeta(M, epsilon) = c^a * m_r^b * s^g
```

El baseline usa `(a, b, g) = (1, 1, 1)`. Las variantes deben interpretarse como sensibilidad metodológica.

### 7.2 Uso en regresión ponderada

Para cada madre y `q`, MUSA ajusta:

```
alpha_w = slope_w( A_q vs ln epsilon ; pesos = zeta )
f_alpha_w = slope_w( F_q vs ln epsilon ; pesos = zeta )
```

Los pesos se normalizan internamente a suma 1. Puntos con `zeta <= 0` no aportan al ajuste ponderado.

### 7.3 Interpretación de `zeta`

| Factor     | Lectura                                                      |
| ---------- | ------------------------------------------------------------ |
| `c` bajo   | madre parcialmente vacía a esa escala                        |
| `m_r` bajo | poca longitud estructural relativa respecto a la escala fina |
| `s` bajo   | escala más gruesa dentro del rango de regresión              |

`zeta = 0` puede ocurrir, por ejemplo, en la escala gruesa del rango porque `s = 0`. Eso es coherente con la definición actual.

### 7.4 Cuándo usar OLS vs ponderado

| Estimador               | Rol recomendado                                                      |
| ----------------------- | -------------------------------------------------------------------- |
| `alpha`, `f_alpha`      | referencia canónica Chhabra–Jensen local; comparable con literatura |
| `alpha_w`, `f_alpha_w`  | alternativa para madres dispersas o con cobertura heterogénea       |
| `zeta_mean`, `zeta_min` | diagnóstico de confiabilidad antes de interpolar                    |
| `reliable`              | filtro operativo por `zeta_mean` y R² ponderados                    |

No hay un criterio universal de superioridad: deben compararse en validación sintética y en el caso geológico concreto.

---

## 8. Flujo monofractal local

Además del multifractal, MUSA exporta descriptores monofractales por madre.

### 8.1 Integrandos por madre y escala

```
N_boxes(M, epsilon) = numero de celdas hijas ocupadas
H(M, epsilon) = - sum_i P_i ln P_i        (entropía local)
```

### 8.2 Regresiones monofractales por madre

| Descriptor | Regresión OLS                   | Regresión ponderada     | Regresión robusta |
| ---------- | ------------------------------- | ----------------------- | ----------------- |
| `d0_local` | `ln N_boxes` vs `ln(1/epsilon)` | `d0_w` con pesos `zeta` | `d0_ts`           |
| `d1_local` | `H` vs `ln(1/epsilon)`          | `d1_w` con pesos `zeta` | `d1_ts`           |

El archivo agregado puede incluir intervalos bootstrap, sensibilidad jackknife y banderas `d0_reliable` y `d1_reliable`.

### 8.3 Índice puntual `d_local_index`

En `monofractal_cells.csv`:

```
d_local_index = - ln(P_i) / ln(mother_scale / epsilon)
```

Es un índice relativo por celda y escala. **No** debe interpretarse como `D_q` ni como dimensión física estricta.

### 8.4 Intensidad estructural `measure_sum_m`

```
measure_sum_m(M) = m_total(M, epsilon_fino)
```

Se calcula **solo en la escala más fina** para evitar contar varias veces la misma longitud al refinar la grilla.

---

## 9. Interpretación de `q`

Cada valor de `q` actúa como una lupa distinta sobre la distribución de medida:

| `q`     | Énfasis típico                       |
| ------- | ------------------------------------ |
| `q < 0` | estructuras raras o muy dispersas    |
| `q = 0` | soporte / capacidad                  |
| `q = 1` | distribución promedio (información)  |
| `q > 1` | zonas densas                         |

Reglas operativas en MUSA:

- no mezclar distintos `q` en un mismo mapa;
- exportar localmente solo `q` aceptados globalmente si se usa la interfaz o `examples/run_musa.py` actualizado;
- interpretar `q` negativos extremos con cautela y documentar si se usa un piso adaptativo.

---

## 10. Archivos de salida y columnas clave

### 10.1 Global

`analysis_report.csv`

- `dq`, `tau`, `alpha`, `f_alpha`
- `r2`, `alpha_r2`, `f_alpha_r2`
- intervalos bootstrap opcionales
- `alpha_ts`, `f_alpha_ts`
- desviaciones jackknife
- filas `accepted` / `eliminated`

`analysis_scale_diagnostics.csv`

- leave-one-scale-out, leverage y Cook por `q` y escala.

### 10.2 Por celda hija

`multifractal_cells.csv`

- geometría: `scale_m`, `cell_ix`, `cell_iy`, `centroid_x`, `centroid_y`
- estado local: `measure_m`, `p_i`, `mu_i_q`
- descomposición CJ: `alpha_integrand_contrib`, `f_integrand_contrib`
- contexto: `q`, `zeta`, `mother_ix`, `mother_iy`

`monofractal_cells.csv`

- `measure_m`, `p_i`, `d_local_index`, `zeta`, `mother_ix`, `mother_iy`

### 10.3 Por celda madre

`multifractal_mother_agg.csv`

- posición: `mother_centroid_x`, `mother_centroid_y`
- intensidad: `measure_sum_m`, `cells_count`
- canónico: `alpha`, `f_alpha`, `alpha_r2`, `f_alpha_r2`
- ponderado: `alpha_w`, `f_alpha_w`, `alpha_w_r2`, `f_alpha_w_r2`
- robusto: `alpha_ts`, `f_alpha_ts`, `alpha_ts_r2`, `f_alpha_ts_r2`
- incertidumbre: intervalos bootstrap y sensibilidad jackknife
- diagnóstico: `zeta_mean`, `zeta_min`, `scales_count`, `q`, `reliable`
- configuración: exponentes y umbrales de confiabilidad

`monofractal_mother_agg.csv`

- `measure_sum_m`, `cells_count`
- `d0_local`, `d1_local`, `d0_r2`, `d1_r2`
- `d0_w`, `d1_w`, `d0_w_r2`, `d1_w_r2`
- `d0_ts`, `d1_ts`, sus R², intervalos y jackknife
- `zeta_mean`, `zeta_min`, `scales_count`, `d0_reliable`, `d1_reliable`

`multifractal_mother_scale_diagnostics.csv`

- diagnósticos leave-one-scale-out, leverage y Cook por madre, `q` y escala.

`multifractal_mother_zeta_sensitivity.csv`

- resultados del barrido de exponentes, cuando se activa la exportación de sensibilidad.

### 10.4 Productos gráficos

**Análisis global** (`export_analysis_plots`):

| Archivo                                 | Contenido estadístico                                             |
| --------------------------------------- | ----------------------------------------------------------------- |
| `multifractal_singularity_spectrum.png` | curva global `f(alpha)` vs `alpha` (OLS, por `q` aceptado)        |
| `dq_scatterplot.png`                    | `Dq` vs `q`, color = `R²`                                         |
| `r2_fit_quality.png`                    | `R²` de `Dq`, `alpha`, `f(alpha)` vs `q` (aceptados y eliminados) |

**Análisis local por celda madre** (`export_mother_plots`, requiere agregación madre):

| Archivo                              | Contenido estadístico                            |
| ------------------------------------ | ------------------------------------------------ |
| `mother_weighted_spectrum_q*.png`    | nube local `(alpha_w, f_alpha_w)` + curva global |
| `mother_local_spectrum_envelope.png` | espectro global vs nube local (todos los `q`)    |
| `mother_spatial_alpha_w_q*.png`      | mapa espacial de `alpha_w`                       |
| `mother_spatial_zeta.png`            | mapa espacial de confiabilidad `zeta_mean`       |
| `mother_spatial_measure_sum_m.png`   | mapa de intensidad estructural                   |
| `mother_ols_vs_weighted_q*.png`      | comparación `alpha` vs `alpha_w`                 |
| `mother_zeta_histogram.png`          | distribución de `zeta_mean`                      |

Los tres productos con sufijo `q*` se generan para cada `q` aceptado; el gráfico inicial conserva el `q` más cercano a 2 como referencia.

### 10.5 Campos estadísticos adicionales

**Global (`analysis_report.csv`):**

- `p_value`: significancia del ajuste de `Dq` por `q` (exportado, no usado como filtro automático).
- intervalos bootstrap: se llenan si `bootstrap_iterations > 0`.
- `alpha_ts`, `f_alpha_ts`: pendientes robustas complementarias.
- filas `eliminated`: `q` rechazados con sus `R²` parciales para diagnóstico.

**Local (`multifractal_mother_agg.csv`):**

- `alpha_r2`, `f_alpha_r2`: calidad OLS por madre y `q`.
- `alpha_w_r2`, `f_alpha_w_r2`: calidad del ajuste ponderado por `zeta`.
- `reliable`: filtro basado en `zeta_mean`, `alpha_w_r2` y `f_alpha_w_r2`.
- intervalos bootstrap locales: se llenan si `local_bootstrap_iterations > 0`.
- `alpha_ts`, `f_alpha_ts`: pendientes robustas por madre.
- campos jackknife: sensibilidad a las escalas disponibles.
- `scales_count`: número de escalas hijas en la regresión local.
- `cells_count`: celdas hijas ocupadas a escala fina.

Estos campos permiten filtrar o ponderar en post-proceso (GIS, interpolación, paper) sin recalcular MUSA.

---

## 11. Inventario de productos estadísticos: qué está cubierto

| Pregunta analítica                               | Producto MUSA                                                 | ¿Implementado? |
| ------------------------------------------------ | ------------------------------------------------------------- | -------------- |
| ¿Es multifractal el dominio global?              | `analysis_report.csv`, espectro PNG global                    | Sí             |
| ¿Qué `q` son estables?                           | `r2_fit_quality.png`, filas accepted/eliminated               | Sí             |
| ¿Dónde hay más lineamiento?                      | `measure_sum_m`, mapa espacial                                | Sí             |
| ¿Cómo varía `alpha` espacialmente?               | `multifractal_mother_agg.csv`, mapas `alpha_w`                | Sí             |
| ¿Es confiable cada madre?                        | `reliable`, `zeta_mean`, `zeta_min`, histograma, mapa `zeta`  | Sí             |
| ¿OLS o ponderado difieren?                       | `mother_ols_vs_weighted_q*.png`, columnas duales              | Sí             |
| ¿Incertidumbre de `Dq` o `alpha`?                | bootstrap global y local opcional                             | Sí             |
| ¿Filtro automático de madres con baja calidad?   | columna `reliable`                                            | Sí             |
| ¿Regresión robusta frente a escalas atípicas?    | columnas Theil–Sen                                            | Sí             |
| ¿Sensibilidad a escalas?                         | CSV de diagnósticos y jackknife                               | Sí             |
| ¿Sensibilidad de `zeta`?                         | `multifractal_mother_zeta_sensitivity.csv` opcional           | Sí             |
| ¿Espectro local por todos los `q` en PNG?        | gráficos locales para cada `q` aceptado                       | Sí             |

**Conclusión:** los productos principales de robustez descritos como futuros en versiones anteriores ya se encuentran implementados, de forma opcional cuando su costo computacional es relevante.

---

## 12. Robustez metodológica

### 12.1 Medidas de robustez ya implementadas

| Medida                                       | Dónde                            | Efecto                                                |
| -------------------------------------------- | -------------------------------- | ----------------------------------------------------- |
| Chhabra–Jensen directo                       | global y local                   | evita derivada numérica de `tau`                      |
| Filtro R² triple global                      | `run_analysis`                   | rechaza `q` inestables en `Dq`, `alpha`, `f`          |
| Umbral de longitud por celda                 | `cell_length_threshold_m`        | elimina ruido de intersección mínima                  |
| Normalización local en madre                 | `export_cell_outputs`            | evita mezclar probabilidades del dominio completo     |
| Exclusión de escala madre en regresión local | local                            | evita `ln(1)=0`                                       |
| Peso `zeta` y exponentes configurables       | regresión local WLS              | pondera confiabilidad y permite sensibilidad          |
| Flag `reliable`                              | agregados madre                  | permite filtrado local reproducible                   |
| Bootstrap global y local                     | reportes y agregados             | aporta intervalos de confianza opcionales             |
| Theil–Sen                                    | global y local                   | compara pendientes robustas con OLS/WLS               |
| Jackknife leave-one-scale-out                | global y local                   | cuantifica sensibilidad a las escalas                 |
| Leverage / Cook por escala                   | CSV de diagnóstico               | identifica puntos influyentes                         |
| Piso adaptativo para `q < 0`                 | cálculo de `mu_i`                | mitiga inestabilidad de probabilidades muy pequeñas   |
| `measure_sum_m` solo en escala fina          | agregados madre                  | evita doble conteo de longitud                        |

### 12.2 Vulnerabilidades conocidas

1. **q negativos:** aun con piso adaptativo, amplifican la parte rara del soporte y deben interpretarse con cautela.
2. **Pocas escalas:** bootstrap y diagnósticos no reemplazan la necesidad de un rango multiescala adecuado.
3. **Madres con baja señal:** `reliable` permite filtrarlas, pero su exclusión modifica la cobertura espacial del mapa.
4. **Exponentes de zeta:** valores distintos del baseline `(1, 1, 1)` son una decisión metodológica que debe reportarse.
5. **Costo computacional:** bootstrap local y sensibilidad de `zeta` pueden aumentar notablemente el tiempo de corrida.
6. **Post-proceso espacial:** kriging, autocorrelación espacial y validación geológica siguen fuera del motor principal.

### 12.3 Controles disponibles en la interfaz

| Control | Uso |
| ------- | --- |
| Robustness Preset | selecciona baseline, balanced, experimental o custom |
| Bootstrap / Local Bootstrap | activa intervalos globales o locales |
| CI y Seed | controla intervalo y reproducibilidad |
| Reliable zeta / Reliable R2 | define la bandera `reliable` |
| Negative q floor | activa estabilización de `P_i` para `q < 0` |
| zeta exponents | define sensibilidad de cobertura, masa y escala |
| Export zeta sensitivity profiles | genera el CSV de sensibilidad |

### 12.4 Secuencia de uso recomendada

1. Revisar `analysis_report.csv`: usar solo `q` aceptados.
2. Consultar `r2_fit_quality.png` y `analysis_scale_diagnostics.csv`.
3. Para mapas de intensidad: interpolar `measure_sum_m`.
4. Para mapas multifractales: seleccionar un `q` y filtrar por `reliable`.
5. Comparar `alpha` contra `alpha_w` y, si es necesario, `alpha_ts`.
6. Activar bootstrap local y sensibilidad de `zeta` en corridas metodológicas finales.
7. Validar con patrón sintético uniforme 2D (`Dq ≈ alpha ≈ 2`) antes de interpretar geológicamente.

---

## 13. Guía de interpolación y cartografía

Coordenadas recomendadas:

- `mother_centroid_x`
- `mother_centroid_y`

Variables recomendadas según objetivo:

| Objetivo                                   | Variable                                      | Archivo                       |
| ------------------------------------------ | --------------------------------------------- | ----------------------------- |
| intensidad de lineamientos                 | `measure_sum_m`                               | `*_mother_agg.csv`            |
| espectro multifractal global               | `dq`, `alpha`, `f_alpha`                      | `analysis_report.csv`         |
| mapa multifractal local canónico           | `alpha` o `f_alpha` por `q` fijo              | `multifractal_mother_agg.csv` |
| mapa multifractal local ponderado          | `alpha_w` o `f_alpha_w` por `q` fijo          | `multifractal_mother_agg.csv` |
| mapa local robusto complementario          | `alpha_ts` o `f_alpha_ts` por `q` fijo        | `multifractal_mother_agg.csv` |
| filtrar confiabilidad espacial             | `reliable`, `zeta_mean`, R² locales           | `multifractal_mother_agg.csv` |
| complejidad monofractal local              | `d0_local`, `d1_local`, `d0_w`, `d1_w`       | `monofractal_mother_agg.csv`  |

---

## 14. Consideraciones GIS

- Datos geográficos (lat/lon) deben reproyectarse a CRS métrico antes del análisis.
- Lineamientos requieren `boundary` y `resolutions_m` explícitas.
- La medida por celda es **longitud**, no presencia binaria.
- Las celdas son cuadradas: `width = height = epsilon`.
- `resolutions_from_mother_cell(mother_cell_m, divisors)` genera escalas hijas exactas si los divisores son compatibles.

---

## 15. Validación y limitaciones

### 15.1 Validación sintética esperada

En un patrón uniforme 2D con escalas bien comportadas, el análisis global debe aproximar:

```
D_q = 2
alpha = 2
f(alpha) = 2
```

para los `q` aceptados.

### 15.2 Limitaciones principales

1. **Pocas escalas:** la regresión multifractal requiere al menos 3 escalas globales; localmente se usan las hijas estrictamente menores que `mother_scale`.
2. **Madres vacías o casi vacías:** pueden producir `NaN`, R² bajos o `reliable = 0`.
3. **q negativos extremos:** amplifican celdas de probabilidad muy pequeña y requieren revisar el piso adaptativo aplicado.
4. **Local vs global:** `alpha(M,q)` describe la ventana madre, no necesariamente el sistema completo.
5. **zeta:** es un peso operativo definido por MUSA; sus exponentes deben validarse en cada aplicación geológica.
6. **d_local_index:** índice exploratorio, no dimensión física estricta.

---

## 16. Resumen operativo

```
Datos -> medida m_i por celda
      -> probabilidad P_i (global o local segun flujo)
      -> funcion de particion / entropia / N_boxes -> D_q
      -> pesos mu_i -> integrandos A_q, F_q
      -> regresion vs ln epsilon -> alpha, f(alpha)
      -> (local) peso zeta -> alpha_w, f_alpha_w
      -> robustez opcional -> bootstrap, Theil-Sen, jackknife, Cook
      -> export CSV + graficos
```

MUSA entrega simultáneamente:

- un espectro multifractal **global** filtrado por calidad;
- mapas **locales** por celda madre con estimadores canónicos, ponderados y robustos;
- descriptores de **intensidad** (`measure_sum_m`) separados de los descriptores de **complejidad** (`alpha`, `D_q`, `d0_local`, etc.);
- productos de diagnóstico para decidir qué estimaciones locales son defendibles.

Esa separación es intencional: densidad estructural, heterogeneidad multifractal y confiabilidad estadística no son la misma magnitud física.

## Nota de versión 2026-05-24

Las mejoras de robustez descritas previamente como pendientes ya están incorporadas al código:

- el reporte global puede incluir intervalos bootstrap opcionales para `Dq`, `alpha` y `f(alpha)`;
- los agregados por celda madre incluyen `reliable`, `reliable_min_zeta` y `reliable_min_r2`;
- los gráficos locales se generan para cada `q` aceptado;
- están disponibles Theil–Sen, jackknife, leverage, Cook, piso adaptativo para `q < 0` y sensibilidad de exponentes de `zeta`.

## Nota metodologica 2026-05-30

La ponderacion zeta fue ajustada para tratarse explicitamente como una mejora de confiabilidad multiescala, no como una dimension multifractal ni como un reemplazo del estimador Chhabra Jensen canonico.

La forma operativa actual combina cobertura espacial, masa relativa, posicion de escala y numero efectivo de cajas ocupadas. El numero efectivo se estima mediante entropia local y penaliza casos donde la medida esta concentrada en muy pocas celdas hijas. Ademas, el factor de escala usa un piso configurable para evitar que la escala hija mas gruesa quede con peso cero en la regresion ponderada.

La interpretacion recomendada es:

| Estimador | Rol |
| --- | --- |
| alpha y f alpha | Estimacion local canonica Chhabra Jensen |
| alpha_w y f_alpha_w | Estimacion local ponderada por confiabilidad zeta |
| zeta_mean y reliable | Diagnostico para filtrar mapas locales |
| alpha_ts y f_alpha_ts | Comparacion robusta frente a puntos de escala atipicos |

La corrida de evidencia ubicada en outputs/congreso_geologia_evidence acepto los nueve q probados entre -4 y 4, con rango Dq de 1.3029 a 1.5948. Para q=2 se obtuvieron 598 celdas madre con resultado local, fraccion reliable de 0.5268, mediana alpha_w de 1.1617 y mediana zeta_mean de 0.1603. Estos valores respaldan el uso de zeta como filtro y ponderacion de confiabilidad, siempre junto al estimador local canonico.

Se agrego un control cuadratico del espectro global para comparar la forma f alpha contra una curva parabolica simple. Este control no reemplaza Chhabra Jensen y no se usa para estimar alpha ni f alpha. Su funcion es diagnostica: si el ajuste no es concavo o el pico cae fuera del rango observado, MUSA deja vacios alpha_peak y f_peak y marca fit_valid igual a 0. En la corrida Broken Hill el ajuste tuvo R2 de 0.8554, pero fue convexo, por lo que no debe presentarse como una campana multifractal valida.
