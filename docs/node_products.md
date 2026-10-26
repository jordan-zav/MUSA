# Nodos y Pathway: contrato de uso

`node_classes` es el producto descriptivo de nodos. `node_class` distingue
1-1, 1-2, 1-3, 2-2, 2-3 y 3-3 por órdenes interpretados participantes.
`node_kind` separa intersección en planta de proximidad sin cruce.
Varias parejas se conservan como `multiple_pairs`; órdenes compartidos como
`ambiguous_classification`. No se escoge automáticamente la pareja más favorable.
`participant_faults_json` permite recuperar las fallas y sus registros originales.

`node_weight` se obtiene de `node_weights.json`: w(n) = w[clase(n)].
El valor inicial es 1 para cada pareja: referencia neutral, no calibración.
Clases ambiguas, múltiples o desconocidas tienen peso nulo, no cero.
Cruces y proximidades deben filtrarse por separado al usar esos pesos.
La hipótesis prioritaria 1-2 puede recibir otro peso explícito en ese archivo;
la prioridad por sí sola no determina un valor numérico defendible.
No se multiplica por ángulo, ζ ni puntaje multifractal.

structural_trap_class es un campo reservado, sin evaluar. Cualquier regla
geológica adicional requiere contexto y validación independientes, aportados
explícitamente por el usuario. La clase 1-2 por sí sola no demuestra dilatación
ni permeabilidad. No se incluye una regla geológica específica de un proyecto.

`pathway_multifractal` conserva el contraste continuo por ventana:

- pᵢ(r) = longitudᵢ(r) / longitud total de la ventana.
- μᵢ(q,r) = pᵢ(r)^q / Σⱼpⱼ(r)^q, sobre cajas ocupadas.
- α(q) = pendiente de promedio_orígenes[Σᵢ μᵢ ln(pᵢ)] frente a ln(r/L).
- H = α(0) − α(2), campo `multifractal_contrast`.

Se mantienen las ventanas 20, 40 y 80 km separadas mediante `window_m`.
No sumarlas como si fueran observaciones independientes. El campo
`contrast_usable` y `support_reason` acompañan H; valores negativos permanecen
como diagnóstico, no como evidencia desfavorable ni cero. La cobertura es provisional.
Este es un producto por ventanas, no un raster RF validado a 500 m.
ζ pondera confiabilidad numérica del ajuste en los diagnósticos ponderados;
no pondera favorabilidad geológica ni sustituye la sensibilidad de origen.

`trap_candidates` conserva resultados históricos por compatibilidad. Su
`score` es rango relativo: S = 100 × mediana(percentiles frente al fondo comparable).
`evidence_class` y `relative_class` no son clases geológicas de nodos.
La intensidad KDE experimental usa esos puntajes por distancia y sigue siendo
otra variable Pathway, sin multiplicarla por el peso geológico del nodo.

Tabla actualizada para el modelo:

| Producto | Uso | Estado |
|---|---|---|
| node_class + node_kind | Categorías estructurales y pesos explícitos | Descriptivo |
| structural_trap_class | Campo reservado para reglas externas validadas | Sin evaluar |
| pathway_multifractal | H continuo por ventana con soporte | Experimental |
| candidate_contrast_intensity | KDE de rango relativo | Experimental; requiere cobertura y validación espacial |

Para actualizar clases/pesos sin repetir el cálculo multifractal, usar
export_products de musa.node_classes sobre un GeoPackage propio compatible,
con una política de pesos explícita. La función modifica el archivo indicado:
trabajar sobre una copia de salida, no sobre una entrega cerrada.
Los lanzadores, datos y reglas específicos de proyectos se mantienen fuera
de la distribución general del software.

Un R² alto de una parábola sobre f(α) no sustituye la evaluación de las pendientes
a través de tamaños de caja. Un q alto enfatiza masa concentrada, no demuestra
prospectividad. Ver `candidate_scoring.md` para la matemática completa y sus límites.
