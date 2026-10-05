from pathlib import Path
from typing import Any


import geopandas as gpd


def find_affected_roads(
    change_geometry: Any,
    roads_file: str | Path,
) -> list[Any]:
    """
    Find roads that intersect the detected change area.

    Parameters
    ----------
    change_geometry:
        Shapely geometry or a GeoJSON-like geometry representing
        the detected affected/change area.

    roads_file:
        Path to a roads GeoJSON file.

    Returns
    -------
    list[Any]
        List of road features that intersect the change area.
    """

    if change_geometry is None:
        return []

    roads_path = Path(roads_file)

    if not roads_path.exists():
        raise FileNotFoundError(
            f"Roads file not found: {roads_path}"
        )

    # Convert GeoJSON-like geometry to a GeoDataFrame if required.
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

    roads = gpd.read_file(roads_path)

    if roads.empty:
        return []

    # Make sure the roads have a CRS.
    if roads.crs is None:
        roads = roads.set_crs("EPSG:4326")

    # The demo change geometry is assumed to be EPSG:4326.
    change_gdf = gpd.GeoDataFrame(
        geometry=[geometry],
        crs="EPSG:4326",
    )

    # Reproject the change area to the roads CRS.
    if change_gdf.crs != roads.crs:
        change_gdf = change_gdf.to_crs(roads.crs)

    # Keep only roads that intersect the change area.
    affected_roads = roads[
        roads.geometry.intersects(change_gdf.geometry.iloc[0])
    ]

    return affected_roads.to_dict("records")