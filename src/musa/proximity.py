"""Exploratory proximity relations; never edits or connects fault geometries."""
import numpy as np

from .network import _iter_line_parts


def analyze_fault_proximity(analyzer, radii_m, max_relations=100000):
    import geopandas as gpd
    from shapely.geometry import LineString, Point
    from shapely.ops import nearest_points, linemerge
    from shapely.strtree import STRtree

    radii = np.unique(np.asarray(radii_m, dtype=float))
    if radii.size == 0 or not np.all(np.isfinite(radii)) or np.any(radii <= 0):
        raise ValueError("Proximity radii must be positive, finite metres.")
    crs = analyzer._active_crs
    if analyzer._kind != 'lines' or not crs or not crs.is_projected or any(abs(a.unit_conversion_factor-1) > 1e-9 for a in crs.axis_info[:2]):
        raise ValueError("Proximity requires GIS lines in a projected metric CRS.")
    boundary = analyzer._boundary_geom
    lines = [part for geom in analyzer._line_geometries for part in _iter_line_parts(geom) if part.length > 0]
    # Remove artificial degree-two endpoint splits, without noding crossings,
    # snapping gaps or merging branches. These are geometric chains, not IDs.
    if lines:
        lines = sorted(_iter_line_parts(linemerge(lines)), key=lambda g: g.normalize().wkb)
        lines = [g.normalize() for g in lines]
    tree = STRtree(lines)
    tol = max(np.sqrt(boundary.area)*1e-10, 1e-8)
    rows, zones = [], []

    def endpoint(line, p):
        return min(p.distance(Point(line.coords[0])), p.distance(Point(line.coords[-1]))) <= tol

    def azimuth(line, p):
        distance = line.project(p)
        delta = min(1.0, line.length/1000)
        a, b = line.interpolate(max(0, distance-delta)), line.interpolate(min(line.length, distance+delta))
        return float(np.degrees(np.arctan2(b.x-a.x, b.y-a.y)) % 180)

    for i, line in enumerate(lines):
        for j in sorted(tree.query(line.buffer(float(radii[-1])))):
            j = int(j)
            if j <= i or line.intersects(lines[j]):
                continue
            a, b = nearest_points(line, lines[j])
            gap = a.distance(b)
            if gap <= tol or gap > radii[-1]:
                continue
            connector = LineString([a, b])
            if boundary.boundary.distance(a) <= tol or boundary.boundary.distance(b) <= tol or not boundary.covers(connector):
                continue  # do not infer relations across clipping boundaries or holes
            ea, eb = endpoint(line, a), endpoint(lines[j], b)
            relation = 'end_end' if ea and eb else 'end_trace' if ea or eb else 'trace_trace'
            angle = abs(azimuth(line, a)-azimuth(lines[j], b))
            matched = radii[radii >= gap]
            row = {'relation_id': len(rows), 'part_a': i, 'part_b': j,
                   'relation_type': relation, 'gap_m': float(gap),
                   'first_radius_m': float(matched[0]), 'tested_radii_count': int(len(matched)),
                   'matching_radii_m': ','.join(f'{r:g}' for r in matched),
                   'axial_angle_deg': min(angle, 180-angle),
                   'interpretation': 'nearest_relation_between_endpoint_merged_chains_not_connection', 'geometry': connector}
            rows.append(row)
            zones.append(dict(row, geometry=connector.interpolate(.5, normalized=True).buffer(float(matched[0])).intersection(boundary)))
            if len(rows) > max_relations:
                raise ValueError("Too many proximity relations; reduce radii or analysis area.")
    columns = ['relation_id', 'part_a', 'part_b', 'relation_type', 'gap_m', 'first_radius_m',
               'tested_radii_count', 'matching_radii_m', 'axial_angle_deg', 'interpretation', 'geometry']
    return (gpd.GeoDataFrame(rows, columns=columns, geometry='geometry', crs=crs),
            gpd.GeoDataFrame(zones, columns=columns, geometry='geometry', crs=crs))
