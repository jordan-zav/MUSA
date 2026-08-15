# Manual de uso de MUSA

Versión 1.0.1

MUSA, Multifractal Spectrum Analyzer, ejecuta análisis multifractales globales y locales sobre lineamientos espaciales, evalúa la confiabilidad de los resultados y genera productos tabulares, gráficos y GIS.

## 1. Inicio rápido

1. Abra MUSA.exe.
2. Seleccione Español en Idioma si desea usar la interfaz en español.
3. En Lineamientos, seleccione la capa vectorial que contiene las líneas.
4. En Límite, seleccione el polígono del área de análisis.
5. En Directorio de salida, elija una carpeta nueva o vacía para la corrida.
6. Mantenga el modo Explorer para una ejecución estándar y defendible.
7. Pulse Sugerir escalas si desea que MUSA proponga la unidad, celda madre y divisores.
8. Revise el resumen de la corrida y pulse Ejecutar MUSA.
9. Espere el mensaje de finalización antes de cerrar la aplicación.

Los valores de ejemplo que aparecen al abrir la interfaz son rutas de desarrollo. En el ejecutable distribuido deben reemplazarse mediante los botones Examinar.

## 2. Datos de entrada

### Lineamientos

Capa vectorial de líneas en formato Shapefile, GeoPackage o GeoJSON. Debe contener la geometría que será medida en las distintas escalas.

### Límite

Capa poligonal que define el área de trabajo. Se recomienda emplear un sistema de coordenadas proyectado en metros. Si la capa está en coordenadas geográficas, MUSA intenta estimar una proyección UTM adecuada.

### Directorio de salida

Carpeta donde se escribirán las tablas, gráficos, GeoPackage y paquete ZIP. Para evitar mezclar corridas, use una carpeta diferente para cada análisis importante.

## 3. Modos de trabajo

### Explorer

Es el modo recomendado para una corrida estándar. Activa la agregación por celda madre, la exportación GIS, el paquete ZIP y el preset baseline. Los controles avanzados quedan ocultos.

### Geomatics

Muestra los controles de robustez, bootstrap, confiabilidad local y ponderación zeta. Debe usarse cuando se requiera evaluar sensibilidad o modificar explícitamente los criterios del análisis.

## 4. Diseño de escalas

### Unidad de celda

Representa la unidad espacial base sugerida para organizar la grilla. Sirve como referencia de diseño y compatibilidad espacial.

### Celda madre

Tamaño, en metros, de la unidad usada para los resultados locales. Debe ser suficientemente grande para contener información representativa.

### Divisores

Lista separada por comas. Las resoluciones analizadas se obtienen dividiendo el tamaño de la celda madre entre cada divisor e incluyendo también la escala de la propia celda madre.

Ejemplo: una celda madre de 4000 m con divisores 2, 4, 8 y 16 produce resoluciones de 4000, 2000, 1000, 500 y 250 m.

### Ventana q

q-min y q-max definen el intervalo de órdenes multifractales. q-step define el incremento. El valor estándar de menos 4 a 4 con paso 1 genera nueve órdenes q.

Los valores q negativos resaltan zonas de baja densidad y son más sensibles a celdas vacías o poco representadas. Los valores positivos resaltan concentraciones mayores.

### Umbral de longitud de celda

Longitud mínima considerada durante la medición de lineamientos. Debe expresarse en metros y ser coherente con la escala de los datos.

## 5. Botón Sugerir escalas

Sugerir escalas lee la extensión del límite y busca una combinación exacta de unidad, celda madre y divisores que evite recortes innecesarios.

Si está activa la opción Expandir automáticamente el límite, MUSA puede ampliar el marco hasta el siguiente múltiplo exacto de la celda madre objetivo. La geometría fuente no se modifica.

La lectura de una capa geográfica grande puede tardar algunos segundos y la ventana puede responder con lentitud durante ese cálculo. Espere a que aparezcan las resoluciones sugeridas en el registro de ejecución.

Si no existe una combinación exacta, revise el CRS, el tamaño del límite o la celda madre objetivo.

## 6. Opciones de salida

- Agregar resultados por celda madre: genera estadísticas multifractales locales y productos de confiabilidad.
- Expandir automáticamente el límite: ajusta el marco para obtener celdas madre completas.
- Exportar GeoPackage GIS: crea capas listas para revisar en QGIS u otro software GIS.
- Crear paquete ZIP: organiza y comprime los productos principales junto con la configuración y el registro de la corrida.

## 7. Controles de robustez

Estos controles aparecen en modo Geomatics.

### Preset baseline

Es el valor predeterminado y la opción recomendada para resultados principales. Usa zeta mínima de 0.15 y R cuadrado mínimo local de 0.90, sin bootstrap.

### Preset balanced

Añade bootstrap global y local con semilla reproducible. Requiere más tiempo que baseline y es útil para evaluar estabilidad.

### Preset experimental

Amplía las pruebas de incertidumbre y exporta sensibilidad de zeta. Puede aceptar resultados con R cuadrado desde 0.85 y zeta desde 0.10. Debe identificarse expresamente si se usa en un informe.

### Preset custom

Se activa cuando se modifican manualmente los parámetros. Registre los valores usados para que la corrida pueda reproducirse.

## 8. Ejecución

Antes de pulsar Ejecutar MUSA, confirme:

- Que las capas existen y pueden abrirse.
- Que el límite tiene CRS definido.
- Que la celda madre y los divisores son coherentes.
- Que q-step es mayor que cero y q-max es mayor que q-min.
- Que el directorio de salida tiene permisos de escritura.

Durante la corrida, el botón queda desactivado y el registro muestra el progreso. No cierre MUSA hasta que el estado indique Completo o aparezca un mensaje de error.

## 9. Resultados principales

- analysis_report.csv: espectro global con q, Dq, tau, alpha, f de alpha y calidad de ajuste.
- analysis_scale_diagnostics.csv: diagnóstico de cada escala usada en las regresiones.
- spectrum_fit_summary.csv: resumen geométrico y estadístico del espectro.
- monofractal_cells.csv y multifractal_cells.csv: resultados por celdas de análisis.
- monofractal_mother_agg.csv y multifractal_mother_agg.csv: resultados agregados por celda madre.
- multifractal_mother_scale_diagnostics.csv: soporte multiescala de cada celda madre.
- musa_mother_cells.gpkg: capas GIS de celdas madre y atributos interpretables.
- lineament_mother_structural_stats.csv: densidad, longitud y orientación estructural.
- lineament_network_stats.csv: estadísticas de conectividad de la red.
- Archivos PNG: gráficos del espectro, calidad de ajuste, zeta y distribución espacial.
- MUSA_Run con fecha y hora en formato ZIP: paquete organizado de la corrida.

Los archivos disponibles dependen de las opciones activadas y de que la agregación por celda madre esté habilitada.

## 10. Interpretación mínima

D0 representa la dimensión de capacidad, D1 la dimensión de información y D2 la dimensión de correlación. Deben interpretarse junto con el intervalo q aceptado y la calidad de los ajustes.

R cuadrado mide la calidad del ajuste en escala logarítmica. MUSA filtra los órdenes q que no alcanzan el criterio global configurado.

zeta es un peso operacional de confiabilidad multiescala. Resume cobertura, distribución de masa, soporte de escala y número efectivo de celdas. No es una propiedad física directa del terreno.

Una celda local se considera confiable cuando cumple simultáneamente los umbrales configurados de zeta y R cuadrado. Por ejemplo, un zeta_mean de 0.527 supera el umbral baseline de 0.15, pero debe verificarse también el R cuadrado y el soporte espacial antes de interpretarla.

## 11. Problemas frecuentes

### La aplicación parece detenida al sugerir escalas

Espere unos segundos, especialmente con archivos grandes o almacenados en una unidad sincronizada. La lectura geoespacial se realiza antes de mostrar la propuesta.

### Boundary sin CRS definido

Asigne a la capa el CRS correcto en un software GIS y vuelva a seleccionarla. No asigne un CRS por aproximación.

### El límite no es entero en metros

Reproyecte el límite a un CRS métrico apropiado y revise que su extensión sea compatible con la grilla deseada.

### No hay suficientes divisores exactos

Cambie la celda madre objetivo o active la expansión automática del límite.

### No aparecen productos locales o GIS

Active Agregar resultados por celda madre. La exportación GIS y la sensibilidad zeta dependen de esa opción.

### La corrida termina con error de escritura

Seleccione una carpeta de salida accesible, cierre archivos abiertos en Excel o QGIS y evite sobrescribir una corrida que esté siendo usada por otro programa.

### Parte de la interfaz no se ve

Use las barras de desplazamiento vertical y horizontal de la ventana. También puede maximizar MUSA.

## 12. Recomendaciones para informes

- Conserve el ZIP completo de la corrida usada en el informe.
- Registre versión de MUSA, preset, celda madre, divisores, intervalo q y umbrales.
- Reporte por separado ajuste global, confiabilidad local y resultados estructurales.
- No presente zeta como probabilidad ni como propiedad geológica directa.
- No interprete una cifra aislada sin su umbral, R cuadrado y contexto espacial.

Para la formulación matemática consulte docs/theory.md. Para las fuentes científicas consulte docs/references.md.
