<p align="center"><a href="README.md">English</a> · <strong>Español</strong></p>

# MUSA — Multifractal Spectrum Analyzer

**Análisis fractal y multifractal de datos espaciales y lineamientos, con productos GIS.**

Combina estimación directa Chhabra–Jensen, análisis local por celdas madre,
ponderación multiescala zeta, estadística estructural y exportación reproducible.
Permite examinar complejidad multifractal separadamente de densidad estructural
y confiabilidad numérica.

## Descarga e instalación

La aplicación Windows independiente no requiere instalar Python:
[descargar MUSA 1.0.1 para Windows x64](https://github.com/jordan-zav/MUSA/releases/download/v1.0.1/MUSA-1.0.1-Windows-x64.exe).
Consulta [Releases](https://github.com/jordan-zav/MUSA/releases/latest) para
notas y archivos. SHA-256 del ejecutable citado:

    d10181fd2f34c663dc0b05398f8ab48dfc10cded0fe19b710bb4db8602cfb158

Desde fuente requiere Python 3.10 o superior. En un entorno aislado:

~~~powershell
python -m pip install -e .
python -m pip install -e .[gis]
musa-ui
~~~

También puedes utilizar launch_musa_ui.bat en Windows. GIS es una dependencia
opcional para las funciones correspondientes.

## Flujo recomendado

1. Prepara lineamientos y límite de análisis en un CRS métrico o activa reproyección.
2. Define tamaño de celda madre y suficientes resoluciones internas.
3. Ejecuta el análisis global y revisa el intervalo de q aceptado.
4. Exporta celdas locales con zeta y las marcas reliable.
5. Compara densidad, orientación, alpha, alpha_w y confiabilidad.
6. Revisa sensibilidad de zeta y controles sintéticos antes de interpretar.

Los espectros globales y locales incluyen Dq, tau, alpha, f(alpha), calidad de
ajuste y diagnósticos de escala. Hay estimaciones locales D0/D1, alternativas
Theil–Sen, bootstrap, jackknife, apalancamiento y diagnóstico de Cook.
Los productos estructurales incluyen longitud, orientación, anisotropía y
conectividad. Se exportan CSV, PNG, GeoPackage y paquetes ZIP.

## Ejemplo Python

~~~python
import numpy as np
from musa import MUSA

rng = np.random.default_rng(42)
points = rng.random((5000, 2))
analyzer = MUSA(points, q_values=np.linspace(-4, 4, 9))
result = analyzer.run_analysis(min_scale=0.01, max_scale=0.4, num_scales=24)
print(result.q)
print(result.dq)
print(result.alpha)
~~~

Los [ejemplos](examples) amplían los flujos espaciales, GIS, sintéticos y estructurales.

## Ventanas móviles y desarrollo

Las ventanas multiescala superpuestas son experimentales. Exportan espectros y
uniones planares únicas con diagnósticos de cobertura y dominancia de q alto;
describen concentración estructural, no permeabilidad.

El perfil de desarrollo promedia 16 orígenes y siete escalas internas y mantiene
separados rangos descriptivos y clases sustentadas. Usa métodos genéricos y
controles sintéticos; los datos, reglas y entregas privadas no son ejemplos del
software. La aceleración opcional conserva una alternativa Python:

~~~powershell
pip install -e ".[gis,fast]"
~~~

- [Ventanas móviles y límites](docs/moving_windows.md).
- [Puntuación de candidatos](docs/candidate_scoring.md).
- [Teoría](docs/theory.md) y [referencias científicas](docs/references.md).

## Estado y límites

La release pública es 1.0.1. Las pruebas cubren espectros, zeta, modos de
interfaz, empaquetado GIS y casos sintéticos. La contribución es integrar estos
métodos y sus diagnósticos, no inventar el análisis multifractal de lineamientos.
Zeta es un peso operativo de confiabilidad, no una propiedad física medida.
Un ajuste estable o zeta alto no demuestra un proceso geológico; cada conjunto
requiere validación externa apropiada.

El paquete está en src/musa, los ejemplos en examples y las pruebas en tests.
Los resultados generados y experimentos locales se excluyen del control de versiones.

## Licencia y contacto

[GNU GPL v3](LICENSE), con fuente de las releases disponible en el repositorio.
Jordan Zavaleta — [correo](mailto:jordanzav@gisgeo.dev) · [GisGeo Dev](https://gisgeo.dev).
