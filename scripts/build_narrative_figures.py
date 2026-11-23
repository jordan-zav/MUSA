"""Bilingual narrative figures, calculated from synthetic geometry, never screenshots.

Run with the project Python. All numeric plot inputs are saved beside the PNGs.
"""
import json
import argparse
from pathlib import Path

import numpy as np
from matplotlib import rc_context
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle, Polygon
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from PIL import Image, ImageChops
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely import intersection, length as geometry_length

from tutorial_network import fracture_network
from knowledge_examples import raster_comparison, random_rods, finite_cantor, synthetic_map
from musa.partition import line_cell_segments

BLUE, ORANGE = '#24536b', '#b45628'


def binary_geometries():
    return [[LineString([(45, 50), (55, 50)])],
            [LineString([(0, 5+10*i), (100, 5+10*i)]) for i in range(10)]]


def grid_masses(lines, scale):
    masses = {}
    for key, length, _ in line_cell_segments(lines, scale, (0., 0.)):
        masses[key] = masses.get(key, 0.) + length
    return masses


def map_measurements(lines, domain):
    """Sample the same vector measurements at 100 m; retain exact boundary clip."""
    union = unary_union(lines)
    coords = np.arange(50, 10000, 100)
    density, distance = [], []
    for y in coords:
        for x in coords:
            point = Point(x, y)
            if not domain.covers(point):
                density.append(None)
                distance.append(None)
                continue
            disk = point.buffer(1000, quad_segs=64).intersection(domain)
            density.append(float(geometry_length(intersection(lines, disk)).sum()) / disk.area)
            distance.append(point.distance(union))
    return dict(coordinates_m=coords.tolist(), cell_m=100, radius_m=1000,
                density_per_m=density, nearest_m=distance,
                distance_display_percentile=95,
                distance_display_max_m=float(np.percentile([v for v in distance if v is not None], 95)))


def calculate():
    lines, domain, families = fracture_network()
    maps = map_measurements(lines, domain)
    angles = [(90 - np.degrees(np.arctan2(line.coords[-1][1]-line.coords[0][1],
                                        line.coords[-1][0]-line.coords[0][0]))) % 180 for line in lines]
    bins = np.arange(0, 181, 10)
    rose = np.histogram(angles, bins, weights=[line.length for line in lines])[0]
    grids = []
    for scale in (2000., 1000., 500.):
        masses = grid_masses(lines, scale)
        grids.append(dict(scale_m=scale, count=len(masses), total_length_m=sum(masses.values()),
                          cells=[dict(i=int(k[0]), j=int(k[1]), length_m=v) for k, v in sorted(masses.items())]))
    return dict(network=dict(trace_count=len(lines), total_length_m=sum(line.length for line in lines),
                             domain_area_m2=domain.area, families=families),
                maps=maps,
                rose=dict(edges_degrees=bins.tolist(), length_m=rose.tolist()), grids=grids,
                binary=dict(side_m=100, lengths_m=[sum(line.length for line in traces) for traces in binary_geometries()],
                            occupied_counts=[int(sum(line.length for line in traces) > 0) for traces in binary_geometries()]),
                koch=dict(levels=list(range(4)), segments=[4**n for n in range(4)],
                          segment_length=[3.**-n for n in range(4)], dimension=float(np.log(4)/np.log(3))),
                raster=raster_comparison(), rods=random_rods(), cantor=finite_cantor())


def render(folder, data, lang):
    es = lang == 'es'
    def t(a, b):
        return a if es else b
    def figure(rows=1, cols=1, height=4):
        fig = Figure(figsize=(10, height), layout='constrained', facecolor='white')
        FigureCanvasAgg(fig)
        return fig, fig.subplots(rows, cols, squeeze=False)
    def save(fig, name):
        path = folder / f'knowledge_{name}.{lang}.png'
        fig.savefig(path, dpi=120, pad_inches=.08)
        # Identical physical width and font sizes; lossless full-color PNG.
        with Image.open(path) as im:
            height = round(im.height * 1200 / im.width)
            im = im.convert('RGB').resize((1200, height), Image.Resampling.LANCZOS)
            # Trim only vertical whitespace, preserving physical width and type scale.
            bounds = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).getbbox()
            if bounds:
                im = im.crop((0, max(0, bounds[1]-8), 1200, min(im.height, bounds[3]+8)))
            im.save(path, optimize=True)
    lines, domain, _ = fracture_network()
    def map_axes(ax, traces=True):
        ax.plot(*domain.exterior.xy, color='#777777', lw=1)
        if traces:
            for line in lines:
                ax.plot(*line.xy, color=BLUE, lw=.65)
        ax.set(xlim=(0, 10000), ylim=(0, 10000), xlabel=t('x (m de modelo)', 'x (model m)'),
               ylabel=t('y (m de modelo)', 'y (model m)'))
        ax.set_aspect('equal')
    fig, axes = figure(height=6)
    map_axes(axes[0, 0])
    axes[0, 0].set_title(t('627 trazas, un dominio observado', '627 traces, one observed domain'))
    save(fig, 'network')
    for name, key, title, label in [
        ('density', 'density_per_m', t('Densidad: radio de 1000 m', 'Density: 1000 m radius'), t('Longitud / área (m/m²)', 'Length / area (m/m²)')),
        ('distance', 'nearest_m', t('Distancia a la traza más cercana', 'Distance to nearest trace'), t('Distancia (m de modelo)', 'Distance (model m)'))]:
        fig, axes = figure(height=6)
        ax = axes[0, 0]
        side = len(data['maps']['coordinates_m'])
        values = np.array([np.nan if x is None else x for x in data['maps'][key]]).reshape(side, side)
        im = ax.imshow(values, extent=(0, 10000, 0, 10000), origin='lower',
                       cmap='YlOrRd' if name == 'density' else 'YlGnBu',
                       vmin=0, vmax=None if name == 'density' else data['maps']['distance_display_max_m'],
                       interpolation='nearest')
        im.set_clip_path(Polygon(np.asarray(domain.exterior.coords), transform=ax.transData))
        map_axes(ax)
        ax.set_title(title)
        fig.colorbar(im, ax=ax, label=label, shrink=.9, extend='max' if name == 'distance' else 'neither')
        save(fig, name)
    fig = Figure(figsize=(10, 4.5), layout='constrained')
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(121)
    map_axes(ax)
    ax.set_title(t('La misma red', 'The same network'))
    ax = fig.add_subplot(122, projection='polar')
    theta = np.deg2rad(np.arange(5, 180, 10))
    values = np.array(data['rose']['length_m']) / 1000
    ax.bar(np.r_[theta, theta+np.pi], np.r_[values, values], width=np.deg2rad(10), color=BLUE, alpha=.8)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_title(t('Rosa axial: longitud (km)', 'Axial rose: length (km)'), pad=20)
    ax.tick_params(pad=6)
    save(fig, 'rose')
    fig, axes = figure(2, 2, 5)
    points = np.array([0+0j, 1+0j])
    for level, ax in enumerate(axes.flat):
        ax.plot(points.real, points.imag, color=BLUE, lw=1.6)
        ax.set_aspect('equal')
        ax.set(xlim=(-.03, 1.03), ylim=(-.04, .33), title=t(f'Koch: paso {level}', f'Koch: step {level}'),
               xlabel=t('x (unidad ideal)', 'x (ideal unit)'), ylabel=t('y (unidad ideal)', 'y (ideal unit)'))
        new = []
        for a, b in zip(points[:-1], points[1:]):
            d = (b-a)/3
            new.extend([a, a+d, a+d+d*np.exp(1j*np.pi/3), a+2*d])
        points = np.array([*new, points[-1]])
    save(fig, 'koch')
    fig, axes = figure(1, 3, 4)
    for row, ax in zip(data['grids'], axes.flat):
        s = row['scale_m']
        for cell in row['cells']:
            patch = Rectangle((cell['i']*s, cell['j']*s), s, s, fc='#d7e6ed', ec='#9eb3be', lw=.5)
            patch.set_clip_path(Polygon(np.asarray(domain.exterior.coords), transform=ax.transData))
            ax.add_patch(patch)
        map_axes(ax)
        ax.set_title(f'ε = {s:g} m; N = {row["count"]}')
    save(fig, 'boxes')
    fig, axes = figure(1, 3, 2.5)
    for n, ax in zip((4, 8), axes.flat):
        eps = 1/n
        for i in range(n):
            ax.add_patch(Rectangle((i*eps, 0), eps, eps, fc='#d7e6ed', ec=BLUE))
        ax.plot([0, 1], [eps/2]*2, color=ORANGE, lw=2)
        ax.set_aspect('equal')
        ax.set(xlim=(-.03, 1.03), ylim=(-.03, .28), title=f'ε = 1/{n}; N = {n}')
        ax.axis('off')
    ax = axes[0, 2]
    ax.plot(np.log([4, 8]), np.log([4, 8]), 'o-', color=BLUE)
    ax.set(xlabel='ln(1/ε)', ylabel='ln N', title='D = 1', xticks=np.log([4, 8]), yticks=np.log([4, 8]))
    ax.set_xticklabels(['ln 4', 'ln 8'])
    ax.set_yticklabels(['ln 4', 'ln 8'])
    save(fig, 'box_counting')
    fig, axes = figure(1, 2, 4.5)
    fig.set_layout_engine('constrained', wspace=.02)
    axes[0, 0].set_anchor('E')
    axes[0, 1].set_anchor('W')
    geometries = binary_geometries()
    for ax, traces, length in zip(axes.flat, geometries, data['binary']['lengths_m']):
        for line in traces:
            ax.plot(*line.xy, color=BLUE, lw=2)
        ax.add_patch(Rectangle((0, 0), 100, 100, fill=False, ec=ORANGE, lw=2))
        ax.set(xlim=(-2, 102), ylim=(-2, 102), xlabel=t('x (m de modelo)', 'x (model m)'),
               ylabel=t('y (m de modelo)', 'y (model m)'), title=t(f'Conteo = 1; longitud = {length:g} m', f'Count = 1; length = {length:g} m'))
        ax.set_aspect('equal')
    save(fig, 'binary')
    fig, axes = figure(2, 2, 6)
    small, _ = synthetic_map()
    for line in small:
        axes[0, 0].plot(*line.xy, color=BLUE)
    axes[0, 0].set(xlabel=t('x (m de modelo)', 'x (model m)'), ylabel=t('y (m de modelo)', 'y (model m)'),
                   title=t('Once trazas, longitud fija', 'Eleven traces, fixed length'))
    axes[0, 0].set_aspect('equal')
    for q, ax in zip((0, 1, 2), [axes[0, 1], axes[1, 0], axes[1, 1]]):
        values = [row['dimensions'][q] for row in data['raster']['rows']]
        ax.bar(range(7), values, color=[ORANGE]+[BLUE]*6)
        ax.set(xticks=range(7), xticklabels=[t('Exacta', 'Exact'), '.5\n1', '.5\n3', '1\n1', '1\n3', '2\n1', '2\n3'],
               ylabel=f'D{q}', title=f'q = {q}', ylim=(0, 1.8),
               xlabel=t('Píxel (m) / grosor (px)', 'Pixel (m) / stroke (px)'))
        for i, v in enumerate(values):
            ax.text(i, v+.025, f'{v:.3f}', ha='center', fontsize=12)
    save(fig, 'raster')
    for name in ('rods', 'cantor'):
        result = data[name]
        classic, report = result['classic'], result['assessment']
        x = np.log(1/np.array(classic['scales_m']))
        y = np.log(classic['occupied_boxes'])
        fit = np.polyval(np.polyfit(x, y, 1), x)
        fig, axes = figure(2, 1, 5.5)
        ax, residual = axes[:, 0]
        ax.plot(x, y, 'o', ms=4, label=t('Conteos clásicos', 'Classic counts'))
        ax.plot(x, fit, label=f'D_BC = {classic["dimension"]:.6f}; R² = {classic["r2"]:.6f}')
        used = report['used_scales_m']
        ax.axvspan(np.log(1/max(used)), np.log(1/min(used)), color='#82ae94', alpha=.2,
                   label=t(f'MUSA: {len(used)} escalas retenidas', f'MUSA: {len(used)} retained scales'))
        residual.axhline(0, color='gray', lw=1)
        residual.plot(x, y-fit, 'o-', label=t('Residuo clásico', 'Classic residual'))
        if name == 'rods':
            row = report['q_results'][0]
            curves = [c for c in report['curves'] if c['q'] == 0]
            mean = np.array([np.mean([c['entropy'] for c in curves if c['scale_m'] == s]) for s in used])
            xm = np.log(1/np.array(used))
            ax.plot(xm, mean, '--', label=t('H0 medio: cuatro orígenes', 'Mean H0: four origins'))
            beta = row['models']['linear']['coefficients']
            residual.plot(xm, mean-np.polyval(beta[::-1], xm-row['x_center_log_inverse_scale']), 's--', ms=4,
                          label=t('Residuo MUSA', 'MUSA residual'))
            title = t('100 segmentos: MUSA no respaldado', '100 rods: MUSA not supported')
        else:
            residual.set_ylim(-.01, .01)
            title = t('Cantor finito: información insuficiente (4 < 8)', 'Finite Cantor: insufficient information (4 < 8)')
        ax.set(ylabel='ln N / H0', title=title)
        residual.set(xlabel=t('ln(1/ε) [ε en m de modelo]', 'ln(1/ε) [ε in model m]'), ylabel=t('Residuo', 'Residual'))
        ax.legend()
        residual.legend()
        save(fig, name)
    fig, axes = figure(1, 2, 4)
    fig.set_layout_engine('constrained', wspace=.16)
    grid = data['grids'][1]
    ax = axes[0, 0]
    for c in grid['cells']:
        patch = Rectangle((c['i']*1000, c['j']*1000), 1000, 1000,
                          fc=__import__('matplotlib').colormaps['YlOrRd'](c['length_m']/max(v['length_m'] for v in grid['cells'])), ec='white', lw=.5)
        patch.set_clip_path(Polygon(np.asarray(domain.exterior.coords), transform=ax.transData))
        ax.add_patch(patch)
    map_axes(ax)
    ax.set_title(t('Longitud por celda (ε = 1000 m)', 'Cell length (ε = 1000 m)'))
    fig.colorbar(ScalarMappable(norm=Normalize(0, max(c['length_m'] for c in grid['cells'])), cmap='YlOrRd'),
                 ax=ax, label=t('Longitud (m)', 'Length (m)'), shrink=.8)
    p = np.sort([c['length_m']/grid['total_length_m'] for c in grid['cells']])[::-1]
    ax = axes[0, 1]
    for q in (0, 1, 2):
        weights = p**q / sum(p**q)
        ax.plot(np.arange(1, len(p)+1), np.cumsum(weights), label=f'q = {q}', linestyle=('-', '--', ':')[q])
    ax.set(xlabel=t('Celdas de mayor a menor longitud', 'Cells from longest to shortest'),
           ylabel=t('Peso acumulado', 'Cumulative weight'), title=t('q concentra la atención', 'q focuses attention'))
    ax.legend()
    save(fig, 'mass')
    # Analytic four-quadrant multiplicative measure, clearly separated from the mapped network.
    probs = np.array([.1, .2, .25, .45])
    qs = np.linspace(0, 4, 41)
    mu = probs[None, :]**qs[:, None]
    mu /= mu.sum(axis=1)[:, None]
    alpha = -(mu*np.log(probs)).sum(axis=1)/np.log(2)
    spectrum = -(mu*np.log(mu)).sum(axis=1)/np.log(2)
    fig, axes = figure(1, 2, 3.5)
    ax = axes[0, 0]
    ax.bar(range(4), probs, color=BLUE)
    ax.set(xticks=range(4), xticklabels=['A', 'B', 'C', 'D'], ylabel=t('Fracción de medida', 'Measure fraction'),
           xlabel=t('Cuadrantes repetidos a cada nivel', 'Quadrants repeated at each level'), title=t('Cascada ideal', 'Ideal cascade'))
    ax = axes[0, 1]
    ax.plot(alpha, spectrum, color=BLUE)
    for i in (0, 10, 20, 40):
        ax.plot(alpha[i], spectrum[i], 'o', color=ORANGE)
        offset = (-8, -16) if i == 0 else (7, 8) if i == 40 else (5, -14)
        ax.annotate(f'q={qs[i]:g}', (alpha[i], spectrum[i]), xytext=offset, textcoords='offset points',
                    ha='right' if i == 0 else 'left', fontsize=12)
    ax.set(xlabel='α', ylabel='f(α)', title=t('Concentraciones que escalan distinto', 'Concentrations scaling differently'))
    save(fig, 'spectrum')
    return dict(q=qs.tolist(), alpha=alpha.tolist(), f=spectrum.tolist(), probabilities=probs.tolist())


def build(folder, render_only=False, refresh_maps=False):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    data = (json.loads((folder/'knowledge_narrative_measurements.json').read_text(encoding='utf-8'))
            if render_only else calculate())
    if refresh_maps:
        lines, domain, _ = fracture_network()
        data['maps'] = map_measurements(lines, domain)
    with rc_context({'font.size': 12, 'axes.titlesize': 12, 'legend.fontsize': 12}):
        for lang in ('es', 'en'):
            data['ideal_spectrum'] = render(folder, data, lang)
    (folder/'knowledge_narrative_measurements.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-only', action='store_true', help='Redraw from the saved numerical measurements')
    parser.add_argument('--refresh-maps', action='store_true', help='Resample maps only; preserve approved examples')
    args = parser.parse_args()
    build(Path(__file__).resolve().parents[1] / 'docs/images', render_only=args.render_only, refresh_maps=args.refresh_maps)
