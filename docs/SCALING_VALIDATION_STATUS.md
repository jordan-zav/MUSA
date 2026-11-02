# Alcance de la validación matemática de MUSA

Revisión de código del 1 de noviembre de 2026. Versión de desarrollo solicitada:
1.0.0. No constituye una revisión por pares ni una certificación matemática.

## Qué calcula y comprueba actualmente

MUSA analiza una medida de longitud de lineamientos en un dominio espacial 2D.
Calcula dimensiones generalizadas Dq y el espectro directo de Chhabra–Jensen,
alpha y f(alpha), a varias escalas. Cambiar q estudia el peso relativo de regiones
densas y poco densas; no agrega dimensiones espaciales ni variables independientes.

Las ventanas móviles separan tamaño de ventana, paso entre centros y escalas
internas. Hay controles de cobertura, número de cajas, dominancia de pesos,
conservación de longitud y ajustes de Dq, alpha y f(alpha). Los ajustes constantes
no se consideran evidencia de escalamiento. Se conservan rechazos y sus motivos.
El conjunto opcional de 16 orígenes y una segunda fase permite examinar sesgo de
malla. Las ventanas solapadas y los orígenes son dependientes, no réplicas
estadísticas independientes. Zeta y su regresión ponderada son diagnósticos
operativos separados de las estimaciones canónicas.

El análisis global añade diagnósticos por escala, jackknife y bootstrap opcional.
La disponibilidad de un intervalo no garantiza que su cobertura esté calibrada
para una red espacial dependiente; el p de una pendiente tampoco es una prueba
de fractalidad o multifractalidad.

## Controles computacionales que sí ejecutan el motor

- tests/test_origin_ensemble.py contrasta particiones con una referencia
  independiente y conserva longitud tras trasladar geometrías.
- La línea uniforme se contrasta con Dq aproximadamente 1 y pequeña anchura
  espectral, sin forzar el espectro a cumplir ese resultado.
- La construcción binomial de Cantor se contrasta con valores analíticos de Dq
  y alpha en el intervalo finito estudiado y bajo dos fases de malla.
- tests/test_numerical_bias.py comprueba bordes, fragmentación de trazas,
  orientación, conservación de longitud y sensibilidad de clasificaciones.

Son controles útiles de implementación en casos concretos; no demuestran que
cualquier cartografía real presente escalamiento fractal. Las trazas finitas de
esos controles tampoco equivalen a un fractal matemático en el límite infinito.

La API histórica run_synthetic_validation, en src/musa/synthetic.py, genera
perfiles prefijados y una tabla ilustrativa. No crea geometrías ni llama al motor.
Sus campos pass/fail y el test de esa tabla no validan el cálculo multifractal.
Se ha aclarado expresamente su alcance en la documentación de la función.

## Lo que falta para una prueba de soporte de escalamiento

Ahora existe un diagnóstico experimental integrado, descrito en
[SCALING_SUPPORT.md](SCALING_SUPPORT.md). Evalúa dimensiones generalizadas de
Rényi Dq; no es una prueba universal calibrada de fractalidad o multifractalidad.
Un R2 elevado,
varios q aceptados o un espectro ancho no bastan. Un conjunto finito de segmentos
rectos tiene dimensión geométrica 1 a escalas suficientemente pequeñas; las
dimensiones mayores estimadas en una cartografía describen su organización en
un intervalo de escalas, no un límite fractal demostrado.

El diagnóstico implementado incorpora:

1. Declarar el intervalo resoluble a partir de precisión cartográfica, tamaño del
   dominio y soporte observado, y registrar su amplitud en órdenes de magnitud.
2. Comparar una recta log–log con curvatura y cambios de pendiente, usando un
   criterio definido antes de seleccionar el intervalo y controles de selección.
3. Evaluar estabilidad al retirar escalas, cambiar orígenes, tamaños de ventana
   y resolución de observación, sin tratar ventanas solapadas como independientes.
4. Contrastar D0−D2 con un modelo nulo condicional que traslada trazas conservando
   formas, longitudes y orientaciones. Holm corrige la familia completa de soportes;
   los q no generan pruebas independientes adicionales. Cambia la densidad local
   y los cruces, por lo que el contraste es de heterogeneidad espacial bajo ese
   modelo, no una demostración de multifractalidad.
5. Reportar por separado evidencia compatible, evidencia contraria e información
   insuficiente, con el intervalo y la sensibilidad; no una etiqueta universal.

Los estados se basan en umbrales operativos explícitos. El piloto con 24 conjuntos
generados bajo el modelo nulo y 39 réplicas por conjunto produjo 1 rechazo a 0,05;
el intervalo binomial del 95 % fue aproximadamente 0,0011–0,2112. No certifica una
tasa de error general del 5 %. Faltan calibración extensa, potencia ante alternativas
y validación independiente para distintos dominios, inventarios y diseños de
muestreo. El usuario debe justificar la resolución cartográfica, el intervalo y
la adecuación del modelo nulo. No se ha implementado multifractal conjunto de
varias variables. Las dimensiones de Rényi sí están implementadas; no se
confunden con dimensiones espaciales adicionales.

## Referencias

- [Chhabra y Jensen (1989), espectro directo](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.62.1327).
- [Roy y colaboradores (2007), box counting de redes de fracturas y rango de escalamiento](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2006JB004582).
- [Gonzato y colaboradores (1998), problemas prácticos de estimar dimensión y rango de invariancia](https://academic.oup.com/gji/article/132/2/275/671597).
