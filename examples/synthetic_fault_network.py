"""Reproducible fault-like traces for MUSA demonstrations, not a geological model.

Uses arbitrary UTM coordinates. Families, orders, gaps and splays are synthetic
construction labels, not inferred geology. No real project data are used.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Polygon


FAMILIES = {
    "Main NE-SW": ("#9b3d2e", 1),
    "Conjugate NW-SE": ("#2a6482", 2),
    "Transfer E-W": ("#9b7526", 2),
    "Fault splays": ("#b96945", 3),
    "Short secondary traces": ("#678775", 3),
}


def generate(seed=20261028):
    rng = np.random.default_rng(seed)
    origin = np.array([400000.0, 8600000.0])
    boundary = Polygon(
        origin
        + np.array(
            [
                [0, 1800],
                [2200, 0],
                [20500, 0],
                [24000, 3500],
                [24000, 17000],
                [20500, 20000],
                [3000, 20000],
                [0, 16000],
            ]
        )
    )
    features = []

    def parts(geometry):
        if geometry.geom_type == "LineString":
            yield geometry
        elif hasattr(geometry, "geoms"):
            for item in geometry.geoms:
                yield from parts(item)

    def add(geometry, family, parent=""):
        added = []
        for part in parts(geometry.intersection(boundary)):
            if part.length < 80:
                continue
            fid = f"SF{len(features) + 1:04d}"
            row = {
                "fault_id": fid,
                "family": family,
                "structural_order": FAMILIES[family][1],
                "parent_id": parent,
                "length_m": float(part.length),
                "synthetic": 1,
                "geometry": part,
            }
            features.append(row)
            added.append(row)
        return added

    def trace(center, azimuth, length, bend, n=35):
        angle = np.radians(azimuth)
        along = np.array([np.sin(angle), np.cos(angle)])
        across = np.array([np.cos(angle), -np.sin(angle)])
        u = np.linspace(-0.5, 0.5, n)
        phase = rng.uniform(-np.pi, np.pi)
        displacement = bend * (np.sin(2 * np.pi * u + phase) + 0.18 * np.sin(7 * np.pi * u + phase))
        return LineString(np.asarray(center) + u[:, None] * length * along + displacement[:, None] * across)

    main = []
    for index in range(9):
        center = origin + [2800 + index * 2150, 9500 + rng.normal(0, 2000)]
        main.extend(
            add(trace(center, rng.normal(32, 5), rng.uniform(15000, 24000), rng.uniform(170, 460)), "Main NE-SW")
        )
    for _ in range(28):
        center = origin + [rng.uniform(2500, 22500), rng.uniform(1800, 18500)]
        add(trace(center, rng.normal(128, 11), rng.uniform(3500, 12500), rng.uniform(70, 220)), "Conjugate NW-SE")
    for _ in range(13):
        center = origin + [rng.uniform(3000, 20500), rng.uniform(2500, 17500)]
        add(trace(center, rng.normal(86, 7), rng.uniform(3000, 10000), rng.uniform(50, 170)), "Transfer E-W")
    # Branches start on a parent trace; several stop short to retain near misses.
    for _ in range(54):
        parent = main[int(rng.integers(len(main)))]
        geom = parent["geometry"]
        distance = rng.uniform(0.12, 0.88) * geom.length
        start = np.array(geom.interpolate(distance).coords[0])
        a = np.array(geom.interpolate(max(0, distance - 20)).coords[0])
        b = np.array(geom.interpolate(min(geom.length, distance + 20)).coords[0])
        azimuth = np.degrees(np.arctan2(*(b - a)))
        azimuth += rng.choice([-1, 1]) * rng.uniform(18, 48)
        length = rng.uniform(450, 3200)
        generated = trace(start, azimuth, length, rng.uniform(15, 75), n=18)
        coords = np.asarray(generated.coords)
        coords += start - coords[0]
        if rng.random() < 0.25:
            coords += (coords[1] - coords[0]) * 0.4
        add(LineString(coords), "Fault splays", parent["fault_id"])
    # Uneven secondary-trace density: two corridors and a sparse background.
    for index in range(110):
        if index < 75:
            cluster = np.array([10500, 10500]) if index % 2 else np.array([17500, 6500])
            center = origin + cluster + rng.normal(0, [2100, 2300])
        else:
            center = origin + [rng.uniform(700, 23300), rng.uniform(700, 19300)]
        family_angle = rng.choice([35.0, 125.0, 85.0], p=[0.6, 0.3, 0.1])
        add(
            trace(center, rng.normal(family_angle, 15), rng.uniform(250, 2100), rng.uniform(10, 60), n=14),
            "Short secondary traces",
        )
    assert boundary.is_valid and all(row["geometry"].is_valid for row in features)
    assert all(boundary.buffer(1e-6).covers(row["geometry"]) for row in features)
    return boundary, features


def write_dataset(output, seed=20261028):
    from osgeo import ogr, osr

    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    boundary, features = generate(seed)
    crs = osr.SpatialReference()
    crs.ImportFromEPSG(32718)
    crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = out / "synthetic_faults.gpkg"
    ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(target))
    layer = ds.CreateLayer("fault_traces", crs, ogr.wkbLineString)
    for name, kind in (
        ("fault_id", ogr.OFTString),
        ("family", ogr.OFTString),
        ("structural_order", ogr.OFTInteger),
        ("parent_id", ogr.OFTString),
        ("length_m", ogr.OFTReal),
        ("synthetic", ogr.OFTInteger),
    ):
        layer.CreateField(ogr.FieldDefn(name, kind))
    for row in features:
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(ogr.CreateGeometryFromWkb(row["geometry"].wkb))
        for key, value in row.items():
            if key != "geometry":
                feature.SetField(key, value)
        assert layer.CreateFeature(feature) == 0
        feature = None
    layer = ds.CreateLayer("analysis_boundary", crs, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("description", ogr.OFTString))
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("description", "Synthetic study area; arbitrary projected coordinates; not a real site")
    feature.SetGeometry(ogr.CreateGeometryFromWkb(boundary.wkb))
    assert layer.CreateFeature(feature) == 0
    feature = None
    ds = None
    description = {
        "seed": seed,
        "crs": "EPSG:32718",
        "synthetic": True,
        "purpose": "Illustrative fault-like geometry, not a mechanical or geological simulation",
        "real_location": False,
        "feature_count": len(features),
        "families": dict(Counter(row["family"] for row in features)),
        "area_km2": boundary.area / 1e6,
        "total_length_km": sum(row["length_m"] for row in features) / 1000,
        "input_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    (out / "dataset_description.json").write_text(json.dumps(description, indent=2), encoding="utf-8")
    return description


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20261028)
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.output, args.seed), indent=2))
