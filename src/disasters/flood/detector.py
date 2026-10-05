from pathlib import Path
from typing import Any

import geopandas as gpd

from src.core.models import ChangeResult


def detect_flood_from_extent(
    flood_extent_file: str | Path,
    pre_date: str | None = None,
    post_date: str | None = None,
    sensor: str | None = None,
) -> ChangeResult:
    """
    Build a ChangeResult from an externally generated flood extent.

    The flood extent must come from the actual flood-detection
    pipeline/data source. This function does not fabricate
    satellite observations.
    """

    path = Path(flood_extent_file)

    if not path.exists():
        raise FileNotFoundError(
            f"Flood extent file not found: {path}"
        )

    flood = gpd.read_file(path)

    if flood.empty:
        raise ValueError(
            f"Flood extent file contains no features: {path}"
        )

    if flood.crs is None:
        raise ValueError(
            "Flood extent must have a defined CRS."
        )

    geometry = flood.geometry.union_all()

    if geometry is None or geometry.is_empty:
        raise ValueError(
            "Flood extent contains no valid geometry."
        )

    # Calculate area in a projected CRS suitable for area measurement.
    area_km2 = float(
        flood.to_crs(6933).geometry.area.sum() / 1_000_000
    )

    return ChangeResult(
        status="detected",
        disaster_type="flood",
        pre_date=pre_date,
        post_date=post_date,
        sensor=sensor,
        change_geometry=geometry,
        affected_area_km2=area_km2,
        confidence=None,
        image_refs=[],
        warnings=[],
        sources=[
            "Flood extent GeoJSON",
        ],
    )