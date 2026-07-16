import csv
from pathlib import Path

import pytest

from musa.geomatics import export_mother_geopackage


pytest.importorskip("geopandas")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_export_mother_geopackage_writes_q2_polygons_and_reliable_layer(tmp_path):
    _write_csv(
        tmp_path / "multifractal_mother_agg.csv",
        [
            {
                "mother_scale_m": 1000,
                "mother_ix": 0,
                "mother_iy": 0,
                "mother_centroid_x": 500,
                "mother_centroid_y": 500,
                "q": 2,
                "alpha_w": 1.2,
                "f_alpha_w": 1.1,
                "alpha_w_r2": 0.95,
                "f_alpha_w_r2": 0.96,
                "zeta_mean": 0.2,
                "measure_sum_m": 1200,
                "reliable": 1,
            },
            {
                "mother_scale_m": 1000,
                "mother_ix": 1,
                "mother_iy": 0,
                "mother_centroid_x": 1500,
                "mother_centroid_y": 500,
                "q": 2,
                "alpha_w": 0.9,
                "f_alpha_w": 0.8,
                "alpha_w_r2": 0.8,
                "f_alpha_w_r2": 0.81,
                "zeta_mean": 0.05,
                "measure_sum_m": 700,
                "reliable": 0,
            },
            {
                "mother_scale_m": 1000,
                "mother_ix": 0,
                "mother_iy": 0,
                "mother_centroid_x": 500,
                "mother_centroid_y": 500,
                "q": 4,
                "alpha_w": 1.4,
                "f_alpha_w": 1.3,
                "alpha_w_r2": 0.97,
                "f_alpha_w_r2": 0.98,
                "zeta_mean": 0.25,
                "measure_sum_m": 1200,
                "reliable": 1,
            },
        ],
    )
    _write_csv(
        tmp_path / "lineament_mother_structural_stats.csv",
        [
            {
                "mother_ix": 0,
                "mother_iy": 0,
                "mother_centroid_x": 500,
                "mother_centroid_y": 500,
                "mother_scale_m": 1000,
                "density_m_per_km2": 1200,
                "dominant_azimuth_deg": 85,
            }
        ],
    )

    outputs = export_mother_geopackage(tmp_path, crs="EPSG:3857", highlight_q=2)

    assert Path(outputs["geopackage"]).is_file()
    assert "mother_multifractal_q2" in outputs["layers"]
    assert "mother_multifractal_q2_reliable" in outputs["layers"]
    assert "mother_structural_stats" in outputs["layers"]

    import geopandas as gpd

    q2 = gpd.read_file(outputs["geopackage"], layer="mother_multifractal_q2")
    reliable = gpd.read_file(outputs["geopackage"], layer="mother_multifractal_q2_reliable")

    assert len(q2) == 2
    assert len(reliable) == 1
    assert q2.geometry.iloc[0].geom_type == "Polygon"
    assert q2.crs.to_epsg() == 3857
