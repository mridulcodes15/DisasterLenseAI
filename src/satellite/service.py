from pathlib import Path
from typing import Optional

import numpy as np
import rasterio

from src.core.models import ChangeResult
from src.satellite.change_detection import detect_change, mask_to_geometry
from src.satellite.confidence import calculate_confidence
from src.satellite.preprocessing import load_raster
from src.satellite.registration import align_images


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
        pixel_width = abs(transform.a)
        pixel_height = abs(transform.e)

        area_m2 = change_geometry.area * pixel_width * pixel_height
        affected_area_km2 = float(area_m2 / 1_000_000)

    warnings = []

    if change_percentage == 0.0:
        warnings.append("No significant change detected.")

    return ChangeResult(
        status="success",
        hazard=hazard,
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