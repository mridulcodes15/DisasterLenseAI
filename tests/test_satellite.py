import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.satellite.catalog import create_scene_pair
from src.satellite.change_detection import (
    calculate_difference,
    detect_change,
    mask_to_geometry,
)
from src.satellite.confidence import calculate_confidence
from src.satellite.sentinel1 import create_scene as create_sentinel1_scene
from src.satellite.sentinel2 import create_scene as create_sentinel2_scene
from src.satellite.service import analyze_change


def test_calculate_difference():
    before = np.zeros((5, 5), dtype=np.float32)
    after = np.zeros((5, 5), dtype=np.float32)

    after[1:3, 1:3] = 10

    difference = calculate_difference(before, after)

    assert difference.shape == (5, 5)
    assert np.all(difference[1:3, 1:3] == 10)
    assert np.all(difference[0, :] == 0)


def test_detect_change():
    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((10, 10), dtype=np.float32)

    after[2:5, 2:5] = 10

    change_mask, change_percentage = detect_change(
        before,
        after,
        threshold=5,
    )

    assert change_mask.shape == (10, 10)
    assert np.count_nonzero(change_mask) == 9
    assert change_percentage == 9.0


def test_detect_change_rejects_mismatched_shapes():
    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((8, 8), dtype=np.float32)

    with pytest.raises(ValueError):
        detect_change(before, after, threshold=5)


def test_mask_to_geometry():
    change_mask = np.zeros((10, 10), dtype=bool)
    change_mask[2:5, 2:5] = True

    transform = from_origin(0, 10, 1, 1)

    geometry = mask_to_geometry(
        change_mask,
        transform,
    )

    assert geometry is not None
    assert geometry.geom_type == "Polygon"
    assert geometry.area == 9.0


def test_mask_to_geometry_returns_none_for_no_change():
    change_mask = np.zeros((10, 10), dtype=bool)

    transform = from_origin(0, 10, 1, 1)

    geometry = mask_to_geometry(
        change_mask,
        transform,
    )

    assert geometry is None


def test_calculate_confidence():
    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((10, 10), dtype=np.float32)

    after[2:5, 2:5] = 10

    change_mask, _ = detect_change(
        before,
        after,
        threshold=5,
    )

    confidence = calculate_confidence(
        before,
        after,
        change_mask,
        threshold=5,
    )

    assert confidence == pytest.approx(2 / 3)


def test_calculate_confidence_returns_zero_for_no_change():
    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((10, 10), dtype=np.float32)

    change_mask = np.zeros((10, 10), dtype=bool)

    confidence = calculate_confidence(
        before,
        after,
        change_mask,
        threshold=5,
    )

    assert confidence == 0.0


def test_create_sentinel1_scene():
    scene = create_sentinel1_scene(
        scene_id="S1_TEST_001",
        acquisition_date="2026-10-01",
        orbit="ascending",
        polarization="VV",
        product_type="GRD",
    )

    assert scene.scene_id == "S1_TEST_001"
    assert scene.acquisition_date == "2026-10-01"
    assert scene.orbit == "ascending"
    assert scene.polarization == "VV"
    assert scene.product_type == "GRD"


def test_create_sentinel1_scene_rejects_empty_scene_id():
    with pytest.raises(ValueError):
        create_sentinel1_scene(
            scene_id="",
            acquisition_date="2026-10-01",
        )


def test_create_sentinel2_scene():
    scene = create_sentinel2_scene(
        scene_id="S2_TEST_001",
        acquisition_date="2026-10-01",
        cloud_cover=12.5,
        processing_level="Level-2A",
    )

    assert scene.scene_id == "S2_TEST_001"
    assert scene.acquisition_date == "2026-10-01"
    assert scene.cloud_cover == 12.5
    assert scene.processing_level == "Level-2A"


def test_create_sentinel2_scene_rejects_invalid_cloud_cover():
    with pytest.raises(ValueError):
        create_sentinel2_scene(
            scene_id="S2_TEST_001",
            acquisition_date="2026-10-01",
            cloud_cover=120.0,
        )


def test_create_scene_pair():
    before = create_sentinel2_scene(
        scene_id="S2_BEFORE",
        acquisition_date="2026-09-01",
    )

    after = create_sentinel2_scene(
        scene_id="S2_AFTER",
        acquisition_date="2026-10-01",
    )

    pair = create_scene_pair(before, after)

    assert pair.before.scene_id == "S2_BEFORE"
    assert pair.after.scene_id == "S2_AFTER"


def test_create_scene_pair_rejects_mixed_sensors():
    before = create_sentinel1_scene(
        scene_id="S1_BEFORE",
        acquisition_date="2026-09-01",
    )

    after = create_sentinel2_scene(
        scene_id="S2_AFTER",
        acquisition_date="2026-10-01",
    )

    with pytest.raises(ValueError):
        create_scene_pair(before, after)


def test_analyze_change(tmp_path):
    transform = from_origin(0, 10, 1, 1)

    metadata = {
        "driver": "GTiff",
        "height": 10,
        "width": 10,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:3857",
        "transform": transform,
    }

    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((10, 10), dtype=np.float32)

    after[2:5, 2:5] = 10

    before_path = tmp_path / "before.tif"
    after_path = tmp_path / "after.tif"

    with rasterio.open(before_path, "w", **metadata) as dst:
        dst.write(before, 1)

    with rasterio.open(after_path, "w", **metadata) as dst:
        dst.write(after, 1)

    result = analyze_change(
        before_path=before_path,
        after_path=after_path,
        hazard="flood",
        threshold=5,
        pre_date="2026-09-01",
        post_date="2026-10-01",
        sensor="Sentinel-2",
    )

    assert result.status == "success"
    assert result.disaster_type == "flood"
    assert result.change_geometry is not None
    assert result.change_geometry.geom_type == "Polygon"
    assert result.affected_area_km2 == pytest.approx(9e-06)
    assert result.confidence == pytest.approx(2 / 3)
    assert result.pre_date == "2026-09-01"
    assert result.post_date == "2026-10-01"
    assert result.sensor == "Sentinel-2"


def test_analyze_change_with_geographic_crs(tmp_path):
    """
    Verify that affected area is calculated correctly when
    the raster uses latitude/longitude coordinates.
    """
    transform = from_origin(
        85.30,
        27.75,
        0.001,
        0.001,
    )

    metadata = {
        "driver": "GTiff",
        "height": 10,
        "width": 10,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
    }

    before = np.zeros((10, 10), dtype=np.float32)
    after = np.zeros((10, 10), dtype=np.float32)

    after[2:5, 2:5] = 10

    before_path = tmp_path / "before_geographic.tif"
    after_path = tmp_path / "after_geographic.tif"

    with rasterio.open(before_path, "w", **metadata) as dst:
        dst.write(before, 1)

    with rasterio.open(after_path, "w", **metadata) as dst:
        dst.write(after, 1)

    result = analyze_change(
        before_path=before_path,
        after_path=after_path,
        hazard="flood",
        threshold=5,
        pre_date="2026-09-01",
        post_date="2026-10-01",
        sensor="Sentinel-2",
    )

    assert result.status == "success"
    assert result.change_geometry is not None
    assert result.affected_area_km2 is not None
    assert result.affected_area_km2 > 0
