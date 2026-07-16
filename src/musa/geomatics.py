from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def export_mother_geopackage(
    output_dir: str | Path,
    crs: Any = None,
    highlight_q: float = 2.0,
    reliable_min_zeta: float = 0.15,
    reliable_min_r2: float = 0.9,
    filename: str = "musa_mother_cells.gpkg",
) -> dict[str, Any]:
    """
    Export mother-cell CSV outputs as GIS-ready GeoPackage layers.

    The function is intentionally downstream of CSV generation: it does not
    recompute MUSA metrics and can be rerun after manual CSV filtering.
    """
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point, box

    out_dir = Path(output_dir)
    multi_path = out_dir / "multifractal_mother_agg.csv"
    if not multi_path.is_file():
        raise FileNotFoundError(f"No existe {multi_path}")

    gpkg_path = out_dir / filename
    if gpkg_path.exists():
        gpkg_path.unlink()

    layers: list[str] = []
    multi = pd.read_csv(multi_path)
    multi = _coerce_numeric_columns(multi)
    multi = _add_reliable_gis_column(multi, reliable_min_zeta, reliable_min_r2)
    q_value = _pick_q(multi["q"].to_numpy(dtype=float), highlight_q)

    all_q = _mother_polygons_gdf(multi, crs, box)
    _write_layer(all_q, gpkg_path, "mother_multifractal_all_q")
    layers.append("mother_multifractal_all_q")

    q_rows = multi[np.isclose(multi["q"].astype(float), q_value)].copy()
    q_label = _q_label(q_value)
    q_layer = f"mother_multifractal_q{q_label}"
    q_gdf = _mother_polygons_gdf(q_rows, crs, box)
    _write_layer(q_gdf, gpkg_path, q_layer)
    layers.append(q_layer)

    reliable_rows = q_rows[q_rows["reliable_gis"] == 1].copy()
    reliable_layer = f"mother_multifractal_q{q_label}_reliable"
    reliable_gdf = _mother_polygons_gdf(reliable_rows, crs, box)
    _write_layer(reliable_gdf, gpkg_path, reliable_layer)
    layers.append(reliable_layer)

    centroid_layer = f"mother_centroids_q{q_label}_reliable"
    centroid_gdf = gpd.GeoDataFrame(
        reliable_rows,
        geometry=[
            Point(float(x), float(y))
            for x, y in zip(reliable_rows["mother_centroid_x"], reliable_rows["mother_centroid_y"])
        ],
        crs=crs,
    )
    _write_layer(centroid_gdf, gpkg_path, centroid_layer)
    layers.append(centroid_layer)

    mono_path = out_dir / "monofractal_mother_agg.csv"
    if mono_path.is_file():
        mono = _coerce_numeric_columns(pd.read_csv(mono_path))
        mono_gdf = _mother_polygons_gdf(mono, crs, box)
        _write_layer(mono_gdf, gpkg_path, "mother_monofractal")
        layers.append("mother_monofractal")

    structural_path = out_dir / "lineament_mother_structural_stats.csv"
    if structural_path.is_file():
        structural = _coerce_numeric_columns(pd.read_csv(structural_path))
        structural_gdf = _mother_polygons_gdf(structural, crs, box)
        _write_layer(structural_gdf, gpkg_path, "mother_structural_stats")
        layers.append("mother_structural_stats")

    validation = _validation_join(q_rows, out_dir)
    if validation is not None:
        validation_gdf = _mother_polygons_gdf(validation, crs, box)
        validation_layer = f"mother_validation_q{q_label}"
        _write_layer(validation_gdf, gpkg_path, validation_layer)
        layers.append(validation_layer)

    return {"geopackage": str(gpkg_path), "layers": layers, "highlight_q": q_value}


def _write_layer(gdf, path: Path, layer: str) -> None:
    if len(gdf) == 0:
        gdf = gdf.copy()
    gdf.to_file(path, layer=layer, driver="GPKG")


def _coerce_numeric_columns(df):
    for column in df.columns:
        df[column] = _maybe_numeric(df[column])
    return df


def _maybe_numeric(series):
    import pandas as pd

    converted = pd.to_numeric(series, errors="coerce")
    if converted.notna().sum() == series.notna().sum():
        return converted
    return series


def _add_reliable_gis_column(df, reliable_min_zeta: float, reliable_min_r2: float):
    reliable = np.ones(len(df), dtype=bool)
    if "reliable" in df.columns:
        reliable &= df["reliable"].fillna(0).astype(float).to_numpy() >= 1
    if "zeta_mean" in df.columns:
        reliable &= df["zeta_mean"].fillna(0).astype(float).to_numpy() >= reliable_min_zeta
    if "alpha_w_r2" in df.columns:
        reliable &= df["alpha_w_r2"].fillna(0).astype(float).to_numpy() >= reliable_min_r2
    if "f_alpha_w_r2" in df.columns:
        reliable &= df["f_alpha_w_r2"].fillna(0).astype(float).to_numpy() >= reliable_min_r2
    df = df.copy()
    df["reliable_gis"] = reliable.astype(int)
    return df


def _pick_q(values: np.ndarray, highlight_q: float) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise ValueError("No hay valores q finitos para exportar GeoPackage.")
    return float(finite[int(np.argmin(np.abs(finite - highlight_q)))])


def _q_label(q_value: float) -> str:
    text = f"{q_value:g}".replace("-", "m").replace(".", "p")
    return text


def _mother_polygons_gdf(df, crs, box_factory):
    import geopandas as gpd

    geometries = []
    for _, row in df.iterrows():
        scale = float(row["mother_scale_m"])
        cx = float(row["mother_centroid_x"])
        cy = float(row["mother_centroid_y"])
        half = scale / 2.0
        geometries.append(box_factory(cx - half, cy - half, cx + half, cy + half))
    return gpd.GeoDataFrame(df.copy(), geometry=geometries, crs=crs)


def _validation_join(q_rows, out_dir: Path):
    import pandas as pd

    validation = q_rows.copy()
    structural_path = out_dir / "lineament_mother_structural_stats.csv"
    if structural_path.is_file():
        structural = _coerce_numeric_columns(pd.read_csv(structural_path))
        keep_cols = [
            c
            for c in [
                "mother_ix",
                "mother_iy",
                "density_m_per_km2",
                "dominant_azimuth_deg",
                "mean_azimuth_deg",
                "circular_variance",
                "anisotropy_ratio",
                "segment_count",
            ]
            if c in structural.columns
        ]
        validation = validation.merge(
            structural[keep_cols],
            on=["mother_ix", "mother_iy"],
            how="left",
            suffixes=("", "_struct"),
        )
    return validation
