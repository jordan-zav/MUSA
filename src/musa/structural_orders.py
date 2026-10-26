"""Preserve interpreted orders as context, separate from geometric scores."""
import json
from itertools import combinations

import numpy as np


def attach_structural_orders(candidates, analyzer, relations=None):
    from shapely.geometry import Point

    source = getattr(analyzer, '_source_gdf', None)
    result = candidates.copy()
    fields = {k: [] for k in ['participant_faults_json', 'interaction_orders', 'order_priority',
                             'order_status', 'participant_count', 'priority_basis']}
    relation_map = {} if relations is None else {int(r.relation_id): r.geometry for r in relations.itertuples()}
    for row in candidates.itertuples():
        participants = []
        if source is not None:
            points = [row.geometry]
            if row.source_layer == 'potential_relations':
                geometry = relation_map[int(row.source_id)]
                points = [Point(geometry.coords[0]), Point(geometry.coords[-1])]
            indices = set()
            # Numeric matching only; this does not snap or join disconnected faults.
            for point in points:
                indices.update(int(i) for i in source.sindex.query(point.buffer(1e-6), predicate='intersects'))
            for i in sorted(indices):
                entry = source.iloc[i]
                raw = entry.get('structural_orders', entry.get('structural_order', ''))
                try:
                    orders = sorted(set(int(float(v.strip())) for v in str(raw).split(',') if v.strip()))
                    if not orders or any(v not in (1, 2, 3) for v in orders):
                        orders = []
                except (ValueError, TypeError):
                    orders = []
                participants.append({'fault_id': str(entry.get('fault_id', i)), 'orders': orders})
        interactions = set()
        for a, b in combinations(participants, 2):
            for oa in a['orders']:
                for ob in b['orders']:
                    interactions.add(f'{min(oa,ob)}-{max(oa,ob)}')
        ambiguous = any(len(p['orders']) > 1 for p in participants)
        missing = not participants or any(not p['orders'] for p in participants)
        status = 'missing_order' if missing else 'ambiguous_classification' if ambiguous else 'known'
        priority = min(p['orders'][0] for p in participants) if status == 'known' else np.nan
        fields['participant_faults_json'].append(json.dumps(participants))
        fields['interaction_orders'].append(','.join(sorted(interactions)))
        fields['order_priority'].append(priority)
        fields['order_status'].append(status)
        fields['participant_count'].append(len(participants))
        fields['priority_basis'].append('lowest interpreted order present; 1 highest; separate from geometric score; no perpendicularity bonus')
    for name, values in fields.items():
        result[name] = values
    from .node_classes import classify_nodes
    return classify_nodes(result)
