"""Reproducible finite-window grid controls, without changing published data."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, box
from musa import MUSA, analyze_moving_windows


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cases = {
        'horizontal': [(0,500),(1000,500)],
        'diagonal': [(0,0),(1000,1000)],
        'oblique': [(0,150),(1000,850)],
        'short_interior': [(250,500),(750,500)],
    }
    ranges = {'coarse': [2,4,8,16], 'intermediate': [8,12,16,24,32,48,64],
              'fine': [16,24,32,48,64,96,128]}
    offsets = np.array([(0,0),(.5,0),(0,.5),(.5,.5)])
    rows = []
    for name, coords in cases.items():
        a = MUSA(gpd.GeoDataFrame(geometry=[LineString(coords)],crs=26910),
                 boundary=gpd.GeoDataFrame(geometry=[box(0,0,1000,1000)],crs=26910),q_values=[0,2])
        for range_name, divisors in ranges.items():
            for shift in (0.,.25):
                spectra = []
                for phase in (offsets+shift)%1:
                    w,_,_ = analyze_moving_windows(a,[1000],500,divisors=divisors,
                        centers=[(500,500)],grid_phase=phase)
                    spectra.append(w.set_index('q')[['dq','alpha','alpha_w']])
                # Same scales and unweighted fits: feature averaging and slope
                # averaging are equivalent; this pilot does not alter weights.
                mean = sum(spectra)/len(spectra)
                rows.append(dict(case=name, scale_range=range_name, offset=shift,
                    dq0=float(mean.loc[0,'dq']),dq2=float(mean.loc[2,'dq']),
                    H=float(mean.loc[0,'alpha']-mean.loc[2,'alpha']),
                    H_w=float(mean.loc[0,'alpha_w']-mean.loc[2,'alpha_w'])))
            print(name,range_name,rows[-2:],flush=True)
    rows=[{k:(None if isinstance(v,float) and not np.isfinite(v) else v) for k,v in row.items()} for row in rows]
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(rows,indent=2,allow_nan=False),encoding='utf-8')


if __name__ == '__main__':
    run()
