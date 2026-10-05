from pathlib import Path
from typing import Any

import geopandas as gpd


def find_affected_bridges(
    change_geometry: Any,
    bridges_file: str | Path,
) -> list[Any]:
    """
    Find bridges that intersect the detected change area.
    """

    if change_geometry is None:
        return []

    bridges_path = Path(bridges_file)

    if not bridges_path.exists():
        raise FileNotFoundError(
            f"Bridges file not found: {bridges_path}"
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

    bridges = gpd.read_file(bridges_path)

    if bridges.empty:
        return []

    if bridges.crs is None:
        bridges = bridges.set_crs("EPSG:4326")

    change_gdf = gpd.GeoDataFrame(
        geometry=[geometry],
        crs="EPSG:4326",
    )

    if change_gdf.crs != bridges.crs:
        change_gdf = change_gdf.to_crs(bridges.crs)

    affected_bridges = bridges[
        bridges.geometry.intersects(
            change_gdf.geometry.iloc[0]
        )
    ]

    return affected_bridges.to_dict("records")