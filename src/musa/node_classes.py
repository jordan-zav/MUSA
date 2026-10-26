"""Descriptive node classes, independent of multifractal ranks."""
import json
import math

PAIRS = ('1-1', '1-2', '1-3', '2-2', '2-3', '3-3')
DEFAULT_POLICY = {
    'version': 'node_classes_v1',
    'status': 'neutral_baseline_not_calibrated',
    'weights': {pair: 1.0 for pair in PAIRS},
    'interpretation': 'Relative class weights, not probability. Neutral until a geological weighting is specified. No angle, zeta or multifractal multiplier.',
}


def classify_nodes(candidates, policy=None):
    policy = DEFAULT_POLICY if policy is None else policy
    weights = policy['weights']
    if set(weights) != set(PAIRS) or any(not math.isfinite(float(v)) or float(v) < 0 for v in weights.values()):
        raise ValueError('Specify all six pair weights as finite nonnegative numbers')
    result = candidates.copy()
    classes, statuses, values, kinds = [], [], [], []
    for row in result.itertuples():
        pairs = sorted(set(str(row.interaction_orders).split(',')) & set(PAIRS))
        kind = 'proximity' if row.source_layer == 'potential_relations' else 'planar_intersection'
        status = row.order_status
        if status == 'known':
            status = 'single_pair' if len(pairs) == 1 else 'multiple_pairs' if pairs else 'unresolved'
        cls = pairs[0] if status == 'single_pair' else status
        classes.append(cls)
        statuses.append(status)
        values.append(float(weights[cls]) if status == 'single_pair' else float('nan'))
        kinds.append(kind)
    result['node_class'] = classes
    result['node_class_status'] = statuses
    result['node_kind'] = kinds
    result['node_weight'] = values
    result['node_weight_status'] = policy['status']
    result['node_policy_json'] = json.dumps(policy, sort_keys=True)
    result['structural_trap_class'] = None
    result['structural_trap_status'] = 'not_assessed_requires_geological_rule'
    return result


def export_products(path, policy=None):
    """Add explicit products to a completed MUSA GeoPackage without refitting."""
    import geopandas as gpd
    import sqlite3
    from .candidates import _spectral_table
    nodes = classify_nodes(gpd.read_file(path, layer='trap_candidates'), policy)
    nodes.to_file(path, layer='node_classes', driver='GPKG')
    windows = gpd.read_file(path, layer='window_spectra')
    pathway = gpd.GeoDataFrame(_spectral_table(windows), geometry='geometry', crs=windows.crs)
    pathway = pathway.rename(columns={'width': 'multifractal_contrast', 'usable': 'contrast_usable'})
    pathway['product_status'] = 'experimental_provisional_coverage'
    pathway.to_file(path, layer='pathway_multifractal', driver='GPKG')
    categories, symbols = [], []
    palette = ['#3366aa', '#cc3377', '#228833', '#ee7733', '#aa4499', '#66ccee', '#888888', '#555555', '#bbbbbb', '#dddddd']
    for i, label in enumerate((*PAIRS, 'multiple_pairs', 'ambiguous_classification', 'missing_order', 'unresolved')):
        categories.append(f'<category value="{label}" label="{label}" symbol="{i}" render="true"/>')
        symbols.append(f'<symbol name="{i}" type="marker"><layer class="SimpleMarker"><Option type="Map"><Option name="name" value="circle"/><Option name="color" value="{palette[i]}"/><Option name="size" value="2.5"/></Option></layer></symbol>')
    qml = '<qgis version="3.34" styleCategories="Symbology"><renderer-v2 type="categorizedSymbol" attr="node_class"><categories>'+''.join(categories)+'</categories><symbols>'+''.join(symbols)+'</symbols></renderer-v2></qgis>'
    with sqlite3.connect(path) as db:
        geom = db.execute("SELECT column_name FROM gpkg_geometry_columns WHERE table_name='node_classes'").fetchone()[0]
        db.execute("DELETE FROM layer_styles WHERE f_table_name='node_classes'")
        db.execute('INSERT INTO layer_styles (f_table_name,f_geometry_column,styleName,styleQML,useAsDefault,description) VALUES (?,?,?,?,1,?)', ('node_classes', geom, 'MUSA_node_classes', qml, 'Fault-pair classes; proximity is not a mapped intersection.'))
        # Reuse the continuous spectrum style with the new explicit field.
        template = db.execute("SELECT styleQML FROM layer_styles WHERE f_table_name='window_spectra' AND useAsDefault=1").fetchone()
        if template:
            qml_pathway = template[0].replace('&quot;q&quot; = 2 AND &quot;accepted&quot;', '&quot;contrast_usable&quot;').replace('q=2 - ajuste aceptado', 'Contraste evaluable').replace('q=2 - ajuste no aceptado', 'Contraste sin soporte')
            db.execute("DELETE FROM layer_styles WHERE f_table_name='pathway_multifractal'")
            db.execute('INSERT INTO layer_styles (f_table_name,f_geometry_column,styleName,styleQML,useAsDefault,description) VALUES (?,?,?,?,1,?)', ('pathway_multifractal', 'geom', 'MUSA_pathway_multifractal', qml_pathway, 'Experimental contrast by window size; inspect contrast_usable.'))
        db.execute("UPDATE gpkg_contents SET description=? WHERE table_name='trap_candidates'", ('Legacy diagnostic layer. Not geological trap classes; use node_classes for fault-pair classes.',))
    return nodes, pathway
