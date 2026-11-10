# Interpretación de q negativos

Evaluación local del 7 de noviembre de 2026. No modifica el motor ni los
valores por defecto. Evidencia completa: sesión MUSA-negq-20261107_204932, archivada por el mantenedor
(informe.md, resultados.json, protocolo.json con el hash del script, curvas y
diagnósticos por escala).

## Resumen

Con la partición cuadrada de MUSA, las dimensiones Dq con q < 0 no recuperan
la verdad conocida de una medida multifractal, aunque D0 a D4 sí se recuperan
con errores pequeños. Ningún remedio ensayado lo corrige sin cambiar la medida.
Por eso, **D(q<0) no debe interpretarse como dimensión de la medida original de
longitudes sin evidencia independiente de un régimen resuelto y estable**.

## Diseño

- Cuatro casos con verdad conocida: cascada diádica de 65.536 segmentos (Dq
  analítico), la misma cascada con segmentos orientados al azar, Koch de nivel
  7 (D = log 4/log 3) y una red de Voronoi (D = 1 a escalas menores que el
  espaciado). Generadores en [scripts/grid_geometry](../scripts/grid_geometry).
- 48 configuraciones de rotación y origen de malla, idénticas para todos los
  remedios. Partición real musa.mass_partition y q = −4, −2, −1, 0, 1, 2, 4.
- Remedios fijados antes de calcular errores:
  - piso de probabilidad (negative_q_floor_fraction) con seis valores;
  - umbral de longitud por celda de 0,01, 0,05 y 0,1 eps;
  - tres recortes del rango de escalas;
  - promedio de 4 y 9 orígenes;
  - Chhabra–Jensen sobre un rango restringido, como control.
  Ningún parámetro se eligió mirando la verdad.
- Criterio descriptivo de recuperación: 48 de 48 estimaciones finitas,
  RMSE ≤ 0,10, |sesgo| ≤ 0,05 y desviación estándar ≤ 0,10. Es una tolerancia
  de este ensayo, no un umbral de MUSA.

## Resultados

| Caso | RMSE base de D(−4), D(−2), D(−1) | Remedios que cumplen el criterio con q < 0 |
| --- | --- | --- |
| Cascada diádica | 1,33 / 1,12 / 0,79 | Ninguno |
| Cascada isótropa | 1,33 / 1,12 / 0,79 | Ninguno |
| Koch | 0,67 / 0,36 / 0,08 | Pisos de 0,01 en adelante en los tres q; la base solo en q = −1 |
| Voronoi | 0,73 / 0,46 / 0,12 | Umbrales relativos en q = −4 y −2; ninguno en q = −1 |

- En todos los casos, el 1 % de celdas con menor masa aporta entre el 99,8 % y
  el 100 % de la suma con q = −4. Los momentos negativos dependen casi por
  completo de las celdas casi vacías.
- En Voronoi, un umbral que retira solo el 0,003 % de la longitud recupera
  D(−4). Allí la cola de masas pequeñas es un artefacto de corte de la malla.
- En las cascadas, esos mismos umbrales retiran entre el 53 % y el 94 % de la
  masa, porque en una medida multifractal la masa rara es señal. Ningún
  procedimiento automático distingue ambos casos.
- Promediar orígenes reduce la variabilidad, pero no corrige el sesgo: en la
  cascada, D(−4) pasa de un RMSE de 1,33 a 1,39 con nueve orígenes.
- Las formas de celda cuadrada y hexagonal fallan por igual
  ([GRID_GEOMETRY.md](GRID_GEOMETRY.md)).

## El piso de probabilidad iguala los q negativos a D0

El piso definido en [teoría](theory.md), sección 8, impone para q < 0 una
probabilidad mínima c/N, donde c = min(0,5; η·max(|q|,1)) y N es el número de
cajas ocupadas. Tras renormalizar, p′ ≥ c/[N(1+c)]. Por convexidad y por esa
cota:

ln N ≤ Hq(p′) ≤ ln N + [q/(1−q)]·ln[c/(1+c)]

La diferencia Hq − ln N queda acotada por una constante que no depende de eps.
Por lo tanto, si existe un régimen de escalamiento, la pendiente regularizada
tiende a D0 para cualquier η > 0 y cualquier q < 0. En un rango finito las
pendientes pueden diferir, pero el piso no puede conservar un espectro
negativo distinto de D0. Su éxito numérico en Koch, que es monofractal y donde
todos los Dq valen D0, no es evidencia de recuperación en una medida
multifractal. Esta derivación es propia de la evaluación y se comprobó por
separado durante la revisión.

## Recomendaciones

1. Reportar Dq con q < 0 solo como descriptor de sensibilidad, no como
   dimensión de la medida original.
2. Mantener el piso y el umbral como opciones documentadas que cambian la
   medida, desactivadas por defecto. Si se usan, reportar la ruta sin ellos.
3. Diagnóstico propuesto, no implementado: medir cuánto cambia D(q<0) al
   retirar fracciones ínfimas de longitud. Un cambio grande ante una pérdida
   mínima indica que ese q negativo no es interpretable en ese mapa.

## Límites

Una realización de cada generador; malla cuadrada sin máscara de estudio; sin
ruido, censura ni trazado digitalizado; intervalos bootstrap condicionales a
estas realizaciones; regresión OLS de entropías fuera de la interfaz. Nada de
esto valida un parámetro para datos geológicos.

## Fuentes consultadas

- [Chhabra y Jensen (1989)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1327), espectro directo.
- [De Bartolo, Gaudio y Gabriele (2004)](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2003WR002760): sesgo de cajas casi vacías en q negativos y método sandbox.
- [Thiem y Schreiber (2012)](https://arxiv.org/abs/1204.3755): esquemas de partición y promedio de orígenes.
