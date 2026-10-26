"""Known-dimension and multifractal controls for the open-boundary ensemble."""
from pathlib import Path
import argparse
import itertools
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import geopandas as gpd
import numpy as np
from shapely.geometry import LineString,box
from musa import MUSA,analyze_moving_windows

OFFSETS = [((x+.137)%1,(y+.271)%1) for x in (0,.25,.5,.75) for y in (0,.25,.5,.75)]
DIVISORS = [16,24,32,48,64,96,128]


def cantor(p=.5,levels=7):
    result=[]
    for bits in itertools.product((0,1),repeat=levels):
        start=sum(2*b*3.**(-k-1) for k,b in enumerate(bits))*1000
        probability=np.prod([p if b==0 else 1-p for b in bits])
        length=1000*3.**(-levels)*probability/max(p,1-p)**levels
        center=start+500*3.**(-levels)
        result.append(LineString([(center-length/2,500),(center+length/2,500)]))
    return result


def run(output):
    cases={'horizontal':[LineString([(0,500),(1000,500)])],
           'diagonal':[LineString([(0,0),(1000,1000)])],
           'oblique':[LineString([(0,150),(1000,850)])],
           'short_interior':[LineString([(250,500),(750,500)])],
           'cantor_uniform':cantor(), 'cantor_binomial':cantor(.7)}
    results=[]
    for name,lines in cases.items():
        a=MUSA(gpd.GeoDataFrame(geometry=lines,crs=26910),
            boundary=gpd.GeoDataFrame(geometry=[box(0,0,1000,1000)],crs=26910),q_values=[0,1,2])
        for phase in ((0,0),(.125,.125)):
            w,_,_=analyze_moving_windows(a,[1000],500,centers=[(500,500)],
                divisors=DIVISORS,origin_offsets=OFFSETS,grid_phase=phase)
            w=w.set_index('q')
            widths=np.asarray(json.loads(w.loc[0,'origin_alpha_json']))-np.asarray(json.loads(w.loc[2,'origin_alpha_json']))
            item=dict(case=name,phase=phase,dq0=w.loc[0,'dq'],dq2=w.loc[2,'dq'],
                alpha0=w.loc[0,'alpha'],alpha2=w.loc[2,'alpha'],H=w.loc[0,'alpha']-w.loc[2,'alpha'],
                H_origin_range=float(np.ptp(widths)),accepted=bool(w.accepted.all()))
            results.append(item)
            print(item,flush=True)
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'offsets':OFFSETS,'divisors':DIVISORS,'results':results},indent=2),encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
