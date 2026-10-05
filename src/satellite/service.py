from pathlib import Path
from typing import Optional

import rasterio
from pyproj import CRS, Transformer
from shapely.ops import transform as shapely_transform

from src.core.models import ChangeResult
from src.satellite.change_detection import detect_change, mask_to_geometry
from src.satellite.confidence import calculate_confidence
from src.satellite.preprocessing import load_raster
from src.satellite.registration import align_images


def _calculate_area_km2(
    geometry,
    crs,
) -> float:
    """
    Calculate geometry area in square kilometres.

    If the source CRS is projected, the geometry is transformed to
    an appropriate metre-based CRS when necessary.

    If the source CRS is geographic (latitude/longitude), the
    geometry is transformed to a local UTM CRS before calculating area.
    """
    if geometry is None:
        return 0.0

    if crs is None:
        raise ValueError(
            "Raster CRS is required to calculate affected area."
        )

    source_crs = CRS.from_user_input(crs)

    if source_crs.is_projected:
        area_m2 = geometry.area
        return float(area_m2 / 1_000_000)

    if not source_crs.is_geographic:
        raise ValueError(
            f"Unsupported CRS type for area calculation: {source_crs}"
        )

    centroid = geometry.centroid

    longitude = centroid.x
    latitude = centroid.y

    zone = int((longitude + 180) // 6) + 1

    if latitude >= 0:
        utm_epsg = 32600 + zone
    else:
        utm_epsg = 32700 + zone

    utm_crs = CRS.from_epsg(utm_epsg)

    transformer = Transformer.from_crs(
        source_crs,
        utm_crs,
        always_xy=True,
    )

    projected_geometry = shapely_transform(
        transformer.transform,
        geometry,
    )

    area_m2 = projected_geometry.area

    return float(area_m2 / 1_000_000)


def analyze_change(
    before_path: str | Path,
    after_path: str | Path,
    hazard: str,
    threshold: float,
    pre_date: Optional[str] = None,
    post_date: Optional[str] = None,
    sensor: Optional[str] = None,
) -> ChangeResult:
    """
    Run the complete satellite change-detection pipeline.

    Returns:
        ChangeResult containing the detected change geometry,
        affected area, dates, sensor information, and confidence.
    """
    before, before_metadata = load_raster(before_path)
    after, _ = load_raster(after_path)

    before, after = align_images(before, after)

    change_mask, change_percentage = detect_change(
        before,
        after,
        threshold,
    )

    confidence = calculate_confidence(
        before,
        after,
        change_mask,
        threshold,
    )

    transform = before_metadata["transform"]

    change_geometry = mask_to_geometry(
        change_mask,
        transform,
    )

    affected_area_km2 = None

    if change_geometry is not None:
        affected_area_km2 = _calculate_area_km2(
            change_geometry,
            before_metadata.get("crs"),
        )

    warnings = []

    if change_percentage == 0.0:
        warnings.append("No significant change detected.")

    return ChangeResult(
        status="success",
        disaster_type=hazard,
        change_geometry=change_geometry,
        affected_area_km2=affected_area_km2,
        pre_date=pre_date,
        post_date=post_date,
        sensor=sensor,
        confidence=confidence,
        warnings=warnings,
        sources=[
            str(before_path),
            str(after_path),
        ],
    )
