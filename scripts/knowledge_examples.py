"""Reproducible synthetic measurements used by Learn and the Python notebooks."""
import itertools

import numpy as np
from shapely.geometry import LineString, box

from musa import MUSA, classic_box_counting
from musa.partition import line_cell_segments
from musa.scaling import ScalingOptions, assess_lineament_scaling, renyi_entropy


def synthetic_map():
    """A sparse oblique network with a dense short-trace cluster, model metres."""
    lines = [LineString([(5.3, 7.1), (119.2, 107.6)]),
             LineString([(9.7, 112.2), (111.8, 23.4)]),
             LineString([(18.4, 14.1), (28.6, 100.7)])]
    lines += [LineString([(67.3, 52.2 + i * 1.7), (94.6, 57.1 + i * 1.7)]) for i in range(8)]
    return lines, box(0, 0, 128, 128)


def entropy_curve(masses):
    positive = np.asarray(masses, dtype=float)
    positive = positive[positive > 0]
    p = positive / positive.sum()
    return [renyi_entropy(p, q) for q in (0, 1, 2)]


def raster_comparison():
    """Pixel-centre binary ink, specified width in pixels, without antialiasing.

    Integer box/pixel ratios give identical origins and box sides in both paths.
    Ink mass is pixel area; a pixel intersecting several strokes is counted once.
    """
    from shapely import points, distance
    from shapely.ops import unary_union
    lines, domain = synthetic_map()
    scales = np.array([2., 4., 8., 16., 32.])
    exact, totals = [], []
    for scale in scales:
        masses = {}
        for key, length, _ in line_cell_segments(lines, scale, (0., 0.)):
            masses[key] = masses.get(key, 0.) + length
        exact.append(entropy_curve(list(masses.values())))
        totals.append(sum(masses.values()))
    x = np.log(1 / scales)
    def record(label, curves, **extra):
        return dict(label=label, entropies=np.asarray(curves).tolist(),
                    dimensions=np.polyfit(x, curves, 1)[0].tolist(), **extra)
    rows = [record('Exact length', exact, total_lengths=totals)]
    union = unary_union(lines)
    for pixel in (.5, 1., 2.):
        n = int(128 / pixel)
        xx, yy = np.meshgrid((np.arange(n) + .5) * pixel, (np.arange(n) + .5) * pixel)
        distances = distance(points(xx, yy), union)
        for width in (1, 3):
            ink = distances <= pixel * width / 2
            curves = []
            for scale in scales:
                k = int(round(scale / pixel))
                mass = ink.reshape(n // k, k, n // k, k).sum(axis=(1, 3)) * pixel**2
                curves.append(entropy_curve(mass.ravel()))
            rows.append(record(f'{pixel:g} m/px; {width} px', curves, pixel_m=pixel,
                               width_px=width, ink_area_m2=float(ink.sum() * pixel**2)))
    return dict(scales_m=scales.tolist(), q=[0, 1, 2], rows=rows,
                total_geometric_length=sum(line.length for line in lines),
                lines=[list(line.coords) for line in lines], domain=list(domain.bounds),
                method='Binary pixel-centre distance <= width/2; no antialiasing; origin (0,0).')


def finite_cantor():
    side, levels = 10000., 7
    lines = []
    for bits in itertools.product((0, 1), repeat=levels):
        start = side * sum(2 * b * 3. ** (-k - 1) for k, b in enumerate(bits))
        length = side * 3. ** (-levels)
        lines.append(LineString([(start, side / 2), (start + length, side / 2)]))
    analyzer = MUSA.from_line_geometries(lines, box(0, 0, side, side), 'EPSG:32718', q_values=[0, 1, 2])
    scales = side / 3. ** np.arange(2, 6)
    classic = classic_box_counting(analyzer, scales)
    assessment = assess_lineament_scaling(analyzer, scales, ScalingOptions(.01))
    return dict(classic=classic, assessment=assessment, levels=levels, trace_count=len(lines))


def random_rods():
    """Fixed 100-rod control selected after the recorded periodic/rod search."""
    rng = np.random.default_rng(42)
    centers = rng.uniform(1000, 9000, (100, 2))
    angles = rng.uniform(0, np.pi, 100)
    vectors = 500 * np.column_stack([np.cos(angles), np.sin(angles)])
    lines = [LineString([center-vector, center+vector]) for center, vector in zip(centers, vectors)]
    model = MUSA.from_line_geometries(lines, box(0, 0, 10000, 10000), 'EPSG:32718', q_values=[0, 1, 2])
    scales = np.geomspace(50, 2000, 24)
    return dict(classic=classic_box_counting(model, scales),
                assessment=assess_lineament_scaling(model, scales, ScalingOptions(1, renyi_order_policy='inform_q0_q2')),
                seed=42, trace_count=100, length_m=1000, centers_bounds_m=[1000, 9000],
                orientation='uniform [0, pi)', domain_side_m=10000)
