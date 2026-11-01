"""Copy and reproject project geometry before starting a background task."""

import hashlib
import json

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsWkbTypes,
)


def validate_metric_crs(crs):
    if not crs.isValid() or crs.isGeographic() or crs.mapUnits() != Qgis.DistanceUnit.Meters:
        raise ValueError("Choose a projected analysis CRS in metres.")


def snapshot_sources(lines, boundary, target_crs, transform_context=None, *, selected_only=False, cancelled=None):
    """Only bytes/strings enter the worker, including unsaved memory/edit data.

    This runs on the main thread in the dock, and in prepareAlgorithm for
    Processing. All boundary features are included; line selection is explicit.
    """
    validate_metric_crs(target_crs)
    transform_context = transform_context or QgsProject.instance().transformContext()

    def copy_source(source, expected_type, selected):
        if source is None or not source.sourceCrs().isValid():
            raise ValueError("Both inputs need a defined source CRS.")
        if QgsWkbTypes.geometryType(source.wkbType()) != expected_type:
            raise ValueError("Choose a line layer and a polygon boundary layer.")
        transform = QgsCoordinateTransform(source.sourceCrs(), target_crs, transform_context)
        features = source.getSelectedFeatures() if selected else source.getFeatures()
        result, attributes = [], []
        retained = [
            field for field in ("fault_id", "structural_order", "structural_orders") if field in source.fields().names()
        ]
        for feature in features:
            if cancelled and cancelled():
                raise RuntimeError("Input preparation cancelled.")
            geometry = QgsGeometry(feature.geometry())
            if geometry.isNull() or geometry.isEmpty():
                continue
            if geometry.requiresConversionToStraightSegments():
                geometry.convertToStraightSegment()
            if not geometry.isGeosValid():
                raise ValueError(f"Invalid geometry in feature {feature.id()}; repair the input layer first.")
            if source.sourceCrs() != target_crs:
                geometry.transform(transform)
            if not geometry.isGeosValid():
                raise ValueError(f"Feature {feature.id()} is invalid after transformation.")
            result.append(bytes(geometry.asWkb()))
            if expected_type == QgsWkbTypes.LineGeometry:
                entry = {name: str(feature[name]) for name in retained}
                entry.setdefault("fault_id", str(feature.id()))
                attributes.append(entry)
        if not result:
            raise ValueError("Input is empty (or the explicit line selection is empty).")
        return tuple(result), tuple(attributes)

    line_wkb, attributes = copy_source(lines, QgsWkbTypes.LineGeometry, selected_only)
    boundary_wkb, _ = copy_source(boundary, QgsWkbTypes.PolygonGeometry, False)

    def digest(items):
        value = hashlib.sha256()
        for item in items:
            value.update(len(item).to_bytes(8, "big"))
            value.update(item)
        return value.hexdigest()

    return {
        "lines": line_wkb,
        "boundary": boundary_wkb,
        "line_attributes": attributes,
        "crs_wkt": target_crs.toWkt(),
        "info": {
            "qgis_version": Qgis.QGIS_VERSION,
            "analysis_crs": target_crs.authid() or target_crs.toWkt(),
            "line_features": len(line_wkb),
            "boundary_features": len(boundary_wkb),
            "selected_lines_only": selected_only,
            "line_geometry_sha256": digest(line_wkb),
            "boundary_geometry_sha256": digest(boundary_wkb),
            "structural_attributes_sha256": hashlib.sha256(
                json.dumps(attributes, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        },
    }


def make_analyzer(snapshot, config):
    from shapely import wkb
    from shapely.ops import unary_union
    from .runtime import core

    MUSA, _, _ = core()
    boundary = unary_union([wkb.loads(value) for value in snapshot["boundary"]])
    lines = [wkb.loads(value) for value in snapshot["lines"]]
    analyzer = MUSA.from_line_geometries(lines, boundary, snapshot["crs_wkt"], q_values=config.q_values())
    if config.moving:
        import geopandas as gpd

        analyzer._source_gdf = gpd.GeoDataFrame(
            list(snapshot["line_attributes"]), geometry=lines, crs=snapshot["crs_wkt"]
        )
    return analyzer
