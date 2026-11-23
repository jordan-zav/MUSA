# Cuadernos ejecutables de MUSA

Cinco recorridos de la API Python, sin QGIS y sin descargas. Todas las geometrías
son sintéticas y sus metros son unidades de modelo sin ubicación geográfica.
Los cuadernos guardados incluyen tablas y figuras de una ejecución completa.

| Cuaderno | Contenido |
| --- | --- |
| [01](01_first_analysis.ipynb) | Primer análisis: mapa, Dq, tau, alpha y f(alpha) por q |
| [02](02_scaling_states.ipynb) | Diagnóstico compatible, sin respaldo e información insuficiente |
| [03](03_classic_and_exact_length.ipynb) | Ráster/longitud, 100 segmentos aleatorios con R² alto y curvatura, y Cantor como abstención por cuatro escalas |
| [04](04_trace_relocation.ipynb) | Recolocación bilateral con 19 réplicas y lectura de p y Holm |
| [05](05_moving_windows.ipynb) | Ventanas, cobertura, valores ausentes y dependencia por solapamiento |

Se requiere un checkout del repositorio con Python >=3.10 y las dependencias de
requirements-dev.txt, que incluyen el núcleo, GIS, nbclient, nbformat e ipykernel.
Se pueden abrir desde Jupyter con un kernel que tenga esas dependencias. La
ejecución reproducible desde la raíz usa el mismo intérprete que el lanzador:

~~~text
python -m pip install -r requirements-dev.txt
python scripts/execute_notebooks.py --output outputs/executed_notebooks
python -m pytest tests/test_notebooks.py -q
~~~

El ejecutor crea una especificación de kernel propia dentro de su carpeta de
salida y ejecuta los cinco cuadernos en serie, con límite total de diez minutos.
MUSA_NOTEBOOK_OUTPUT_ROOT permite elegir dónde guardar CSV, JSON y PNG;
interactivamente se utiliza outputs/notebooks. Cada cuaderno registra tiempo
de pared y CPU de su kernel en execution.json. La suite ejecuta los cinco sin
omitirlos; las dependencias ausentes hacen fallar la instalación o la prueba.
El workflow de tests instala esos requisitos y ejecuta la misma prueba.

En la revisión local del 22 de noviembre de 2026 se reutilizaron las dependencias
ya disponibles del intérprete de desarrollo, sin instalar paquetes adicionales.
Si hace falta aislar dependencias locales, se deben alojar en el recurso
compartido de desarrollo indicado por las instrucciones del entorno.

Los cuadernos y sus productos quedan fuera del ZIP de QGIS. El generador
scripts/build_notebooks.py conserva su estructura; volver a generarlos elimina
las salidas guardadas, por lo que debe seguirle una ejecución antes de commitear.
El cuaderno 03 reutiliza scripts/knowledge_examples.py y build_knowledge_figure.py
del checkout para asegurar que figuras y cifras coincidan con Fundamentos.
