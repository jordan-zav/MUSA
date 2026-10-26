"""Overlapping spatial supports; structural descriptors, not permeability estimates."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.special import logsumexp
from scipy.stats import linregress

from .network import _iter_line_parts

# Defined with synthetic controls. Offsets avoid giving special weight to
# exactly aligned edges; the second bank is shifted by one eighth of a box.
ENSEMBLE_OFFSETS = [((x+.137)%1,(y+.271)%1)
                    for x in (0.,.25,.5,.75) for y in (0.,.25,.5,.75)]
ENSEMBLE_DIVISORS = [16,24,32,48,64,96,128]


def fracture_nodes(lines, boundary):
    """Exact planar topology. Degree counts branches, not intersecting line pairs.

    Unary union removes coincident traces and splits at exact intersections.
    No snapping: cartographic near misses remain disconnected.
    """
    from shapely.geometry import Point
    from shapely.ops import unary_union

    parts = list(_iter_line_parts(unary_union(lines)))
    degrees = Counter()
    directions = {}
    for line in parts:
        degrees[tuple(line.coords[0][:2])] += 1
        degrees[tuple(line.coords[-1][:2])] += 1
        for coords in (list(line.coords), list(line.coords)[::-1]):
            xy = tuple(coords[0][:2])
            other = next((p for p in coords[1:] if tuple(p[:2]) != xy), None)
            if other is not None:
                angle = float(np.degrees(np.arctan2(other[0]-xy[0], other[1]-xy[1])) % 180)
                directions.setdefault(xy, []).append(angle)
    tolerance = max(np.sqrt(boundary.area) * 1e-10, 1e-8)
    def angle_details(xy):
        axes = []
        for angle in sorted(directions.get(xy, [])):
            if not any(min(abs(angle-a), 180-abs(angle-a)) < 1e-7 for a in axes):
                axes.append(angle)
        pairs = [{'axis_a': i, 'axis_b': j, 'angle_deg': min(abs(a-b), 180-abs(a-b))}
                 for i, a in enumerate(axes) for j, b in enumerate(axes) if j > i]
        values = [p['angle_deg'] for p in pairs]
        return {'intersection_angles_json': json.dumps(pairs),
                'intersection_angle_min_deg': min(values) if values else np.nan,
                'intersection_angle_max_deg': max(values) if values else np.nan,
                'angle_basis': 'unique_local_axial_tangents_not_geological_fault_ids'}
    return [
        {"node_id": i, "degree": degree,
         "kind": "I" if degree == 1 else "Y" if degree == 3 else "X" if degree == 4 else "complex",
         "boundary_node": bool(boundary.boundary.distance(Point(xy)) <= tolerance),
         "max_branch_angle_deg": max((min(abs(a-b), 180-abs(a-b)) for a in directions.get(xy, []) for b in directions.get(xy, [])), default=0.0),
         **angle_details(xy),
         "geometry": Point(xy)}
        for i, (xy, degree) in enumerate(sorted(degrees.items())) if degree != 2
    ]


def _fit(x, y):
    if np.ptp(y) < 1e-12:
        return 0.0, 0.0  # constant features do not provide scaling evidence
    fit = linregress(x, y)
    return float(fit.slope), float(fit.rvalue**2)


def analyze_moving_windows(
    analyzer, window_sizes_m, step_m, *, divisors=(2, 4, 8, 16),
    q_values=None, min_coverage=0.8, min_r2=0.9, min_effective_boxes=2.0,
    max_windows=10000, centers=None, grid_phase=(0.0, 0.0), origin_offsets=None, workers=1,
    zeta_exponents=(1., 1., 1., 1.), zeta_scale_floor=0.25, reliable_min_zeta=0.15,
):
    """Return (window GeoDataFrame, unique-node GeoDataFrame, configuration).

    Window sides L, common center spacing h and internal sizes L/divisor are
    separate. Centers may also be explicit projected (x,y) locations. Windows
    retain actual clipped supports and rejected estimates with reason flags.
    """
    import geopandas as gpd
    from shapely.geometry import Point, box
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    if analyzer._kind != "lines":
        raise ValueError("Moving windows require GIS lines and a polygon boundary.")
    crs = analyzer._active_crs
    if not crs or not crs.is_projected or any(abs(a.unit_conversion_factor - 1) > 1e-9 for a in crs.axis_info[:2]):
        raise ValueError("Moving windows require a projected CRS in metres.")
    sizes = np.unique(np.asarray(window_sizes_m, dtype=float))
    div = np.unique(np.asarray(divisors, dtype=float))
    qs = np.unique(np.asarray(analyzer.q_values if q_values is None else q_values, dtype=float))
    phase = np.asarray(grid_phase, dtype=float)
    if phase.shape != (2,) or not np.isfinite(phase).all() or (phase < 0).any() or (phase >= 1).any():
        raise ValueError('Grid phase must contain two fractions in [0,1).')
    offsets = np.asarray([(0.,0.)] if origin_offsets is None else origin_offsets,dtype=float)
    if offsets.ndim != 2 or offsets.shape[1] != 2 or not 1 <= len(offsets) <= 64 or not np.isfinite(offsets).all() or (offsets < 0).any() or (offsets >= 1).any():
        raise ValueError('Origin offsets must be 1 to 64 pairs in [0,1).')
    if len(np.unique(offsets,axis=0)) != len(offsets):
        raise ValueError('Duplicate origin offsets would overweight a grid.')
    phases = (offsets+phase)%1

    if not sizes.size or not np.all(np.isfinite(sizes)) or np.any(sizes <= 0):
        raise ValueError("Window sizes must be positive and finite.")
    if div.size < 4 or not np.all(np.isfinite(div)) or np.any(div < 2) or np.any(div != np.floor(div)):
        raise ValueError("Use at least four distinct integer divisors >= 2.")
    if not qs.size or not np.all(np.isfinite(qs)) or np.max(np.abs(qs)) > 100:
        raise ValueError("q must be finite and between -100 and 100.")
    if not np.isfinite(step_m) or step_m <= 0:
        raise ValueError("Step must be positive and finite.")
    if not 0 < min_coverage <= 1 or not 0 <= min_r2 < 1 or not np.isfinite(min_effective_boxes) or min_effective_boxes < 1:
        raise ValueError("Invalid coverage, R2 or effective-box threshold.")
    if not isinstance(max_windows, int) or max_windows < 1:
        raise ValueError("max_windows must be a positive integer.")
    zeta_exponents = analyzer._normalize_zeta_exponents(zeta_exponents)
    if not np.isfinite(zeta_scale_floor) or not 0 <= zeta_scale_floor <= 1 or not np.isfinite(reliable_min_zeta) or reliable_min_zeta < 0:
        raise ValueError("Invalid zeta floor or reliability threshold.")
    boundary = analyzer._boundary_geom
    lines = list(_iter_line_parts(unary_union(analyzer._line_geometries)))
    tree = STRtree(lines)
    nodes = fracture_nodes(lines, boundary)
    node_gdf = gpd.GeoDataFrame(nodes, columns=["node_id", "degree", "kind", "boundary_node", "max_branch_angle_deg", "intersection_angles_json", "intersection_angle_min_deg", "intersection_angle_max_deg", "angle_basis", "geometry"], geometry="geometry", crs=crs)
    if centers is None:
        x0, y0, x1, y1 = boundary.bounds
        nx, ny = max(1, int(np.ceil((x1-x0)/step_m))), max(1, int(np.ceil((y1-y0)/step_m)))
        if nx * ny * len(sizes) > max_windows:
            raise ValueError("Too many windows; increase step or max_windows explicitly.")
        centers = [(x0+(i+0.5)*step_m, y0+(j+0.5)*step_m) for i in range(nx) for j in range(ny)]
    else:
        centers = list(centers)
    coords = np.asarray(centers, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 2 or not np.all(np.isfinite(coords)) or len(coords)*len(sizes) > max_windows:
        raise ValueError("Invalid centers or window limit exceeded.")
    if not isinstance(workers,int) or not 1 <= workers <= 16:
        raise ValueError('Workers must be an integer from 1 to 16.')
    if workers > 1 and len(coords) > 1:
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing
        import pandas as pd
        options=dict(divisors=div,q_values=qs,min_coverage=min_coverage,min_r2=min_r2,
            min_effective_boxes=min_effective_boxes,max_windows=max_windows,grid_phase=phase,
            origin_offsets=offsets,zeta_exponents=zeta_exponents,zeta_scale_floor=zeta_scale_floor,
            reliable_min_zeta=reliable_min_zeta,workers=1)
        inside=np.array([i for i,(cx,cy) in enumerate(coords) if boundary.covers(Point(cx,cy))],dtype=int)
        if not len(inside):
            raise ValueError('No window centers inside the boundary; reduce step or supply centers.')
        chunks=np.array_split(inside,min(len(inside),workers*4))
        tasks=[(analyzer,sizes,step_m,coords[ids].tolist(),ids.tolist(),options) for ids in chunks]
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
            batches=list(pool.map(_window_chunk,tasks))
        windows=gpd.GeoDataFrame(pd.concat([frame for frame,_ in batches],ignore_index=True),crs=crs)
        configuration=batches[0][1]
        configuration.update(centers=coords.tolist(),workers=workers)
        return windows,node_gdf,configuration
    rows = []
    for center_id, (cx, cy) in enumerate(coords):
        if not boundary.covers(Point(cx, cy)):
            continue
        for size in sizes:
            xmin, ymin = cx-size/2, cy-size/2
            support = box(xmin, ymin, cx+size/2, cy+size/2).intersection(boundary)
            area = support.area
            coverage = area / size**2
            clipped = [part for idx in tree.query(support, predicate="intersects")
                       for part in _iter_line_parts(lines[int(idx)].intersection(support)) if part.length > 0]
            length = sum(line.length for line in clipped)
            local_nodes = [n for n in nodes if not n["boundary_node"] and n["degree"] >= 3 and support.contains(n["geometry"])]
            base = {"center_id": center_id, "center_x": cx, "center_y": cy,
                    "window_m": float(size), "area_m2": area, "coverage": coverage,
                    "length_m": length, "density_m_per_km2": length/area*1e6 if area else np.nan,
                    "junction_count": len(local_nodes),
                    "junction_density_per_km2": len(local_nodes)/area*1e6 if area else np.nan,
                    "geometry": support}
            probabilities, mass_totals = [], []
            scales = size/div
            zeta_values, scale_details = [], []
            from .mass_partition import primitive_arrays, bounded_mass_values
            starts, ends = primitive_arrays(clipped)
            for index, eps in enumerate(scales if length and coverage >= min_coverage else []):
                phase_probabilities, origin_details = [], []
                for current_phase in phases:
                    origin = np.array([xmin,ymin])+current_phase*eps
                    upper = np.ceil(size/eps-current_phase).astype(int)-1
                    mass = bounded_mass_values(starts,ends,float(eps),float(origin[0]),float(origin[1]),int(upper[0]),int(upper[1]))
                    total = float(mass.sum())
                    if not np.isclose(total,length,rtol=1e-9,atol=1e-8):
                        raise ValueError('Length conservation failed in origin ensemble.')
                    prob = mass/total if mass.size else mass
                    phase_probabilities.append(prob)
                    entropy = float(-np.sum(prob*np.log(prob))) if prob.size else 0.
                    possible = int(np.prod(div[index]+(current_phase > 0).astype(int)))
                    zeta = analyzer._zeta_mother_scale(float(size),float(eps),float(scales[0]),
                        float(scales[-1]),total,length,len(prob),entropy,zeta_exponents,
                        zeta_scale_floor,possible_boxes=possible)
                    origin_details.append(dict(phase=current_phase.tolist(),occupied_boxes=len(prob),
                        possible_boxes=possible,mass_m=total,occupancy=len(prob)/possible,
                        entropy=entropy,effective_ratio=float(np.exp(entropy)/len(prob)) if len(prob) else 0.,zeta=zeta))
                probabilities.append(phase_probabilities)
                mass_totals.append(float(np.mean([d['mass_m'] for d in origin_details])))
                average = {key:float(np.mean([d[key] for d in origin_details])) for key in
                           ('occupied_boxes','possible_boxes','mass_m','occupancy','entropy','effective_ratio','zeta')}
                zeta_values.append(average['zeta'])
                scale_details.append(dict(eps_m=float(eps),mass_ratio=average['mass_m']/length,
                                          origin_details=origin_details,**average))
            for q in qs:
                row = dict(base, q=float(q), dq=np.nan, alpha=np.nan, f_alpha=np.nan,
                           dq_r2=np.nan, alpha_r2=np.nan, f_alpha_r2=np.nan,
                           min_effective_boxes=np.nan, max_box_weight=np.nan,
                           accepted=False, reason="insufficient_support",
                           dq_w=np.nan, alpha_w=np.nan, f_alpha_w=np.nan,
                           dq_w_r2=np.nan, alpha_w_r2=np.nan, f_alpha_w_r2=np.nan,
                           zeta_mean=float(np.mean(zeta_values)) if zeta_values else np.nan,
                           zeta_min=float(min(zeta_values)) if zeta_values else np.nan,
                           weighted_scales=sum(v > 0 for v in zeta_values),
                           accepted_w=False, reliable_w=False, reason_w="insufficient_support",
                           origin_alpha_json="[]", origin_alpha_w_json="[]",
                           origin_count=len(phases), scale_diagnostics_json="[]")
                if coverage < min_coverage:
                    row["reason"] = "low_coverage"
                    row["reason_w"] = "low_coverage"
                elif len(probabilities) == len(scales) and all(len(p) >= 2 for bank in probabilities for p in bank):
                    features, alphas, fs, neff, dominant = [], [], [], [], []
                    origin_alphas = []
                    for bank in probabilities:
                        bank_features, bank_alphas, bank_fs = [], [], []
                        for p in bank:
                            logp = np.log(p)
                            logmu = q*logp-logsumexp(q*logp)
                            mu = np.exp(logmu)
                            bank_features.append(-np.sum(p*logp) if np.isclose(q,1) else -logsumexp(q*logp)/(q-1))
                            bank_alphas.append(float(np.sum(mu*logp)))
                            bank_fs.append(float(np.sum(mu*logmu)))
                            neff.append(float(1/np.sum(mu**2)))
                            dominant.append(float(mu.max()))
                        features.append(float(np.mean(bank_features)))
                        alphas.append(float(np.mean(bank_alphas)))
                        fs.append(float(np.mean(bank_fs)))
                        origin_alphas.append(bank_alphas)
                    # These are correlated origin diagnostics, never independent
                    # samples for a standard error. Common weights preserve the
                    # equality between the average slope and fitted mean features.
                    x = np.log(scales)
                    for weights,field in ((np.ones(len(scales)), 'origin_alpha_json'),
                                          (np.asarray(zeta_values), 'origin_alpha_w_json')):
                        dx = x-np.average(x,weights=weights) if weights.sum() else x-x.mean()
                        denominator = np.sum(weights*dx*dx)
                        slopes = (weights*dx)@np.asarray(origin_alphas)/denominator if denominator > 0 else np.full(len(phases),np.nan)
                        row[field] = json.dumps([float(v) if np.isfinite(v) else None for v in slopes])
                    row["dq"], row["dq_r2"] = _fit(np.log(1/scales), features)
                    row["alpha"], row["alpha_r2"] = _fit(np.log(scales), alphas)
                    row["f_alpha"], row["f_alpha_r2"] = _fit(np.log(scales), fs)
                    for name, x, values in (("dq", np.log(1/scales), features),
                                            ("alpha", np.log(scales), alphas),
                                            ("f_alpha", np.log(scales), fs)):
                        row[name+"_w"], row[name+"_w_r2"] = analyzer._weighted_regression_slope_r2(x, values, zeta_values)
                    row['scale_diagnostics_json'] = json.dumps([
                        dict(d, dq_feature=features[i], alpha_feature=alphas[i], f_feature=fs[i])
                        for i,d in enumerate(scale_details)], allow_nan=False)
                    row["min_effective_boxes"] = min(neff)
                    row["max_box_weight"] = max(dominant)
                    good_fit = min(row[k] for k in ("dq_r2", "alpha_r2", "f_alpha_r2")) >= min_r2
                    enough_boxes = min(neff) >= min_effective_boxes
                    row["accepted"] = bool(good_fit and enough_boxes)
                    row["reason"] = "accepted" if row["accepted"] else "dominant_box" if not enough_boxes else "poor_scaling"
                    weighted_fit = all(np.isfinite(row[k]) and row[k] >= min_r2
                                       for k in ('dq_w_r2', 'alpha_w_r2', 'f_alpha_w_r2'))
                    row['accepted_w'] = bool(weighted_fit and enough_boxes and row['weighted_scales'] >= 3)
                    row['reliable_w'] = bool(row['accepted_w'] and row['zeta_mean'] >= reliable_min_zeta)
                    row['reason_w'] = ('accepted' if row['accepted_w'] else 'insufficient_weighted_scales'
                                       if row['weighted_scales'] < 3 else 'dominant_box'
                                       if not enough_boxes else 'poor_scaling')
                rows.append(row)
    if not rows:
        raise ValueError("No window centers inside the boundary; reduce step or supply centers.")
    windows = gpd.GeoDataFrame(rows, geometry="geometry", crs=crs)
    windows["accepted_window_sizes"] = windows.groupby(["center_id", "q"])["accepted"].transform("sum")
    config = {"method": "moving-window Chhabra-Jensen", "window_sizes_m": sizes.tolist(),
              "step_m": float(step_m), "divisors": div.tolist(), "q_values": qs.tolist(), "grid_phase": phase.tolist(), "origin_offsets": offsets.tolist(),
              "origin_aggregation": "equal mean of per-origin entropy/CJ features before fitting; mean per-origin zeta per scale; no periodic boundaries",
              "min_coverage": min_coverage, "min_r2": min_r2, "min_effective_boxes": min_effective_boxes,
              "zeta_exponents": list(zeta_exponents), "zeta_scale_floor": zeta_scale_floor,
              "reliable_min_zeta": reliable_min_zeta,
              "zeta_method": "same MUSA four-factor weight per support/scale; shifted nominal box count corrected; mass conserved",
              "crs": str(crs), "centers": coords.tolist(), "max_windows": max_windows, "workers": workers,
              "measure": "unique planar line length; coincident traces dissolved",
              "topology": "exact intersections; no snapping; AOI boundary nodes excluded from window counts",
              "interpretation": "structural concentration and junctions, not measured permeability",
              "uncertainty": "overlapping windows are dependent; accepted-size count is not anomaly persistence"}
    return windows, node_gdf, config


def _window_chunk(task):
    analyzer,sizes,step,centers,ids,options=task
    frame,_,config=analyze_moving_windows(analyzer,sizes,step,centers=centers,**options)
    frame['center_id']=frame.center_id.map(dict(enumerate(ids)))
    return frame,config


def export_moving_windows(analyzer, output_dir, window_sizes_m, step_m, *, export_gis=True, proximity_radii_m=None, evidence_settings=None, progress=None, **kwargs):
    if progress: progress('Fondo: primer conjunto de origenes.')
    windows, nodes, config = analyze_moving_windows(analyzer, window_sizes_m, step_m, **kwargs)
    nodes["role"] = np.where(nodes.boundary_node, "boundary_control", np.where(nodes.degree >= 3, "structural_candidate", "endpoint_control"))
    nodes["interpretation"] = "planar_geometry_not_validated_prospectivity"
    # Context refers to intersecting windows, never a node-level multifractal score.
    contexts = []
    for point in nodes.geometry:
        local = windows.loc[windows.geometry.contains(point)]
        q2 = local.loc[np.isclose(local.q, 2)]
        good = q2.loc[q2.accepted]
        contexts.append({"context_windows_q2": len(q2), "accepted_context_q2": len(good),
                         "accepted_sizes_q2": int(good.window_m.nunique()),
                         "context_status_q2": "not_evaluated" if q2.empty else "accepted_context" if len(good) else "no_accepted_context"})
    for field in ("context_windows_q2", "accepted_context_q2", "accepted_sizes_q2", "context_status_q2"):
        nodes[field] = [row[field] for row in contexts]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    proximity = None
    if proximity_radii_m is not None:
        from .proximity import analyze_fault_proximity
        proximity = analyze_fault_proximity(analyzer, proximity_radii_m)
        proximity[0].drop(columns='geometry').to_csv(out / 'potential_relations.csv', index=False)
        config['proximity_radii_m'] = sorted(set(float(r) for r in proximity_radii_m))
        config['proximity_interpretation'] = 'Disjoint endpoint-merged degree-two chains; nearest approach only; no snapping or inferred connectivity. Zones are midpoint search buffers at first matching radius, not damage zones.'
    from .candidates import evaluate_candidates
    (traps, diagnostics, scoring), centered, shifted, shifted_background = evaluate_candidates(
        analyzer, nodes, windows, proximity[0] if proximity is not None else None, config, evidence_settings, progress)
    import pandas as pd
    pd.DataFrame(diagnostics).to_csv(out / 'candidate_evidence.csv', index=False)
    from .structural_orders import attach_structural_orders
    traps = attach_structural_orders(traps, analyzer, proximity[0] if proximity is not None else None)
    scoring['structural_orders'] = 'User-interpreted order priority, independent of relative multifractal score. Ambiguous or missing orders have null priority; no perpendicularity bonus.'
    traps.drop(columns='geometry').to_csv(out / 'trap_candidates.csv', index=False)
    (out / 'candidate_scoring.json').write_text(json.dumps(scoring, indent=2), encoding='utf-8')
    config['candidate_scoring'] = scoring
    csv = out / "moving_windows.csv"
    windows.drop(columns="geometry").to_csv(csv, index=False)
    node_csv = out / "moving_nodes.csv"
    tab = nodes.drop(columns="geometry").copy()
    tab["x"] = nodes.geometry.x
    tab["y"] = nodes.geometry.y
    tab.to_csv(node_csv, index=False)
    metadata = out / "moving_windows_config.json"
    metadata.write_text(json.dumps(config, indent=2), encoding="utf-8")
    outputs = {"moving_windows": str(csv), "moving_nodes": str(node_csv), "moving_config": str(metadata)}
    outputs['trap_candidates'] = str(out / 'trap_candidates.csv')
    outputs['candidate_scoring'] = str(out / 'candidate_scoring.json')
    outputs['candidate_evidence'] = str(out / 'candidate_evidence.csv')
    if proximity is not None:
        outputs['potential_relations'] = str(out / 'potential_relations.csv')
    if export_gis:
        path = out / "musa_moving_windows.gpkg"
        if path.exists():
            path.unlink()
        windows.to_file(path, layer="window_spectra", driver="GPKG")
        if shifted_background is not None:
            shifted_background.to_file(path,layer="window_shifted_spectra",driver="GPKG")
        candidates = nodes.loc[nodes.role == "structural_candidate"]
        controls = nodes.loc[nodes.role != "structural_candidate"]
        candidates.to_file(path, layer="structural_candidates", driver="GPKG")
        controls.to_file(path, layer="topology_controls", driver="GPKG")
        traps.to_file(path, layer='trap_candidates', driver='GPKG')
        if centered is not None:
            centered.to_file(path, layer='candidate_centered_spectra', driver='GPKG')
            shifted.to_file(path, layer='candidate_shifted_spectra', driver='GPKG')
        if proximity is not None:
            proximity[0].to_file(path, layer='potential_relations', driver='GPKG')
            proximity[1].to_file(path, layer='interaction_search_zones', driver='GPKG')
        from .gis_styles import embed_styles
        embed_styles(path)
        from .node_classes import export_products
        export_products(path)
        import sqlite3
        with sqlite3.connect(path) as db:
            if diagnostics:
                pd.DataFrame(diagnostics).to_sql('candidate_evidence', db, index=False, if_exists='replace')
            pd.DataFrame([{'configuration_json': json.dumps(scoring)}]).to_sql('candidate_scoring', db, index=False, if_exists='replace')
        outputs["moving_gis"] = str(path)
    return outputs
