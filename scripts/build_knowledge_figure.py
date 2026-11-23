"""Generate the small teaching diagram from geometry, with no external input."""
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle
import numpy as np
import json

from knowledge_examples import finite_cantor, random_rods, raster_comparison, synthetic_map


def build(target):
    fig = Figure(figsize=(8, 2.6), facecolor="white", constrained_layout=True)
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, 3)
    for ax, n in zip(axes[:2], (4, 8)):
        eps = 1 / n
        for i in range(n):
            ax.add_patch(Rectangle((i * eps, 0), eps, eps, facecolor="#e2ecf1", edgecolor="#517487"))
        ax.plot([0, 1], [eps / 2, eps / 2], color="#a45028", linewidth=2.5)
        ax.set(xlim=(-.05, 1.05), ylim=(-.08, .36), title=f"ε = 1/{n}     N = {n}")
        ax.set_aspect("equal")
        ax.axis("off")
    ax = axes[2]
    ax.plot(np.log([4, 8]), np.log([4, 8]), "o-", color="#24536b")
    ax.set(xlabel="ln(1/ε)", ylabel="ln N", title="D = 1", xticks=np.log([4, 8]), yticks=np.log([4, 8]))
    ax.set_xticklabels(['ln 4', 'ln 8'])
    ax.set_yticklabels(['ln 4', 'ln 8'])
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=120, metadata={"Software": "MUSA teaching diagram"})


def build_examples(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    raster, cantor, rods = raster_comparison(), finite_cantor(), random_rods()
    (folder / 'knowledge_measurements.json').write_text(
        json.dumps(dict(raster=raster, cantor=cantor, rods=rods), indent=2), encoding='utf-8')
    fig = Figure(figsize=(9, 5.6), constrained_layout=True)
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 2)
    lines, _ = synthetic_map()
    for line in lines:
        axes[0, 0].plot(*line.xy, color='#24536b', linewidth=1)
    axes[0, 0].set(xlim=(0, 128), ylim=(0, 128), xlabel='x (model m)', ylabel='y (model m)',
                   title='Synthetic traces / Trazas sintéticas')
    axes[0, 0].set_aspect('equal')
    for q, ax in zip((0, 1, 2), (axes[0, 1], axes[1, 0], axes[1, 1])):
        values = [row['dimensions'][q] for row in raster['rows']]
        ax.bar(np.arange(len(values)), values, color=['#ad572b'] + ['#477a90'] * 6)
        ax.axhline(values[0], color='#ad572b', linestyle='--', linewidth=1)
        ax.set(xticks=range(7), xticklabels=['Exact', '0.5 m\n1 px', '0.5 m\n3 px', '1 m\n1 px', '1 m\n3 px', '2 m\n1 px', '2 m\n3 px'],
               ylabel=f'D{q}', xlabel='Pixel size (m) / Tamaño de píxel (m); stroke / grosor (px)', title=f'q = {q}')
        for i, value in enumerate(values):
            ax.text(i, value + .025, f'{value:.3f}', ha='center', fontsize=8)
        ax.set_ylim(0, max(values) + .2)
    fig.savefig(folder / 'knowledge_raster.png', dpi=120)
    classic, report = cantor['classic'], cantor['assessment']
    x, y = np.log(1 / np.array(classic['scales_m'])), np.log(classic['occupied_boxes'])
    fit = np.polyval(np.polyfit(x, y, 1), x)
    fig = Figure(figsize=(8, 4.7), constrained_layout=True)
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 1, sharex=True)
    axes[0].plot(x, y, 'o', label='Classic counts / Conteos clásicos')
    axes[0].plot(x, fit, '-', label=f"OLS: D={classic['dimension']:.6f}; R²={classic['r2']:.6f}")
    used = report['used_scales_m']
    axes[0].axvspan(np.log(1 / max(used)), np.log(1 / min(used)), color='#90b49b', alpha=.2,
                    label=f'MUSA retained / retenido: {len(used)} scales')
    axes[0].set(ylabel='ln N', title='Finite Cantor / Cantor finito: 7 levels, 128 traces')
    axes[0].legend(fontsize=8)
    axes[1].axhline(0, color='gray', linewidth=1)
    axes[1].plot(x, y - fit, 'o-')
    axes[1].set_ylim(-.01, .01)
    axes[1].text(.02, .08, 'Residuals < 3×10⁻¹⁵ (floating-point rounding) / redondeo',
                 transform=axes[1].transAxes, fontsize=8)
    axes[1].set(xlabel='ln(1/ε)  [ε in model m]', ylabel='OLS residual / Residuo')
    fig.suptitle('MUSA: insufficient information / información insuficiente\n4 resolved scales; minimum 8 / 4 escalas resueltas; mínimo 8', fontsize=10)
    fig.savefig(folder / 'knowledge_cantor.png', dpi=120)
    classic, report = rods['classic'], rods['assessment']
    x = np.log(1 / np.array(classic['scales_m']))
    y = np.log(classic['occupied_boxes'])
    fit = np.polyval(np.polyfit(x, y, 1), x)
    row = report['q_results'][0]
    fig = Figure(figsize=(8.5, 6), constrained_layout=True)
    FigureCanvasAgg(fig)
    axes = fig.subplots(2, 1, sharex=True)
    axes[0].plot(x, y, 'o', label='Classic counts / Conteos clásicos', markersize=4)
    axes[0].plot(x, fit, label=f"OLS: D={classic['dimension']:.6f}; R²={classic['r2']:.6f}")
    used = report['used_scales_m']
    axes[0].axvspan(np.log(1/max(used)), np.log(1/min(used)), alpha=.18, color='#82ae94',
                    label=f'MUSA retained / retenido: {len(used)} scales / escalas')
    # Four-origin mean H0 is the actual curve assessed by MUSA.
    curves = [c for c in report['curves'] if c['q'] == 0]
    mean = [np.mean([c['entropy'] for c in curves if c['scale_m'] == scale]) for scale in used]
    axes[0].plot(np.log(1/np.array(used)), mean, '--', label='MUSA mean H0 / H0 medio')
    axes[0].set(ylabel='ln N', title='100 random rods / 100 segmentos aleatorios (seed / semilla 42)')
    axes[0].legend(fontsize=8)
    axes[1].axhline(0, color='gray', linewidth=1)
    axes[1].plot(x, y-fit, 'o-', label='Classic OLS / OLS clásico')
    centered = np.log(1/np.array(used)) - row['x_center_log_inverse_scale']
    beta = row['models']['linear']['coefficients']
    axes[1].plot(np.log(1/np.array(used)), np.array(mean)-np.polyval(beta[::-1], centered),
                 's--', label='MUSA mean / media')
    axes[1].set(xlabel='ln(1/ε) [ε in model m / m de modelo]', ylabel='Residual / Residuo')
    axes[1].legend(fontsize=8)
    fig.suptitle('MUSA D0: not supported / no respaldado\n'
                 'Quadratic and segmented predictions improve CV error /\n'
                 'La curvatura y el cambio de pendiente mejoran el error predictivo', fontsize=10)
    fig.savefig(folder / 'knowledge_rods.png', dpi=120)
    return dict(raster=raster, cantor=cantor, rods=rods)


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "docs/images/knowledge_box_counting.png")
    build_examples(Path(__file__).resolve().parents[1] / 'docs/images')
