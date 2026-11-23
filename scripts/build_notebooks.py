"""Build the five small, synthetic Python API tutorials (no QGIS imports)."""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]

SETUP = '''from pathlib import Path
import os
import sys
import time
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from IPython.display import display, Image
from shapely.geometry import LineString, box
from pyproj import CRS

started_wall, started_cpu = time.perf_counter(), time.process_time()
repository = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "src/musa").is_dir())
sys.path.insert(0, str(repository / "src"))
sys.path.insert(0, str(repository / "scripts"))
from musa import MUSA, ScalingOptions, assess_lineament_scaling, write_scaling_reports
crs = CRS.from_proj4("+proj=eqc +R=6371000 +units=m +no_defs +type=crs")
lines = [LineString([(1000, 1500), (9000, 6500)])]
domain = box(0, 0, 10000, 10000)
scales = np.geomspace(10, 1000, 16)
model = MUSA.from_line_geometries(lines, domain, crs, q_values=[0, 1, 2])
output = Path(os.environ.get("MUSA_NOTEBOOK_OUTPUT_ROOT", repository / "outputs/notebooks")) / "{name}"
output.mkdir(parents=True, exist_ok=True)
def save_figure(figure, name):
    target = output / (name + ".png")
    figure.savefig(target, dpi=120, bbox_inches="tight")
    display(Image(filename=str(target)))
    plt.close(figure)
print("Synthetic inputs; unlocated model metres. Outputs:", output.name)
'''

FINISH = '''metrics = dict(wall_seconds=time.perf_counter()-started_wall,
               cpu_seconds_kernel=time.process_time()-started_cpu)
(output / "execution.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(json.dumps(metrics))
'''


def notebook(name, title, intro, steps):
    cells = [nbf.v4.new_markdown_cell('# ' + title + '\n\n' + intro),
             nbf.v4.new_code_cell(SETUP.replace('{name}', name))]
    for explanation, code in steps:
        cells.extend([nbf.v4.new_markdown_cell(explanation), nbf.v4.new_code_cell(code)])
    cells.append(nbf.v4.new_code_cell(FINISH))
    nb = nbf.v4.new_notebook(cells=cells, metadata=dict(
        kernelspec=dict(display_name='Python 3', language='python', name='python3'),
        language_info=dict(name='python'), musa=dict(synthetic=True, qgis_required=False)))
    target = ROOT / 'notebooks' / (name + '.ipynb')
    target.parent.mkdir(exist_ok=True)
    nbf.write(nb, target)


def build():
    notebook('01_first_analysis', '01 · Primer análisis con la API',
             'Se miden Dq, tau, alpha y f(alpha) de una traza dentro de un dominio cuadrado. '
             'Los metros son unidades de modelo sin ubicación geográfica. Se declaran los parámetros antes del cálculo. '
             'La tabla descriptiva conserva las estimaciones; el diagnóstico examina su respaldo por separado.', [
        ('## Mapa y cálculo descriptivo\n\nSe usan q=0…4 y cinco escalas descriptivas; el filtro R² es 0,9.', '''model = MUSA.from_line_geometries(lines, domain, crs, q_values=np.arange(5.))
result = model.run_analysis(resolutions_m=[1000, 500, 250, 125, 62.5], min_r2=.9)
table = pd.DataFrame(dict(q=result.q, Dq=result.dq, tau=result.tau, alpha=result.alpha, f_alpha=result.f_alpha))
assert result.accepted_count == 5
np.testing.assert_allclose(result.tau, (result.q-1)*result.dq, atol=1e-10)
table.to_csv(output / "per_q.csv", index=False)
display(table)
figure, ax = plt.subplots(figsize=(5, 4))
ax.plot(*domain.exterior.xy, color="gray")
ax.plot(*lines[0].xy)
ax.set(xlabel="x (model m)", ylabel="y (model m)", aspect="equal")
save_figure(figure, "map")'''),
        ('## Las cuatro magnitudes por q\n\nLa línea uniforme tiene Dq cercano a uno en este diseño. '
         'Cada punto f(alpha(q)) se muestra frente a q. La forma conjunta f(alpha) requiere controles adicionales.', '''figure, axes = plt.subplots(2, 2, figsize=(8, 6), constrained_layout=True)
for ax, field in zip(axes.ravel(), ["Dq", "tau", "alpha", "f_alpha"]):
    ax.plot(table.q, table[field], "o-")
    ax.set(xlabel="q", ylabel=field)
    if np.ptp(table[field]) < 1e-6:
        middle = float(table[field].mean())
        ax.set_ylim(middle-.02, middle+.02)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
save_figure(figure, "four_observables")
report = assess_lineament_scaling(model, scales, ScalingOptions(1, renyi_order_policy="inform_q0_q2"))
write_scaling_reports(output / "assessment", [report])
display(pd.DataFrame(report["q_results"])[["q", "dimension", "tau", "alpha", "f_alpha", "status"]])''')])

    notebook('02_scaling_states', '02 · Tres estados del diagnóstico',
             'Los controles de curva aíslan el diagnóstico del muestreo geométrico: '
             'una ley lineal, una curva y un intervalo con pocas observaciones. '
             'La traza sintética del cuaderno 01 aporta además un diagnóstico geométrico completo.', [
        ('## Controles declarados\n\nLa opción exige ocho escalas y una década. La curva se construye antes de evaluar los estados.', '''from musa.scaling import assess_curve
x = np.log(1/scales)
options = ScalingOptions(1)
controls = {"lineal": (scales, 5+1.2*x),
            "curva": (scales, 5+1.2*x+.15*x*x),
            "cuatro escalas": (scales[:4], (5+1.2*x)[:4])}
reports = {name: assess_curve(s, h, options) for name, (s, h) in controls.items()}
assert {r["status"] for r in reports.values()} == {"compatible_finite_range", "not_supported", "insufficient_information"}
table = pd.DataFrame([dict(control=k, status=r["status"], dimension=r.get("dimension"), reasons=r["reasons"]) for k,r in reports.items()])
display(table)
table.to_csv(output / "three_states.csv", index=False)
(output / "three_states.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
figure, axes = plt.subplots(1, 3, figsize=(10, 3), constrained_layout=True)
for ax, (name, (s, h)) in zip(axes, controls.items()):
    ax.plot(np.log(1/s), h, "o-")
    ax.set(title=name, xlabel="ln(1/epsilon)", ylabel="Hq")
save_figure(figure, "states")'''),
        ('## Interpretación\n\nCompatible se refiere al intervalo probado. Sin respaldo conserva el motivo del fallo. '
         'Información insuficiente conserva la ausencia de una dimensión; nunca se sustituye por cero.', '''full = assess_lineament_scaling(model, scales, ScalingOptions(1, renyi_order_policy="inform_q0_q2"))
short = assess_lineament_scaling(model, scales[:4], ScalingOptions(1))
assert all(row["dimension"] is None for row in short["q_results"])
write_scaling_reports(output / "maps", [full, dict(short, support_id="short")])
display(pd.DataFrame(full["q_results"])[["q", "status", "dimension"]])''')])

    notebook('03_classic_and_exact_length', '03 · Píxeles, longitud exacta y R² clásico',
             'Se repiten exactamente los ejemplos calculados de Fundamentos: once trazas oblicuas con '
             'agrupamiento, 100 segmentos aleatorios y un Cantor finito de siete niveles. Se usa Python sin QGIS. '
             'Las funciones versionadas generan geometrías y llaman al mismo núcleo de MUSA.', [
        ('## Longitud frente a área de tinta\n\nSe conserva origen (0,0), cajas 2…32 m y seis configuraciones de píxel/grosor. '
         'Cada celda exacta recibe longitud geométrica; cada píxel binario aporta su área una vez.', '''from knowledge_examples import raster_comparison, finite_cantor, random_rods
from build_knowledge_figure import build_examples
comparison = raster_comparison()
table = pd.DataFrame([dict(measure=row["label"], D0=row["dimensions"][0], D1=row["dimensions"][1], D2=row["dimensions"][2]) for row in comparison["rows"]])
display(table)
np.testing.assert_allclose(comparison["rows"][0]["total_lengths"], comparison["total_geometric_length"], rtol=1e-12)
assert abs(table.iloc[-1].D0-table.iloc[0].D0) > .2
table.to_csv(output / "raster_vs_length.csv", index=False)
build_examples(output)
display(Image(filename=str(output / "knowledge_raster.png")))'''),
        ('## R² alto y curvatura con 24 escalas\n\nSe repite el control de 100 segmentos aleatorios de 1000 m, '
         'semilla 42, cajas geométricas de 50 a 2000 m y resolución 1 m. Los umbrales son los actuales del núcleo.', """rods = random_rods()
row = rods["assessment"]["q_results"][0]
assert rods["classic"]["r2"] > .99
assert len(rods["assessment"]["used_scales_m"]) == 24
assert row["status"] == "not_supported"
assert {"quadratic_predicts_better", "segmented_predicts_better"} <= set(row["reasons"])
print("D_BC:", rods["classic"]["dimension"], "R2:", rods["classic"]["r2"])
display(pd.DataFrame(rods["assessment"]["q_results"])[["q", "status", "dimension", "reasons"]])
display(pd.DataFrame(row["margins"]["curvature"]).T)
display(Image(filename=str(output / "knowledge_rods.png")))"""),
        ('## Cantor: valor clásico correcto y cuatro escalas\n\nEl clásico acierta ln(2)/ln(3). '
         'MUSA se abstiene por contar con cuatro escalas frente al mínimo ocho.', """cantor = finite_cantor()
assert np.isclose(cantor["classic"]["dimension"], np.log(2)/np.log(3))
assert all(row["status"] == "insufficient_information" for row in cantor["assessment"]["q_results"])
print("D_BC correcto:", cantor["classic"]["dimension"])
display(Image(filename=str(output / "knowledge_cantor.png")))""")])

    notebook('04_trace_relocation', '04 · Recolocación condicional con 19 réplicas',
             'El modelo traslada cada traza conservando forma, longitud y orientación dentro del mismo polígono. '
             'La prueba evalúa T=D0−D2 con semilla 42 y cola bilateral. Se demuestra la ejecución con pocas réplicas.', [
        ('## Simulación y reporte\n\nEl intervalo de 16 escalas 10…1000 m queda fijo. '
         'La política inform_q0_q2 conserva la advertencia de orden junto al contraste.', '''options = ScalingOptions(1, null_replicates=19, seed=42, renyi_order_policy="inform_q0_q2", null_tail="two_sided")
report = assess_lineament_scaling(model, scales, options)
assert report["null"]["status"] == "complete"
assert len(report["null"]["values"]) == 19
write_scaling_reports(output / "assessment", [report])
saved = json.loads((output / "assessment/scaling_support.json").read_text())["supports"][0]["null"]
display(pd.DataFrame([{key:saved[key] for key in ["observed", "p_value", "p_holm", "minimum_p", "holm_family_size"]}]))
figure, ax = plt.subplots(figsize=(6, 3))
ax.hist(saved["values"], bins=7, label="Relocations")
ax.axvline(saved["observed"], color="brown", label="Observed")
ax.set(xlabel="T = D0-D2 (dimensionless)", ylabel="Replicates")
ax.legend()
save_figure(figure, "null_distribution")
assert np.isclose(saved["minimum_p"], .1)
print("19 replicates: minimum two-sided p=0.1; rejection at 0.05 is unresolved.")'''),
        ('## Una familia declarada\n\nAquí se solicita un soporte y Holm conserva su p. '
         'El recorrido QGIS incluye diez soportes y obtiene p de Holm=1; la familia forma parte de la lectura.', '''print("Raw p:", saved["p_value"], "Holm p:", saved["p_holm"])
assert not saved["reject_relocation_at_0_05"]
assert not saved["resolution_sufficient_for_family_at_0_05"]''')])

    notebook('05_moving_windows', '05 · Ventanas móviles y cobertura',
             'Se estiman soportes locales sobre la misma traza sintética. Ventanas y centros se fijan antes '
             'de calcular; el solapamiento hace dependientes las estimaciones. Se usa la API Python y GeoPandas.', [
        ('## Ejecutar ventanas\n\nSe fijan ventanas de 4000 m, paso 4000 m y cuatro divisores internos. '
         'La salida conserva cobertura y motivos para todas las ventanas y q.', '''from musa.moving import analyze_moving_windows
windows, nodes, configuration = analyze_moving_windows(model, [4000], 4000, divisors=(2,4,8,16), q_values=[0,1,2])
assert len(windows) > 0 and windows.center_id.nunique() == 9
assert (windows.coverage < .8).any()
display(windows[["center_id", "window_m", "q", "coverage", "dq", "accepted", "reason"]])
windows.drop(columns="geometry").to_csv(output / "windows.csv", index=False)
nodes.drop(columns="geometry").to_csv(output / "nodes.csv", index=False)
(output / "configuration.json").write_text(json.dumps(configuration, indent=2), encoding="utf-8")
figure, ax = plt.subplots(figsize=(5, 5))
windows.drop_duplicates("center_id").plot(ax=ax, column="coverage", vmin=0, vmax=1, legend=True, alpha=.4, edgecolor="gray")
ax.plot(*lines[0].xy, color="brown")
ax.plot(*domain.exterior.xy, color="black")
ax.set(xlabel="x (model m)", ylabel="y (model m)", title="Observed coverage (fraction)")
save_figure(figure, "window_coverage")'''),
        ('## Conservar abstenciones\n\nUna ventana con menos del 80 % observado conserva su estado y sus motivos. '
         'Las curvas locales canónicas y ponderadas tienen contratos separados. El paso cambia el solapamiento, '
         'mientras la resolución procede de la cartografía.', '''low = windows[windows.coverage < .8]
assert not low.accepted.any()
display(low[["center_id", "coverage", "q", "reason"]].head(9))
print("Unique supports:", windows.center_id.nunique(), "rows:", len(windows))''')])


if __name__ == '__main__':
    build()
