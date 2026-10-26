"""Read-only reproducer for numerical audit findings; does not rewrite outputs."""
from pathlib import Path
import argparse
import json
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString, box

from musa import MUSA, analyze_moving_windows
from musa.proximity import analyze_fault_proximity
from musa.structural import compute_lineament_mother_structural_stats


def model(lines, boundary):
    return MUSA(gpd.GeoDataFrame(geometry=lines,crs=26910),
                boundary=gpd.GeoDataFrame(geometry=[boundary],crs=26910),q_values=[0,2])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gpkg',required=True)
    args=parser.parse_args()
    report={}
    line=LineString([(.2,.2),(1,.2),(1,1.8),(1.8,1.8)])
    measured=sum(MUSA._line_length_cells([line],1,np.array([0.,0.])).values())
    report['cell_boundary_mass']={'true_length':line.length,'assigned_length':measured,
                                  'relative_excess':measured/line.length-1}
    a=model([LineString([(0,500),(1000,500)])],box(0,0,1000,1000))
    report['uniform_line_phases']=[]
    for phase in [(0,0),(.5,.5)]:
        frame,_,_=analyze_moving_windows(a,[1000],500,centers=[(500,500)],grid_phase=phase)
        report['uniform_line_phases'].append({'phase':phase,'spectra':frame[
            ['q','dq','alpha','alpha_w','accepted','zeta_mean']].to_dict('records')})
    report['segmentation_proximity']=[]
    for split in [False,True]:
        lines=([LineString([(0,0),(1000,0)])] if not split else
               [LineString([(0,0),(500,0)]),LineString([(500,0),(1000,0)])])
        lines.append(LineString([(0,100),(1000,100)]))
        relations,_=analyze_fault_proximity(model(lines,box(-100,-100,1100,300)),[150])
        report['segmentation_proximity'].append({'split':split,'count':len(relations)})
    report['segmentation_orientation']=[]
    for lines in [[LineString([(100,100),(900,100),(900,900)])],
                  [LineString([(100,100),(900,100)]),LineString([(900,100),(900,900)])]]:
        row=compute_lineament_mother_structural_stats(lines,box(0,0,1000,1000),1000)[0]
        report['segmentation_orientation'].append({k:row[k] for k in
            ['measure_sum_m','mean_azimuth_deg','anisotropy_ratio','mean_resultant_length']})
    with sqlite3.connect(Path(args.gpkg).resolve().as_uri()+'?mode=ro',uri=True) as db:
        report['high_class_quality']=db.execute('SELECT quality_status_w,count(*) FROM trap_candidates WHERE evidence_class_w=3 GROUP BY quality_status_w').fetchall()
        report['high_class_support']=db.execute('SELECT evaluated_sizes_w,count(*) FROM trap_candidates WHERE evidence_class_w=3 GROUP BY evaluated_sizes_w').fetchall()
        hits=[]
        for cid,window,length,audit in db.execute('SELECT candidate_id,window_m,length_m,scale_diagnostics_json FROM candidate_centered_spectra WHERE q=0'):
            errors=[v['mass_m']/length-1 for v in json.loads(audit)] if length else []
            if any(abs(v)>1e-9 for v in errors):
                hits.append({'candidate_id':cid,'window_m':window,'maximum_excess':max(errors)})
        report['real_mass_discrepancies']=hits
    print(json.dumps(report,indent=2,default=str))


if __name__=='__main__':
    main()
