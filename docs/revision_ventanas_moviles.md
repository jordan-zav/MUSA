# Revision de logica espacial y propuesta multiescala

Revision inicial: 2026-09-24. Los hallazgos siguientes describen el estado
anterior al desarrollo. Ya se implemento un modo experimental documentado en
[moving_windows.md](moving_windows.md): ventanas solapadas, cruces unicos,
diagnosticos de dominancia y exportacion GIS. Tambien se corrigieron el area
observada de densidad y los pesos numericos de q. El grafo historico se mantiene
para compatibilidad. Snapping, validacion hidraulica, incertidumbre espacial y
persistencia de anomalias siguen pendientes; no se consideran implementados.

## Implementacion actual

- core.py/export_cell_outputs recalcula probabilidades locales por celda madre;
  los centroides representan el soporte, no son observaciones puntuales.
- El lado madre se fija a max(resolutions_m); las escalas inferiores alimentan
  la regresion. No hay parametros independientes de ventana y paso.
- Las hijas se asignan a madres por centroide. Para escalas no anidadas una
  hija puede cruzar una frontera madre: su masa no queda recortada a esa madre.
- geomatics.py exporta poligonos y centroides; interpolar estos centroides no
  equivale a recalcular el estimador en ventanas solapadas.
- network.py implementa un grafo de lineas: node_count cuenta lineas y
  edge_count pares intersectados. No representa nodos geograficos I/Y/X.
- structural.py divide la longitud por el area completa del cuadrado incluso
  cuando solo una fraccion pertenece al dominio observado.
- _mu_for_q usa potencias directas; ampliar q requiere estabilidad numerica
  y diagnosticos de dominancia, no solo ampliar el selector de la interfaz.
- El bootstrap local remuestrea puntos de regresion entre escalas, no bloques
  espaciales ni realizaciones de la cartografia. No mide toda su incertidumbre.

## Comprobaciones reproducidas

Tres lineas que comparten un solo cruce producen edge_count=3 e
intersection_density_per_km2=3 en un dominio de 1 km2. Es correcto como numero
de pares, pero no como numero de intersecciones geograficas distintas.

Una celda de 1 km de lado, observada solo en 0.5 km2 y con 500 m de linea,
reporta 500 m/km2. La densidad sobre area observada seria 1000 m/km2.
Debe conservarse tambien la fraccion de cobertura para comparar resultados.

## Diseno propuesto

1. Separar escala cartografica de origen, tamano de ventana L, paso h y
   resoluciones internas epsilon. Registrar procedencia y no sumar varias
   representaciones de la misma falla como si fueran estructuras distintas.
2. Evaluar ventanas solapadas en centros regulares y, opcionalmente, centradas
   en intersecciones reales. Recortar lineas al soporte ventana-interseccion-AOI
   y recalcular masa, probabilidades y regresiones dentro de cada soporte.
3. Mantener un conjunto suficiente de escalas internas y rango de escalamiento;
   rechazar ventanas sin soporte. Un paso pequeno no aumenta la resolucion
   geologica ni hace independientes los resultados vecinos.
4. Comparar varios L sin promediarlos ciegamente: exportar persistencia de las
   anomalias, sensibilidad al origen de grilla, cobertura e incertidumbre.
5. Construir una red de cruces y extremos unicos, segmentos entre nodos,
   tolerancia geometrica documentada y banderas de nodos artificiales del borde.
   Separar conectividad regional de conectividad truncada por cada ventana.
6. Exportar descriptores independientes de longitud, orientacion, topologia y
   multifractalidad antes de proponer un indice compuesto de favorabilidad.
7. Para q positivo, registrar pesos mu, max(mu) y N_eff=1/sum(mu**2) por escala;
   usar log-sum-exp para calculos extremos. Si domina una sola caja, marcar
   estimacion poco informativa aunque su R2 sea alto.
8. Validar con redes sinteticas de igual longitud/densidad y distinta
   conectividad, cambios de segmentacion, desplazamientos de grilla y bordes.
   Para validacion externa usar bloques espaciales, no ventanas solapadas
   repartidas aleatoriamente entre entrenamiento y prueba.

## Interpretacion

q positivo alto enfatiza cajas con gran proporcion de la medida (actualmente
longitud de lineas). No determina apertura, sellado ni permeabilidad. Los
resultados deben describirse como concentracion o conectividad estructural
candidata hasta contrastarlos con evidencia hidraulica/geologica independiente.

La seleccion de L, h, epsilon y q depende de escala y calidad de las capas.
Los valores son descriptores multifractales y la entrada es una capa lineal.
No se mezclan automaticamente capas cartograficas de distintas escalas.

## Referencias primarias

- Chhabra y Jensen (1989): https://doi.org/10.1103/PhysRevLett.62.1327
- Sanderson y Nixon (2015): https://eprints.soton.ac.uk/375431/
- Caine, Evans y Forster (1996): https://digitalcommons.usu.edu/geology_facpub/35/
