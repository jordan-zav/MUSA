# Geometría de la celda: cuadrados, hexágonos y rotación de la malla

Experimento local del 7 de noviembre de 2026. Es un estudio exploratorio de
sensibilidad y no cambia el motor: MUSA sigue usando celdas cuadradas. La
partición hexagonal es un prototipo en [scripts/grid_geometry](../scripts/grid_geometry)
y no forma parte del plugin ni de la API.

## Pregunta

¿Recuperan las celdas hexagonales las dimensiones de Rényi Dq de una medida de
longitud mejor que las cuadradas? ¿Rinden mejor en redes con organización
hexagonal (uniones a 120°, grietas de desecación, disyunción columnar)? Que un
patrón natural tenga forma hexagonal no implica que una malla hexagonal mida
mejor; esa segunda afirmación es la que se pone a prueba aquí.

## Diseño

- Prototipo de partición hexagonal (hexágonos con un vértice arriba). Cada arista
  hexagonal está sobre una recta n·p = m·a/2, con normales a 0°, 60° y 120°.
  Cada segmento se corta en todas esas rectas y cada pieza se asigna al centro
  más cercano a su punto medio. La partición es exacta y conserva la longitud
  con tolerancia relativa de 1e-9 en todas las escalas. Se comprobó que la
  asignación al centro más cercano coincide con la búsqueda exhaustiva en
  20.000 puntos.
- Mallas comparadas con celdas de igual área (lado equivalente eps), las mismas
  escalas, el mismo estimador de entropía de Rényi y la misma recta contra
  log(1/eps). Para la malla cuadrada se usa la partición real de MUSA
  (musa.mass_partition).
- Cada configuración usa una rotación aleatoria del mapa y un origen de malla
  aleatorio, y ambas mallas ven exactamente la misma geometría.
- Casos con verdad conocida: la cascada diádica de 65.536 segmentos (Dq
  analítico, construida sobre una malla cuadrada), la curva de Koch de nivel 7
  (D = log 4/log 3, ángulos de 60°), la misma cascada con segmentos orientados
  al azar, y redes poligonales de panal con perturbación y de Voronoi (D = 1 a
  escalas menores que el espaciado).
- Mapas públicos sin verdad conocida: dos de Åland, tres de Loviisa, FracPaQ
  map1, HatchFrac y Hornelen fig. 7, con las escalas declaradas en los
  manifiestos del 2 de noviembre. Se mide la desviación estándar de Dq entre
  48 configuraciones.
- q = −4, −2, −1, 0, 1, 2, 4. Valor p pareado por permutación de signos sobre
  la diferencia de error absoluto.

## Resultados

Ejecución verificada: D:/DevResources/Sessions/MUSA-hex-extended-20261107_195052
(64 configuraciones por caso y promedio de cuatro orígenes).

| Caso | Cambio del RMSE del hexágono frente al cuadrado, q >= 0 | Observación |
| --- | --- | --- |
| Cascada diádica | −4 % a −11 % | p < 0,05 en la mayoría de los q |
| Cascada isótropa | −3 % a −9 % | p < 0,05 en D0 y D1 |
| Koch | −5 % a −8 % | Casi nunca significativo |
| Panal | −1 % a −6 % en D0–D2; +1 % con q = 4 | Consistente (89 % a 95 % de las configuraciones), pero pequeño |
| Voronoi | −1 % a −8 % en D0–D2; +1,5 % con q = 4 | Consistente, pero pequeño |

En los mapas públicos, la desviación estándar de D1 con hexágonos bajó al 49 %
a 65 % de la obtenida con cuadrados en los 8 mapas. D0 bajó en 7 de 8 y D2 en
8 de 8. Con q negativos el resultado fue mixto: mejoró en 4 mapas y empeoró
hasta 1,33 veces en otros 4. En valor absoluto, la desviación estándar de D1 ya
era pequeña (del orden de 0,005).

Los errores grandes no dependen de la forma de la celda. En D(−4), el RMSE
llegó a 1,3 en la cascada y a 0,6 en Koch, Voronoi y panal con ambas mallas.
En D0 de las cascadas, ambas mallas tienen un sesgo de unos −0,12, y en las
redes poligonales un sesgo de +0,06 frente a D = 1.

## Rotación de la malla cuadrada

Ejecución verificada: D:/DevResources/Sessions/MUSA-rotation-vs-hex-20261107_204652.
Todos los estimadores tienen el mismo costo: cuatro particiones cuyas curvas
de entropía se promedian antes de ajustar una sola pendiente.

- cuadrado con 4 orígenes: desplazamientos de medio paso, como hace MUSA;
- cuadrado con 4 rotaciones: 0°, 22,5°, 45° y 67,5°, con un origen aleatorio en cada una;
- hexágono con 4 orígenes;
- hexágono con 4 rotaciones: 0°, 15°, 30° y 45°.

Se usaron 48 configuraciones por caso con verdad conocida y 32 por mapa público.

| Estimador | RMSE de D0 (cascada / isótropa / Voronoi) | Desviación estándar en mapas, mediana respecto del cuadrado con 4 orígenes (D0 / D1 / D2) |
| --- | --- | --- |
| Cuadrado, 1 partición | 0,123 / 0,123 / 0,064 | 1,27 / 2,45 / 3,75 |
| Cuadrado, 4 orígenes | 0,123 / 0,123 / 0,064 | 1 / 1 / 1 |
| Cuadrado, 4 rotaciones | 0,120 / 0,120 / 0,064 | 0,37 / 0,92 / 1,83 |
| Hexágono, 4 orígenes | 0,114 / 0,114 / 0,059 | 0,32 / 0,30 / 0,35 |
| Hexágono, 4 rotaciones | 0,114 / 0,114 / 0,059 | 0,36 / 0,47 / 1,35 |

- La rotación del cuadrado iguala al hexágono en estabilidad de D0, pero no en
  exactitud de D0 (p < 0,02 en los cuatro casos) ni en D1 o D2. Con q = 2 y
  q = 4, las rotaciones con origen aleatorio son incluso menos estables que los
  cuatro orígenes estructurados.
- El hexágono con cuatro orígenes fue el estimador más estable en los mapas
  públicos para q >= 0. En valor absoluto, la desviación estándar de D1 bajó de
  unos 0,0025 a unos 0,0008.
- En exactitud frente a la verdad, la ventaja del hexágono sigue siendo de pocos
  puntos porcentuales. En Koch, el cuadrado con rotaciones fue mejor en D(−1).
- Limitación del diseño: las rotaciones se combinaron con orígenes aleatorios,
  no con los desplazamientos estructurados. Parte de su peor estabilidad en
  q >= 2 puede deberse a esa combinación y no a la rotación en sí.

## Interpretación

- La forma de la celda es una fuente de incertidumbre de segundo orden. El rango
  de escalas y los q negativos pesan mucho más.
- La ventaja del hexágono no es mayor en las redes hexagonales que en la
  cascada isótropa. Es más coherente atribuirla a que el hexágono se parece más
  a un círculo que a una correspondencia con la forma del patrón natural.
- Los hexágonos no se anidan: un hexágono no se divide exactamente en
  hexágonos más pequeños. El análisis local de MUSA, con celdas madre y
  resoluciones hijas, necesita esa anidación, así que una malla hexagonal solo
  sería aplicable al análisis global y al diagnóstico de soporte.
- La rotación de la malla cuadrada no sustituye al hexágono en D1 y D2. Si se
  quisiera aprovechar la ganancia, la opción candidata sería un hexágono
  experimental solo para el análisis global, sin cambiar los valores por defecto.
  Dado su tamaño absoluto, la ganancia tiene menos prioridad que los q negativos
  y la calibración del modelo nulo.

## Límites

Un solo intervalo de escalas por caso; tamaño definido por igual área; sin
tratamiento del borde ni de la cobertura parcial; los mapas públicos solo
permiten medir estabilidad, no exactitud; el prototipo no está cubierto por la
suite de tests del repositorio. Nada de esto establece validez geológica.

## Reproducción

Ejecutar mediante DEVRESOURCES_RUN.cmd y elegir una carpeta nueva:

~~~text
python scripts/grid_geometry/run_hex_vs_square.py D:/DevResources/Sessions/NUEVA_SESION
python scripts/grid_geometry/run_extended.py D:/DevResources/Sessions/NUEVA_SESION
python scripts/grid_geometry/run_rotation.py D:/DevResources/Sessions/NUEVA_SESION
~~~

Los dos últimos necesitan las entradas preparadas de la suite ampliada. Su ruta
se indica con la variable MUSA_BENCH_DATASETS (carpeta datasets de una
preparación con scripts/extended_benchmark_inputs.py). Requieren numba.
