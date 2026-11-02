import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pyproj import CRS
from shapely.ops import unary_union

script = Path(__file__).resolve().parents[1] / "scripts/run_author_benchmarks.py"
spec = importlib.util.spec_from_file_location("author_benchmarks", script)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_published_lattice_construction_count_and_unique_length():
    for level in (0, 1, 2, 3):
        lines = benchmark.roy_lattice(level)
        assert len(lines) == 3 ** (level + 1) - 1
        assert unary_union(lines).length == pytest.approx(sum(line.length for line in lines))


def test_source_raster_vectorization_is_explicit_and_counts_unrepresented_pixels(tmp_path):
    pixels = np.full((10, 10), 255, dtype=np.uint8)
    pixels[4, 1:9] = 0
    pixels[1:9, 5] = 0
    pixels[0, 0] = 0
    source = tmp_path / "cross.bmp"
    Image.fromarray(pixels).save(source)
    lines, domain, info, ink = benchmark.bitmap_centerlines(source)
    assert len(lines) == 2
    assert info["unrepresented_black_pixels"] == 1
    assert info["threshold"] == 128
    assert sum(line.length for line in lines) == pytest.approx(14 * benchmark.SIDE / 10)
    assert all(domain.covers(line) for line in lines)
    assert int(ink.sum()) == 16


def test_unlocated_model_crs_is_not_an_invented_epsg_geolocation():
    crs = CRS.from_wkt(benchmark.CRS_WKT)
    assert crs.is_projected
    assert crs.to_epsg() is None
    assert "UNLOCATED" in crs.name
    assert crs.axis_info[0].unit_conversion_factor == 1


def test_analytic_cantor_targets_and_unavailable_finite_interval():
    d = np.log(2) / np.log(3)
    for q in (-2, -1, 0, 1, 2):
        values = benchmark.expected_cantor(q, .5)
        assert values["dq"] == pytest.approx(d)
        assert values["alpha"] == pytest.approx(d)
        assert values["f_alpha"] == pytest.approx(d)
        assert values["tau"] == pytest.approx((q - 1) * d)
    no_range = benchmark.raster_capacity(np.ones((10, 10), bool), 8, 2)
    assert no_range["dimension"] is None
    assert not no_range["pixel_sizes"]
