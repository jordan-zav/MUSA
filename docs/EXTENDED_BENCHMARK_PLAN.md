# Plan de ampliación de validación de MUSA

Fecha: 2026-11-02. Trabajo local autorizado por el usuario; conservar cambios existentes y entregas anteriores. No publicar automáticamente ni incorporar datos al plugin.

1. Inventario y procedencia. Inspeccionar las fuentes de Åland, Hornelen, Bristol Channel, GeoCrack, FraXet y HatchFrac; conservar metadatos, licencias, hashes y enlaces a artículos. Priorizar geometrías originales sobre redigitalización de figuras. Registrar las fuentes inaccesibles sin sustituirlas silenciosamente.
2. Preparación reproducible. Crear adaptadores de vectores, MATLAB y máscaras según los archivos efectivamente obtenidos. Conservar CRS, resolución y dominio observacional declarados. Separar datos georreferenciados, modelos sin ubicación y derivados de imágenes. Evitar convertir parches distintos en un supuesto afloramiento continuo.
3. Referencias matemáticas. Ampliar los controles mono/multifractales y negativos; evaluar Dq, tau, alpha y f(alpha), identidades y errores frente a valores analíticos. Revisar muestreo, rango de escalas y q negativos según De Souza y Rostirolla, Roy, Bour y Ouillon. No asignar dimensiones teóricas a redes naturales sin correspondencia de medida y escala.
4. Ejecución. Procesar datos naturales/sintéticos disponibles con MUSA, globalmente y mediante ventanas, usando intervalos declarados antes de ajustar y conservando rechazos. Comparar resoluciones/representaciones cuando existan; añadir comprobaciones independientes de box-counting o medidas de referencia compatibles. Aplicar simulaciones nulas a un subconjunto viable y documentar su alcance.
5. QGIS. Crear proyectos portables por familia de coordenadas/datos; verificar capas, tablas, apertura del visor y procesamiento representativo en QGIS 3.44.12. Revisar visualmente mapas y curvas sin modificar el perfil habitual del usuario.
6. Calidad y entrega. Ejecutar pruebas relevantes y Ruff; corregir defectos demostrados. Preparar informes en español, inventario completo de estados, figuras y ZIP verificado con hashes. Distinguir pruebas completadas, límites científicos y bloqueos externos.

Código y scripts: O:/0. Projects/0. Other Projects/MUSA. Originales públicos: D:/DevResources/Shared/MUSA-benchmarks. Resultados: una sesión nueva dentro de D:/DevResources/Sessions. Utilizar DEVRESOURCES_RUN.cmd para comandos de desarrollo y los lanzadores QGIS existentes.

## Ejecución

Fases 1–5 completadas: inventario y adaptadores; 67 casos procesados sin errores pendientes; controles matemáticos y de rango; cuadrantes e interiores solapados; ocho proyectos QGIS y 67 ejecuciones revisadas en el visor. Dos casos se repitieron por Processing con curvas numéricamente equivalentes a Python. Se conservan los resultados iniciales de ventanas antes de añadir los interiores.

GeoCrack quedó en metadatos por HTTP403/verificación antibot de Harvard Dataverse; no se afirma descargar sus máscaras. Zhu sigue identificado como coordenadas no descargadas. Se documenta selección FraXet parcial, variantes relacionadas y límites de inferencia en EXTENDED_BENCHMARKS.md. Los artículos orientan comparaciones; no se incorporan algoritmos ajenos enteros que no formen parte del alcance.

Fase 6 completada: 53 pruebas dirigidas y Ruff correctos; informe, inventarios, figuras y archivo ZIP verificado. Se comprobaron hashes de 67 entradas y 498 archivos de resultados, además del CRC del ZIP. Evidencias finales en D:/DevResources/Sessions/MUSA-extended-benchmarks-20261102_143812. ZIP: 34.847.311 bytes; SHA256 f541d903efef30b513c066ac15ea506be55c0e912522f36c30264076b8d4630d. Los resultados no certifican fractalidad universal ni se publican como release.
