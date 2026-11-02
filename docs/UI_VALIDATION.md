# Revisión de uso habitual de la interfaz

Revisión del 2 de noviembre de 2026 sobre MUSA experimental 1.0.0, con QGIS 3.44.12 para Windows. El [manual ilustrado](USER_GUIDE.es.md) muestra el flujo comprobado. Las capturas se obtuvieron del complemento real en un runtime nativo de QGIS, mediante scripts reproducibles y un perfil temporal de comprobación.

## Correcciones incluidas

- Results recupera su desplazamiento exterior cuando el panel es pequeño.
- La rueda sobre gráficos y selectores desplaza Results; no cambia accidentalmente el centro seleccionado.
- La tabla y el visor de detalles conservan su desplazamiento interior.
- Run details recupera estado, fechas, procedencia, configuración y salidas del manifiesto al abrir una ejecución guardada.
- Cada ejecución nueva vacía los mensajes anteriores; al terminar puede conservar sus propios mensajes junto a los detalles. No se fabrica un registro histórico de progreso al reabrir una carpeta.
- Las ventanas con cobertura insuficiente muestran el porcentaje y motivo, conservando sus valores ausentes.
- Los gráficos nativos se adaptan al panel; sus ampliaciones y las imágenes originales se abren al hacer clic.

## Casos comprobados

| Caso | Resultado observado |
| --- | --- |
| Abrir una ejecución terminada | Selectores, figuras y tabla recuperados sin recalcular ni duplicar capas |
| Abrir Run details | Datos recuperados; contenido no vacío y desplazamiento interior operativo |
| Panel de 680 × 600 en la prueba dirigida | Scroll exterior disponible; controles inferiores accesibles |
| Rueda sobre gráfico | La posición de Results cambia |
| Rueda sobre selector de centro | Results se desplaza y el centro permanece seleccionado |
| Center 1 de Åland | Cobertura de 66,7 %, inferior al mínimo de 80 %; nueve q sin estimaciones, con motivo |
| Center 5 de Åland | Cobertura de 99,6 %; dos de nueve q utilizables para el espectro completo |
| Dq frente a espectro completo | Se conservan estados diferentes por observable, sin promover el espectro completo |
| Pulsar un espectro | Abre una ampliación nativa; cierre sin repetir el análisis |
| Pulsar una figura guardada | Abre el original con controles de ampliación y desplazamiento |
| Exportación | PNG y SVG del soporte seleccionado generados |
| Cambio entre fuentes y estimadores | Global/ventanas y análisis/diagnóstico permanecen separados |

La comprobación nativa general también cubre Processing, ejecución en segundo plano, reproyección, selección de líneas, GeoPackage, ejecuciones sucesivas y descarga del complemento durante una tarea. Las pruebas no se limitan a una captura de una interfaz estática.

## Reproducción y entrega documental

La comprobación general se ejecuta con tests/qgis_smoke.py sobre un ZIP construido con scripts/build_qgis_plugin.py, usando scripts/run_qgis_python.cmd y MUSA_QGIS_ROOT en el entorno de desarrollo Windows.

scripts/capture_user_guide_qgis.py recibe cuatro rutas: ZIP del plugin, GeoPackage con lineaments/boundary, ejecución terminada y carpeta de entrega. Conserva los datos originales y crea las capturas y un proyecto de ejemplo con referencias relativas. Requiere un ejemplo público apropiado para compartir.

scripts/build_user_manual.py recibe el Markdown y la carpeta de salida. Genera Word, HTML y Markdown portable; requiere python-docx y Pillow en el entorno de documentación. El PDF de la entrega se exportó desde Word y se comprobó con un lector independiente. Las imágenes originales se conservan separadas para ampliarlas.

## Límites

No se afirma cobertura exhaustiva de versiones QGIS, sistemas operativos, escalados de pantalla o todos los tamaños posibles de panel. Las comprobaciones de interfaz no prueban multifractalidad de una red. La resolución operacional y los estados de calidad del ejemplo se conservan sin modificar umbrales para producir curvas.
