# Ventanas moviles multiescala (experimental)

El backend tambien genera la capa `trap_candidates` con componentes,
puntaje exploratorio, calidad separada y simbologia. Ver
[formula y angulos de interseccion](candidate_scoring.md).

En Opciones de salida, activar **Ventanas moviles (experimental)**. Introducir
los lados de ventana en metros, el paso entre centros y al menos cuatro
divisores internos enteros. El modo anterior sigue disponible y se ejecuta
tambien para facilitar comparaciones. Los q son los elegidos en la interfaz;
no se eliminan ventanas porque ese q falle en el analisis global.

Los valores iniciales 2000,4000,8000 m, paso 1000 m y divisores 2,4,8,16 son
ejemplos editables, no escalas geologicas recomendadas universalmente. Cada
ventana L utiliza cajas de lado L/divisor: verificar que la escala mas fina
sea compatible con la resolucion cartografica. Reducir el paso no agrega
detalle a los datos. No combinar capas que repiten las mismas fallas sin
armonizar primero su procedencia y geometria.

## Metodo y controles

- Ventanas cuadradas solapadas recortadas al dominio real, con probabilidades
  renormalizadas dentro de cada ventana y espectro Chhabra-Jensen no ponderado.
- Longitud de trazas unicas: los segmentos exactamente coincidentes se
  disuelven. No se deduplican trazas cercanas que difieran geometricamente.
- CRS proyectado en metros obligatorio. No se amplian los datos observados
  fuera del limite. Cobertura minima por defecto: 80% del cuadrado.
- Al menos cuatro escalas internas y dos cajas ocupadas en cada escala.
- Se reportan Dq, alpha, f_alpha y sus R2. R2 minimo por defecto: 0.9.
- Pesos calculados en dominio logaritmico. min_effective_boxes es el minimo
  entre escalas de 1/sum(mu^2); por defecto se requieren al menos dos cajas
  efectivas. max_box_weight revela concentracion excesiva del peso.
- Se conservan estimaciones rechazadas con accepted=false y reason:
  low_coverage, insufficient_support, dominant_box o poor_scaling.
  Un ajuste constante no se considera evidencia de escalamiento.
- accepted_window_sizes cuenta tamanos con estimacion aceptada para cada
  centro/q; NO mide persistencia de una anomalia ni probabilidad de exito.
- Los nodos se calculan sobre toda la red recortada al dominio: I=extremo,
  Y=grado 3, X=grado 4, complex=grado superior. Grado 2 no se exporta.
  El conteo local incluye cruces estrictamente dentro de la ventana y excluye
  nodos del borde del dominio. No crea cruces nuevos al recortar ventanas.
- No hay snapping automatico. Un cruce planar no prueba conexion en 3D.
- Limite por defecto de 10000 ventanas; ampliar el paso si se supera.

El perfil experimental actual conserva estimaciones canónicas y ponderadas por
zeta, con sus diagnósticos separados. Consulte candidate_scoring.md para los
factores, parámetros y criterios de soporte. Zeta no se interpreta como una
propiedad física ni como probabilidad de validez geológica. No se produce un
índice de permeabilidad ni una incertidumbre hidráulica. Las ventanas vecinas
son dependientes y no deben repartirse al azar entre entrenamiento y prueba.

## Salidas

- moving_windows.csv: resultados por centro, tamano y q, cobertura y cruces.
- moving_nodes.csv: coordenadas y grados de nodos unicos.
- moving_windows_config.json: parametros, centros, CRS y limitaciones.
- musa_moving_windows.gpkg, al activar GIS: poligonos window_spectra,
  structural_candidates (cruces interiores) y topology_controls (extremos y
  cortes del limite). Los resultados entran en el ZIP de la corrida.

El GeoPackage incluye estilos predeterminados de QGIS en layer_styles:
Y triangulo naranja, X rombo azul, complejo estrella violeta. Los controles
son cruces grises pequenos. Las ventanas no tienen relleno; por defecto se
dibujan contornos para q=2 segun calidad. Para otros q, cambiar el filtro de
reglas. Filtrar tambien window_m evita superponer tamanos. La visibilidad de
capas se guarda en un proyecto QGIS, no en el GeoPackage.

Los candidatos incluyen max_branch_angle_deg (mayor separacion axial entre
tangentes de ramas, 0-90 grados; NO identifica familias tectonicas), y contexto
de las ventanas que contienen el punto: context_windows_q2,
accepted_context_q2, accepted_sizes_q2 y context_status_q2. No son un espectro
centrado en el nodo, una puntuacion prospectiva ni persistencia geologica.
Si q=2 no fue evaluado, el estado es not_evaluated. No se descarta un cruce
geologico porque no haya ventanas aceptadas alrededor. El atributo
interpretation recuerda que la geometria planar no esta validada para prospeccion.

## Python: centros regulares o nodos seleccionados

### Interacciones potenciales por radio

En la GUI, activar Ventanas moviles y **Interacciones potenciales por radio**.
Los radios 100,250,500 m son ejemplos exploratorios editables, no tolerancias
cartograficas verificadas ni distancias hidraulicas. Al ejecutar, el backend
genera potential_relations.csv y, con GIS activado, dos capas adicionales con
estilos QGIS incorporados: potential_relations (conectores discontinuos por
tipo) e interaction_search_zones (contornos punteados sin relleno).

Se examinan pares de partes lineales disjuntas dentro del radio mayor. Se
guarda una relacion mas cercana por par, con distancia, separacion axial de
tangentes locales, tipo extremo-extremo/extremo-traza/traza-traza y primer
radio ensayado que la detecta. Las geometrias no se modifican. Se excluyen
pares con interseccion exacta, puntos de contacto en el borde y conectores
que atraviesan zonas fuera del AOI. part_a/part_b son indices de partes de la
entrada preparada, no identificadores geologicos de fallas independientes.
Segmentacion y cartografia pueden influir; revisar antes de interpretar.

matching_radii_m indica inclusion por distancia: no es persistencia independiente
ni puntuacion. Las zonas son buffers del punto medio con el primer radio
compatible, recortados al AOI; solo representan busqueda, no zonas de dano.
No se infiere conectividad 3D, permeabilidad ni familias tectonicas del angulo.
No se unen componentes ni se inventan conexiones por proximidad. Para evitar
salidas desmesuradas se limita a 100000 relaciones, con error explicito.

En Python, pasar proximity_radii_m=[100,250,500] a export_moving_windows.

```python
from musa import MUSA, export_moving_windows

musa = MUSA('fallas.gpkg', boundary='limite.gpkg', q_values=[0, 1, 2, 4, 8])
outputs = export_moving_windows(
    musa, 'outputs/ventanas', window_sizes_m=[2000, 4000, 8000], step_m=1000,
    divisors=[2, 4, 8, 16],
)
# Para evaluar entornos de nodos concretos, pasar centers=[(x1,y1), (x2,y2)].
# Las coordenadas deben estar en el CRS metrico activo del analizador.
```

La validacion automatica cubre dimension conocida de una linea, eliminacion
de duplicados exactos, redes con igual densidad y distinta conectividad,
invariancia por traslacion/segmentacion, bordes, q extremos y exportacion GIS.
Falta validar con las capas reales del proyecto y evidencia independiente
antes de interpretar nodos como favorables para flujo.
