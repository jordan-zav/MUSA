"""Deterministic three-family fracture teaching map in unlocated model metres.

Run: python scripts/tutorial_network.py --output outputs/fracture_example
The four-level spatial cascade is a synthetic sampling design, not a calibrated
geological process. Clipping changes the retained count from 900 proposals.
"""
from pathlib import Path
import argparse
import json

import numpy as np
from shapely.geometry import LineString, Polygon


def fracture_network():
    rng = np.random.default_rng(20261122)
    boundary = Polygon([(0, 800), (1800, 0), (8500, 300), (10000, 2300),
                        (9200, 8400), (7000, 10000), (1700, 9000)])
    lines, families = [], []
    for i in range(900):
        center, side = np.zeros(2), 10000.
        for _ in range(4):
            side /= 2
            quadrant = rng.choice(4, p=[.1, .2, .25, .45])
            center += side * np.array([quadrant % 2, quadrant // 2])
        center += rng.uniform(0, side, 2)
        angle = np.deg2rad((20, 80, 140)[i % 3] + rng.normal(0, 9))
        length = np.clip(150 * (1 + rng.pareto(1.3)), 150, 900)
        vector = length / 2 * np.array([np.cos(angle), np.sin(angle)])
        line = LineString([center - vector, center + vector]).intersection(boundary)
        if line.geom_type == 'LineString' and line.length > 5:
            lines.append(line)
            families.append(i % 3 + 1)
    return lines, boundary, families


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import geopandas as gpd
    from pyproj import CRS
    args.output.mkdir(parents=True, exist_ok=True)
    lines, boundary, families = fracture_network()
    crs = CRS.from_proj4('+proj=eqc +R=6371000 +units=m +no_defs +type=crs')
    crs = CRS.from_wkt(crs.to_wkt().replace('unknown', 'MUSA synthetic UNLOCATED model metres'))
    gpkg = args.output / 'inputs.gpkg'
    gpd.GeoDataFrame({'family': families}, geometry=lines, crs=crs).to_file(gpkg, layer='lineaments')
    gpd.GeoDataFrame(geometry=[boundary], crs=crs).to_file(gpkg, layer='boundary')
    (args.output / 'provenance.json').write_text(json.dumps(dict(seed=20261122, proposals=900,
        retained=len(lines), families=[20, 80, 140], angular_sd_degrees=9, cascade_levels=4,
        quadrant_probabilities=[.1, .2, .25, .45], pareto_shape=1.3,
        length_min_m=150, length_max_m=900, minimum_clipped_length_m=5,
        units='UNLOCATED model metres; synthetic, no field location'), indent=2), encoding='utf-8')
    print(gpkg)
