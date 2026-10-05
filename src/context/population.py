from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping


def estimate_population_exposed(
    change_geometry: Any,
    population_raster: str | Path,
) -> Optional[float]:
    """
    Estimate population exposed inside a detected change geometry.

    Assumption:
    The population raster stores population count per pixel/cell.

    Parameters
    ----------
    change_geometry:
        Shapely geometry or a GeoJSON-like geometry representing
        the detected affected/change area.

    population_raster:
        Path to the population raster (.tif).

    Returns
    -------
    Optional[float]
        Estimated population exposed inside the change area.
        Returns None when the input geometry or raster cannot be used.
    """

    if change_geometry is None:
        return None

    raster_path = Path(population_raster)

    if not raster_path.exists():
        raise FileNotFoundError(
            f"Population raster not found: {raster_path}"
        )

    # Convert GeoJSON-like geometry to a Shapely geometry if required.
    if isinstance(change_geometry, dict):
        geometry = gpd.GeoSeries.from_features(
            [{"type": "Feature", "geometry": change_geometry}]
        ).iloc[0]
    else:
        geometry = change_geometry

    if geometry is None or geometry.is_empty:
        return None

    if not geometry.is_valid:
        geometry = geometry.buffer(0)

    with rasterio.open(raster_path) as src:
        # Population raster and change geometry must use the same CRS.
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

        population_values = clipped[0]

        if population_values.count() == 0:
            return 0.0

        # Ignore NoData values.
        valid_values = population_values.compressed()

        # Population count per pixel → sum exposed population.
        exposed_population = float(valid_values.sum())

    return exposed_population