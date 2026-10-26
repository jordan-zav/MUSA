"""Candidate-centered multifractal contrast: no automatic structural bonuses."""
import json
import numpy as np


def candidate_seeds(nodes, relations=None):
    import geopandas as gpd
    seeds = []
    for row in nodes.loc[(nodes.degree >= 3) & (~nodes.boundary_node)].itertuples():
        seeds.append(dict(candidate_id=f'node_{row.node_id}', source_layer='structural_candidates',
                          source_id=int(row.node_id), candidate_type='exact_'+row.kind,
                          gap_m=0.0, degree=int(row.degree), angle_deg=row.intersection_angle_min_deg,
                          angle_kind='intersection', angle_pairs_json=row.intersection_angles_json,
                          geometry=row.geometry))
    if relations is not None:
        for row in relations.itertuples():
            seeds.append(dict(candidate_id=f'relation_{row.relation_id}', source_layer='potential_relations',
                              source_id=int(row.relation_id), candidate_type=row.relation_type,
                              gap_m=row.gap_m, degree=np.nan, angle_deg=row.axial_angle_deg,
                              angle_kind='nearby_traces_not_intersection', angle_pairs_json='[]',
                              geometry=row.geometry.interpolate(.5, normalized=True)))
    columns = list(seeds[0]) if seeds else ['candidate_id', 'source_layer', 'source_id', 'candidate_type', 'geometry']
    return gpd.GeoDataFrame(seeds, columns=columns, geometry='geometry', crs=nodes.crs)


DEFAULT_EVIDENCE = {
    'min_reference_windows': 20, 'density_match_factor': 2.0,
    'class_2_above_percentile': 0.50, 'class_3_above_percentile': 0.80,
    'max_phase_difference': 0.05,
}


def _spectral_table(windows):
    """Join q=0 and q=2 on the SAME support; retain rejected supports."""
    keys = ['center_id', 'window_m']
    a = windows.loc[np.isclose(windows.q, 0)].set_index(keys)
    b = windows.loc[np.isclose(windows.q, 2)].set_index(keys)
    result = a[['center_x', 'center_y', 'density_m_per_km2', 'coverage', 'geometry']].copy()
    result['width'] = a.alpha-b.alpha.reindex(a.index)
    result['usable'] = (a.accepted & b.accepted.reindex(a.index).fillna(False)
                        & np.isfinite(result.width) & (result.width >= -1e-8))
    result.loc[result.width.between(-1e-8, 0), 'width'] = 0.0
    fit_ok=(a.accepted & b.accepted.reindex(a.index).fillna(False)).astype(bool)
    result['support_reason']=np.where(~fit_ok,'rejected_scaling',
        np.where(~np.isfinite(result.width),'nonfinite_spectrum',
                 np.where(result.width < -1e-8,'negative_spectral_width','usable')))
    if 'reason' in a and 'reason' in b:
        coverage=a.reason.eq('low_coverage') | b.reason.reindex(a.index).eq('low_coverage')
        result.loc[coverage,'support_reason']='low_coverage'

    result['origin_width_range'] = np.nan
    if 'origin_alpha_json' in a and 'origin_alpha_json' in b:
        spread=[]
        for aa,bb in zip(a.origin_alpha_json,b.reindex(a.index).origin_alpha_json):
            av=np.asarray(json.loads(aa),dtype=float)
            bv=np.asarray(json.loads(bb),dtype=float) if isinstance(bb,str) else np.array([])
            spread.append(float(np.ptp(av-bv)) if len(av) and len(av)==len(bv) and np.isfinite(av-bv).all() else np.nan)
        result['origin_width_range']=spread
    return result.reset_index()


def classify_candidate_evidence(seeds, background, centered, shifted, sizes, settings=None, shifted_background=None):
    """Descriptive background-relative classes, with computational quality separate.

    The primary and background spectra use the SAME grid convention. The shifted
    grid diagnoses sensitivity without replacing the primary rank by a minimum.
    These
    ranks describe finite-scale heterogeneity, not prospectivity or confidence.
    Supported classes additionally require complete, resolved two-phase support.
    """
    import geopandas as gpd
    import pandas as pd
    cfg = dict(DEFAULT_EVIDENCE)
    if settings:
        unknown = set(settings)-set(cfg)
        if unknown:
            raise ValueError(f'Unknown evidence settings: {sorted(unknown)}')
        cfg.update(settings)
    if (not all(np.isfinite(v) for v in cfg.values())
            or cfg['min_reference_windows'] < 2
            or cfg['min_reference_windows'] != int(cfg['min_reference_windows'])
            or cfg['density_match_factor'] < 1
            or not 0 < cfg['class_2_above_percentile'] < cfg['class_3_above_percentile'] < 1
            or cfg['max_phase_difference'] < 0):
        raise ValueError('Invalid evidence settings.')
    sizes = sorted(set(float(v) for v in sizes))
    if not sizes or not all(np.isfinite(v) and v > 0 for v in sizes):
        raise ValueError('Window sizes must be positive and finite.')
    bg, primary, alternate = map(_spectral_table, (background, centered, shifted))
    if shifted_background is not None:
        alternate_reference = _spectral_table(shifted_background)
        bg = bg.merge(alternate_reference[['center_id','window_m','width','usable']],
                      on=['center_id','window_m'],how='left',suffixes=('','_alternate'),validate='one_to_one')
    primary = primary.set_index(['center_id', 'window_m'])
    alternate = alternate.set_index(['center_id', 'window_m'])
    rows, details = [], []
    for center_id, seed in enumerate(seeds.to_dict('records')):
        percentiles, stable, sensitive, unknown_phase = [], 0, 0, 0
        contrasts = []
        phase_errors = []
        origin_ranges = []
        for size in sizes:
            key = (center_id, size)
            d = {'candidate_id': seed['candidate_id'], 'window_m': size,
                 'search_halfwidth_m': size/2, 'reason': 'insufficient_support',
                 'alpha_width': None, 'shifted_alpha_width': None, 'phase_difference': None,
                 'phase_status': 'not_evaluated', 'reference_count': 0,
                 'reference_center_ids': '', 'background_median': None,
                 'contrast': None, 'empirical_percentile': None, 'size_class': None,
                 'alternate_background_median': None, 'background_phase_difference': None,
                 'alternate_percentile': None, 'alternate_size_class': None, 'origin_width_range': None}
            if key not in primary.index:
                details.append(d)
                continue
            p = primary.loc[key]
            d['alpha_width'] = float(p.width) if np.isfinite(p.width) else None
            d['origin_width_range'] = float(p.origin_width_range) if np.isfinite(p.origin_width_range) else None
            if not p.usable:
                d['reason']=str(p.support_reason)
                details.append(d)
                continue
            if key in alternate.index:
                alt = alternate.loc[key]
                d['shifted_alpha_width'] = float(alt.width) if np.isfinite(alt.width) else None
                if alt.usable:
                    difference = abs(float(p.width-alt.width))
                    d.update(phase_difference=difference,
                             phase_status='stable' if difference <= cfg['max_phase_difference'] else 'sensitive')
                else:
                    d['phase_status'] = 'shifted_spectrum_not_usable'
            density = p.density_m_per_km2
            refs = bg.loc[(bg.window_m == size) & bg.usable
                          & (bg.density_m_per_km2 >= density/cfg['density_match_factor'])
                          & (bg.density_m_per_km2 <= density*cfg['density_match_factor'])
                          & ((bg.coverage-p.coverage).abs() <= .1)]
            refs = refs.loc[~refs.geometry.intersects(p.geometry)]
            if shifted_background is not None:
                refs = refs.loc[refs.usable_alternate.fillna(False)]
            d['reference_count'] = len(refs)
            d['reference_center_ids'] = ','.join(str(int(v)) for v in refs.center_id)
            if len(refs) < cfg['min_reference_windows']:
                d['reason'] = 'insufficient_reference'
                details.append(d)
                continue
            reference = refs.width.to_numpy()
            median = float(np.median(reference))
            contrast = float(p.width-median)
            percentile = float((np.sum(reference < p.width-1e-10)
                                + .5*np.sum(np.isclose(reference, p.width, rtol=0, atol=1e-10)))/len(reference))
            size_class = (3 if percentile > cfg['class_3_above_percentile'] else
                          2 if percentile > cfg['class_2_above_percentile'] else 1)
            if shifted_background is not None and d['phase_status'] in ('stable','sensitive'):
                alternate_values=refs.width_alternate.to_numpy()
                alt_median=float(np.median(alternate_values))
                alt_width=float(alternate.loc[key].width)
                alt_percentile=float((np.sum(alternate_values < alt_width-1e-10)
                    + .5*np.sum(np.isclose(alternate_values,alt_width,rtol=0,atol=1e-10)))/len(alternate_values))
                alt_class=(3 if alt_percentile > cfg['class_3_above_percentile'] else
                           2 if alt_percentile > cfg['class_2_above_percentile'] else 1)
                reference_difference=abs(median-alt_median)
                d.update(alternate_background_median=alt_median,background_phase_difference=reference_difference,
                         alternate_percentile=alt_percentile,alternate_size_class=alt_class)
                d['phase_difference']=max(d['phase_difference'],reference_difference)
                if d['phase_difference'] > cfg['max_phase_difference'] or alt_class != size_class:
                    d['phase_status']='sensitive'
            d.update(reason='ranked', background_median=median, contrast=contrast,
                     empirical_percentile=percentile, size_class=size_class)
            details.append(d)
            percentiles.append(percentile)
            contrasts.append(contrast)
            if d["origin_width_range"] is not None:
                origin_ranges.append(d["origin_width_range"])
            phase_errors.append(d["phase_difference"])
            stable += int(d['phase_status'] == 'stable')
            sensitive += int(d['phase_status'] == 'sensitive')
            unknown_phase += int(d['phase_status'] not in ('stable', 'sensitive'))
        evaluated = len(percentiles)
        score = float(100*np.median(percentiles)) if evaluated else np.nan
        category = (3 if score > 100*cfg['class_3_above_percentile'] else
                    2 if score > 100*cfg['class_2_above_percentile'] else 1) if evaluated else None
        label = {None: 'Sin clasificar: soporte insuficiente', 1: 'Contraste relativo bajo',
                 2: 'Contraste relativo intermedio', 3: 'Contraste relativo alto'}[category]
        quality = ('not_evaluated' if not evaluated else
                   'grid_sensitive' if sensitive or unknown_phase else
                   'partial_support' if evaluated < len(sizes) else 'stable_two_phases')
        # A percentile remains a descriptive rank. A supported class requires
        # all requested sizes, usable alternate phase and bounded sensitivity.
        # Positive contrast must exceed the observed numerical phase spread;
        # this is a computational resolution check, not a significance test.
        relative_class = category
        resolved = (evaluated == len(sizes) and stable == len(sizes)
                    and all(v is not None for v in phase_errors))
        if resolved and category in (2, 3):
            resolved = bool(np.median(contrasts) > max(1e-8, np.median(phase_errors)))
        class_status = ('supported_two_phases' if resolved else
                        'insufficient_support' if evaluated < len(sizes) else
                        'grid_sensitive' if stable < len(sizes) else 'contrast_below_phase_resolution')
        if not resolved:
            category = None
            label = 'Sin clasificar: ' + class_status
        seed.update(score=score, relative_class=relative_class, class_status=class_status, evidence_class=category, evidence_label=label,
                    score_status='not_evaluated' if not evaluated else 'complete' if evaluated == len(sizes) else 'partial',
                    evaluated_sizes=evaluated, requested_sizes=len(sizes),
                    high_contrast_sizes=sum(v > cfg['class_3_above_percentile'] for v in percentiles),
                    stable_sizes=stable, sensitive_sizes=sensitive, unknown_phase_sizes=unknown_phase,
                    computational_quality=100*stable/len(sizes), quality_status=quality,
                    support_fraction=evaluated/len(sizes),
                    median_contrast=float(np.median(contrasts)) if contrasts else np.nan,
                    median_origin_width_range=float(np.median(origin_ranges)) if origin_ranges else np.nan,
                    source_confidence=np.nan, confidence_status='cartographic_confidence_not_evaluated',
                    formula_version='relative_multifractal_supported_v6',
                    interpretation='relative finite-scale heterogeneity; not permeability, significance or trap probability',
                    explanation=json.dumps({'formula':'100*median(background_percentiles) over evaluable sizes; null if none',
                        'percentiles': percentiles, 'evaluated_sizes': evaluated,
                        'quality_separate_from_rank': True, 'supported_class_requires_complete_stable_support': True, 'settings': cfg}, allow_nan=False))
        rows.append(seed)
    columns = list(rows[0]) if rows else ['candidate_id','source_layer','source_id','candidate_type','score','score_status','evidence_class','geometry']
    result = gpd.GeoDataFrame(rows, columns=columns, geometry='geometry', crs=seeds.crs)
    result['evidence_class'] = pd.array(result.evidence_class, dtype='Int64')
    metadata = {'version': 'relative_multifractal_supported_v6', 'settings': cfg,
                'measure': 'alpha(q=0)-alpha(q=2) in candidate-centered square windows',
                'grid_phases': [[0,0],[.5,.5]],
                'reference': 'primary phase for candidate AND background; accepted q0/q2, same size, matched density and coverage; outside candidate support',
                'reference_dependence': 'overlapping background windows; descriptive percentiles, not p-values or probabilities',
                'excluded_bonuses': ['exact crossing','degree','proximity','angle','structural order'],
                'interpretation': 'relative finite-scale patterns, not validated geological categories',
                'class_1': 'median background percentile <=50 (low relative contrast)',
                'class_2': 'median background percentile >50 and <=80 (intermediate relative contrast)',
                'class_3': 'median background percentile >80 (high relative contrast)',
                'unclassified': 'incomplete or unstable support or unresolved positive contrast; descriptive score and relative_class retained when evaluable',
                'quality': 'rank retained independently; supported class requires complete two-phase support and positive contrast exceeding phase spread',
                'score': '100*median(percentiles) over evaluable sizes; missing sizes reported separately',
                'class_limits': 'fixed background percentile thresholds, NOT candidate quantiles; classes may be empty',
                'persistence': 'high_contrast_sizes is descriptive support count, not independent confirmation'}
    if shifted_background is not None:
        result['formula_version']='relative_multifractal_ensemble_v7'
        metadata.update(version='relative_multifractal_ensemble_v7',
            reference='same-bank comparison on reference supports usable in both banks',
            quality='complete support and stable candidate/background bank means and per-size categories; individual-origin spread retained separately')
    return result, details, metadata


def compare_zeta_candidates(seeds, background, primary, shifted, sizes, settings=None, shifted_background=None):
    import pandas as pd
    canonical, details, metadata = classify_candidate_evidence(seeds, background, primary, shifted, sizes, settings, shifted_background)
    def weighted(frame):
        copy = frame.copy()
        copy['alpha'] = copy.alpha_w
        copy['accepted'] = copy.accepted_w
        if 'origin_alpha_w_json' in copy:
            copy['origin_alpha_json'] = copy.origin_alpha_w_json
        return copy
    weighted_result, weighted_details, weighted_meta = classify_candidate_evidence(
        seeds, weighted(background), weighted(primary), weighted(shifted), sizes, settings,
        weighted(shifted_background) if shifted_background is not None else None)
    for field in ('median_origin_width_range', 'relative_class', 'class_status', 'score', 'evidence_class', 'evidence_label', 'score_status', 'evaluated_sizes',
                  'high_contrast_sizes', 'stable_sizes', 'sensitive_sizes', 'unknown_phase_sizes',
                  'computational_quality', 'quality_status', 'support_fraction', 'median_contrast', 'explanation'):
        canonical[field+'_w'] = weighted_result[field]
    canonical['class_agreement'] = [
        'not_comparable' if pd.isna(a) or pd.isna(b) else
        'same_class' if a == b else 'changed_class'
        for a,b in zip(canonical.evidence_class, weighted_result.evidence_class)]
    canonical['score_delta_w'] = canonical.score_w-canonical.score
    for column in ('zeta_mean', 'zeta_min', 'zeta_reliable_sizes'):
        canonical[column] = np.nan
    for i in canonical.index:
        local = primary.loc[primary.center_id.eq(i)]
        canonical.loc[i, 'zeta_mean'] = local.zeta_mean.mean()
        canonical.loc[i, 'zeta_min'] = local.zeta_min.min()
        canonical.loc[i, 'zeta_reliable_sizes'] = sum(
            group.q.isin([0,2]).sum() == 2 and group.loc[group.q.isin([0,2]), 'reliable_w'].all()
            for _,group in local.groupby('window_m'))
    canonical['formula_version'] = 'relative_multifractal_zeta_supported_v6'
    metadata.update(version='relative_multifractal_zeta_supported_v6',
                    weighted_comparison=weighted_meta,
                    default_score='canonical; weighted counterpart score_w exported independently',
                    zeta_role='weights regression scales, never multiplies class or percentile; reliability separate')
    if shifted_background is not None:
        canonical['formula_version']='relative_multifractal_ensemble_v7'
        metadata.update(version='relative_multifractal_ensemble_v7',
            reference='paired usable background supports in both origin banks; each candidate compared to its same-bank reference',
            class_eligibility='complete support; candidate and reference mean width stable; same relative class in both banks at every size; positive contrast exceeds bank difference',
            origin_spread='raw per-origin H range retained; origins are dependent, not standard-error samples')
    for d in details:
        d['estimator'] = 'canonical'
    for d in weighted_details:
        d['estimator'] = 'zeta_weighted'
    return canonical, details+weighted_details, metadata


def evaluate_candidates(analyzer, nodes, background, relations, config, settings=None, progress=None):
    from .moving import analyze_moving_windows
    seeds = candidate_seeds(nodes, relations)
    if seeds.empty:
        return classify_candidate_evidence(seeds, background, background, background, config['window_sizes_m'], settings), None, None, None
    centers = [(p.x, p.y) for p in seeds.geometry]
    args = dict(divisors=config['divisors'], q_values=[0,2], min_coverage=config['min_coverage'],
                min_r2=config['min_r2'], min_effective_boxes=config['min_effective_boxes'],
                centers=centers, max_windows=config['max_windows'],
                zeta_exponents=config['zeta_exponents'], zeta_scale_floor=config['zeta_scale_floor'],
                reliable_min_zeta=config['reliable_min_zeta'],origin_offsets=config.get('origin_offsets'),workers=config.get('workers',1))
    base_phase=np.asarray(config['grid_phase'])
    ensemble=len(config.get('origin_offsets',[(0,0)])) > 1
    alternate_phase=(base_phase+(.125 if ensemble else .5))%1
    shifted_background=None
    if ensemble:
        if progress: progress('Fondo: segundo conjunto de origenes.')
        reference_args=dict(args,centers=config['centers'])
        shifted_background,_,_=analyze_moving_windows(analyzer,config['window_sizes_m'],config['step_m'],
            grid_phase=alternate_phase,**reference_args)
    if progress: progress('Candidatos: primer conjunto de origenes.')
    primary, _, _ = analyze_moving_windows(analyzer, config['window_sizes_m'], config['step_m'],grid_phase=base_phase, **args)
    if progress: progress('Candidatos: segundo conjunto de origenes.')
    shifted, _, _ = analyze_moving_windows(analyzer, config['window_sizes_m'], config['step_m'], grid_phase=alternate_phase, **args)
    result = compare_zeta_candidates(seeds, background, primary, shifted, config['window_sizes_m'], settings, shifted_background)
    result[2]['grid_phases']=[base_phase.tolist(),alternate_phase.tolist()]
    result[2]['origin_offsets']=config.get('origin_offsets',[(0,0)])
    result[2]['divisors']=config['divisors']
    result[2]['zeta_settings'] = {k: config[k] for k in
                                 ('zeta_exponents', 'zeta_scale_floor', 'reliable_min_zeta')}
    for frame in (primary, shifted):
        frame['candidate_id'] = frame.center_id.map(seeds.candidate_id.to_dict())
    return result, primary, shifted, shifted_background
