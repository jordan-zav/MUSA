import json

import numpy as np
import pytest

from musa import MUSA
from musa.control import AnalysisCancelled
from musa.workflow import RunConfig, execute_analysis


def _analyzer():
    from shapely.geometry import LineString, box

    rng = np.random.default_rng(24)
    lines = [LineString([(0, float(y)), (1000, float(y + 30))]) for y in rng.uniform(0, 960, 25)]
    return MUSA.from_line_geometries(lines, box(0, 0, 1000, 1000), "EPSG:32718")


def test_native_geometry_adapter_matches_original_gis_core():
    gpd = pytest.importorskip("geopandas")
    native = _analyzer()
    data = gpd.GeoDataFrame(geometry=native._line_geometries, crs="EPSG:32718")
    boundary = gpd.GeoDataFrame(geometry=[native._boundary_geom], crs=data.crs)
    original = MUSA(data, boundary=boundary, q_values=[0, 1, 2])
    native.q_values = original.q_values
    kwargs = dict(resolutions_m=[1000, 500, 250, 125, 62.5], min_r2=0)
    a, b = native.run_analysis(**kwargs), original.run_analysis(**kwargs)
    np.testing.assert_allclose(a.dq, b.dq)
    np.testing.assert_allclose(a.alpha, b.alpha)
    np.testing.assert_allclose(a.f_alpha, b.f_alpha)


def test_workflow_manifest_cancellation_and_collision(tmp_path):
    config = RunConfig(
        mother_cell_m=1000,
        divisors=(2, 4, 8, 16),
        q_min=0,
        q_max=2,
        local=False,
        structural=False,
        plots=False,
        gis=False,
        min_r2=0,
    )
    restored = RunConfig.from_recipe(json.loads(json.dumps(config.recipe())))
    np.testing.assert_array_equal(restored.q_values(), [0, 1, 2])
    target = tmp_path / "complete"
    manifest = execute_analysis(_analyzer(), restored, target)
    assert manifest["status"] == "complete"
    assert manifest["files"]["analysis_report.csv"]
    before = (target / "run_manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        execute_analysis(_analyzer(), config, target)
    assert (target / "run_manifest.json").read_bytes() == before
    checks = 0

    def cancelled():
        nonlocal checks
        checks += 1
        return checks >= 4

    with pytest.raises(AnalysisCancelled):
        execute_analysis(_analyzer(), config, tmp_path / "cancelled", cancelled=cancelled)
    assert json.loads((tmp_path / "cancelled/run_manifest.json").read_text())["status"] == "cancelled"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"q_step": 0},
        {"min_r2": 1},
        {"divisors": (2, 4, 8)},
        {"mother_cell_m": float("nan")},
        {"local": "false"},
        {"bootstrap_iterations": -1},
    ],
)
def test_invalid_configuration_fails_before_creating_output(tmp_path, kwargs):
    with pytest.raises(ValueError):
        execute_analysis(_analyzer(), RunConfig(**kwargs), tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()
