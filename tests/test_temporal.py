import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.change_detection.service import load_change_result
from src.change_detection.temporal import compare_sar_backscatter


def _write_raster(path, values, *, transform=None):
    values = np.asarray(values, dtype="float32")
    profile = {
        "driver": "GTiff",
        "height": values.shape[0],
        "width": values.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32645",
        "transform": transform or from_origin(500000, 3100000, 10, 10),
        "nodata": -9999,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(values, 1)


def test_compare_sar_backscatter_writes_candidate_mask_and_geojson(tmp_path):
    before = np.full((8, 8), -10, dtype="float32")
    after = before.copy()
    after[2:4, 3:5] = -20
    after[0, 0] = -20  # Isolated candidate removed by min_pixels.
    before[7, 7] = -9999  # Nodata is excluded from valid pixels.
    after[7, 7] = -20
    before_path, after_path = tmp_path / "before.tif", tmp_path / "after.tif"
    _write_raster(before_path, before)
    _write_raster(after_path, after)

    result = compare_sar_backscatter(
        before_path, after_path, output_dir=tmp_path / "out", min_pixels=4
    )

    assert result["candidate_pixels"] == 4
    assert result["valid_pixels"] == 63
    assert result["feature_count"] == 1
    assert result["validated_flood"] is False
    with rasterio.open(result["mask_path"]) as mask:
        assert mask.read(1).sum() == 4
        assert mask.dtypes == ("uint8",)
    geojson = json.loads((tmp_path / "out" / "candidate_change_extent.geojson").read_text())
    assert geojson["metadata"]["validated_flood"] is False
    assert geojson["features"][0]["properties"]["validated_flood"] is False


def test_compare_sar_backscatter_rejects_different_grids(tmp_path):
    values = np.zeros((4, 4), dtype="float32")
    before_path, after_path = tmp_path / "before.tif", tmp_path / "after.tif"
    _write_raster(before_path, values)
    _write_raster(after_path, values, transform=from_origin(500010, 3100000, 10, 10))

    with pytest.raises(ValueError, match="not aligned"):
        compare_sar_backscatter(before_path, after_path, output_dir=tmp_path / "out")


def test_bundled_demo_extent_is_not_reported_as_satellite_detection():
    demo_path = "data/demo/flood/flood_extent.geojson"
    result = load_change_result(demo_path)

    assert result.status == "demo_unverified"
    assert result.change_geometry is not None
    assert result.pre_date is None
    assert result.post_date is None
    assert result.sensor is None
    assert result.affected_area_km2 is None
    assert result.confidence is None
    assert any("Prepared demo geometry only" in warning for warning in result.warnings)
