from pathlib import Path
from typing import Any

import geopandas as gpd


def find_affected_hospitals(
    change_geometry: Any,
    hospitals_file: str | Path,
) -> list[Any]:
    """
    Find hospitals that intersect the detected change area.
    """

    if change_geometry is None:
        return []

    hospitals_path = Path(hospitals_file)

    if not hospitals_path.exists():
        raise FileNotFoundError(
            f"Hospitals file not found: {hospitals_path}"
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
        return []

    if not geometry.is_valid:
        geometry = geometry.buffer(0)

    hospitals = gpd.read_file(hospitals_path)

    if hospitals.empty:
        return []

    if hospitals.crs is None:
        hospitals = hospitals.set_crs("EPSG:4326")

    change_gdf = gpd.GeoDataFrame(
        geometry=[geometry],
        crs="EPSG:4326",
    )

    if change_gdf.crs != hospitals.crs:
        change_gdf = change_gdf.to_crs(hospitals.crs)

    affected_hospitals = hospitals[
        hospitals.geometry.intersects(
            change_gdf.geometry.iloc[0]
        )
    ]

    return affected_hospitals.to_dict("records")