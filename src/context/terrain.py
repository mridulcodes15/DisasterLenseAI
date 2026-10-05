from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping


def analyze_terrain(
    change_geometry: Any,
    dem_raster: str | Path,
) -> dict[str, float | None]:
    """
    Analyze elevation statistics inside the detected change area
    using a real DEM raster.
    """

    if change_geometry is None:
        return {
            "min_elevation_m": None,
            "max_elevation_m": None,
            "mean_elevation_m": None,
        }

    dem_path = Path(dem_raster)

    if not dem_path.exists():
        raise FileNotFoundError(
            f"DEM raster not found: {dem_path}"
        )

    if isinstance(change_geometry, dict):
        change_gdf = gpd.GeoDataFrame.from_features(
            [{"type": "Feature", "geometry": change_geometry}],
            crs="EPSG:4326",
        )
        geometry = change_gdf.geometry.iloc[0]
    else:
        geometry = change_geometry

    if geometry is None or geometry.is_empty:
        return {
            "min_elevation_m": None,
            "max_elevation_m": None,
            "mean_elevation_m": None,
        }

    if not geometry.is_valid:
        geometry = geometry.buffer(0)

    with rasterio.open(dem_path) as src:

        change_gdf = gpd.GeoDataFrame(
            geometry=[geometry],
            crs="EPSG:4326",
        )

        if change_gdf.crs != src.crs:
            change_gdf = change_gdf.to_crs(src.crs)

        clipped, _ = mask(
            src,
            [mapping(change_gdf.geometry.iloc[0])],
            crop=True,
            filled=False,
        )

        values = clipped[0].compressed()

        values = values[
            np.isfinite(values)
        ]

        if len(values) == 0:
            return {
                "min_elevation_m": None,
                "max_elevation_m": None,
                "mean_elevation_m": None,
            }

        return {
            "min_elevation_m": round(
                float(values.min()),
                2,
            ),
            "max_elevation_m": round(
                float(values.max()),
                2,
            ),
            "mean_elevation_m": round(
                float(values.mean()),
                2,
            ),
        }