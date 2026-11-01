"""GeoPackage output using GDAL supplied by QGIS; no GeoPandas for mother cells."""

import csv
import math
from pathlib import Path


def export_mother_layers(output_dir, crs_wkt, config):
    from osgeo import ogr, osr

    out = Path(output_dir)
    target = out / "musa_mother_cells.gpkg"
    if target.exists():
        raise FileExistsError(target)
    srs = osr.SpatialReference()
    if srs.SetFromUserInput(str(crs_wkt)) != 0:
        raise ValueError("Cannot decode analysis CRS.")
    srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    datasource = ogr.GetDriverByName("GPKG").CreateDataSource(str(target))
    if datasource is None:
        raise OSError(f"Cannot create {target}")
    definitions = (
        ("multifractal_mother_agg.csv", "mother_multifractal_all_q"),
        ("monofractal_mother_agg.csv", "mother_monofractal"),
        ("lineament_mother_structural_stats.csv", "mother_structural_stats"),
    )

    def write_layer(name, rows, fields):
        layer = datasource.CreateLayer(name, srs, ogr.wkbPolygon)
        if layer is None:
            raise OSError(f"Cannot create layer {name}")
        numeric = {}
        for field in fields:
            values = [row[field] for row in rows if row[field] != ""]
            try:
                [float(value) for value in values]
                numeric[field] = True
            except ValueError:
                numeric[field] = False
            layer.CreateField(ogr.FieldDefn(field, ogr.OFTReal if numeric[field] else ogr.OFTString))
        datasource.StartTransaction()
        try:
            for row in rows:
                x, y, size = (float(row[key]) for key in ("mother_centroid_x", "mother_centroid_y", "mother_scale_m"))
                ring = ogr.Geometry(ogr.wkbLinearRing)
                half = size / 2
                for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half), (-half, -half)):
                    ring.AddPoint_2D(x + dx, y + dy)
                polygon = ogr.Geometry(ogr.wkbPolygon)
                polygon.AddGeometry(ring)
                feature = ogr.Feature(layer.GetLayerDefn())
                feature.SetGeometry(polygon)
                for key, value in row.items():
                    if value == "":
                        continue
                    if numeric[key]:
                        value = float(value)
                        if not math.isfinite(value):
                            continue
                    feature.SetField(key, value)
                if layer.CreateFeature(feature) != 0:
                    raise OSError(f"Cannot write {name}")
                feature = None
            datasource.CommitTransaction()
        except Exception:
            datasource.RollbackTransaction()
            raise

    try:
        for filename, name in definitions:
            path = out / filename
            if not path.is_file() or not path.stat().st_size:
                continue
            with path.open(encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                rows = list(reader)
                fields = reader.fieldnames
            write_layer(name, rows, fields)
            if name == "mother_multifractal_all_q" and rows:
                q = min({float(row["q"]) for row in rows}, key=lambda value: abs(value - 2))
                selected = [row for row in rows if float(row["q"]) == q]
                write_layer("mother_multifractal_display", selected, fields)
                reliable = [
                    row
                    for row in selected
                    if float(row.get("reliable", 0)) >= 1
                    and float(row.get("zeta_mean", 0)) >= config.reliable_min_zeta
                    and float(row.get("alpha_w_r2", 0)) >= config.min_r2
                    and float(row.get("f_alpha_w_r2", 0)) >= config.min_r2
                ]
                write_layer("mother_multifractal_reliable", reliable, fields)
    finally:
        datasource = None
    return {"mother_geopackage": str(target)}
