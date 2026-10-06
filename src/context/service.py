from pathlib import Path
from typing import Any

import geopandas as gpd
from shapely.geometry import shape

from src.core.models import ContextResult
from src.weather.service import get_weather_context
from src.alerts.service import get_relevant_flood_alerts

from .population import estimate_population_exposed
from .roads import find_affected_roads
from .bridges import find_affected_bridges
from .hospitals import find_affected_hospitals
from .terrain import analyze_terrain


def build_context(
    change_geometry: Any,
    population_raster: str | Path,
    roads_file: str | Path,
    bridges_file: str | Path,
    hospitals_file: str | Path,
    terrain_raster: str | Path,
    dhm_report_text: str | Path,
    basin_name: str,
    weather_start_date: str,
    weather_end_date: str,
    aoi_file: str | Path,
) -> ContextResult:
    """
    Build real context evidence for the detected disaster area.
    """

    if isinstance(change_geometry, dict):
        geometry = shape(change_geometry)
    else:
        geometry = change_geometry

    if geometry is None or geometry.is_empty:
        raise ValueError("change_geometry is empty")

    # Load the real AOI geometry.
    aoi = gpd.read_file(aoi_file)

    if aoi.empty:
        raise ValueError(f"AOI file contains no features: {aoi_file}")

    if aoi.crs is None:
        raise ValueError("AOI must have a defined CRS.")

    # Calculate real AOI area in km².
    aoi_area_km2 = float(
        aoi.to_crs(6933).geometry.area.sum() / 1_000_000
    )

    # Calculate real affected area in km².
    affected_area_km2 = float(
        gpd.GeoSeries([geometry], crs=aoi.crs)
        .to_crs(6933)
        .area.iloc[0]
        / 1_000_000
    )

    # Calculate percentage of AOI affected.
    affected_percentage = (
        affected_area_km2 / aoi_area_km2 * 100
        if aoi_area_km2 > 0
        else None
    )

    centroid = geometry.centroid

    population_exposed = estimate_population_exposed(
        geometry,
        population_raster,
    )

    affected_roads = find_affected_roads(
        geometry,
        roads_file,
    )

    affected_bridges = find_affected_bridges(
        geometry,
        bridges_file,
    )

    affected_hospitals = find_affected_hospitals(
        geometry,
        hospitals_file,
    )

    terrain = analyze_terrain(
        geometry,
        terrain_raster,
    )

    weather = get_weather_context(
        latitude=centroid.y,
        longitude=centroid.x,
        start_date=weather_start_date,
        end_date=weather_end_date,
    )

    alerts = get_relevant_flood_alerts(
        str(dhm_report_text),
        basin_name,
    )

    return ContextResult(
        aoi_area_km2=aoi_area_km2,
        affected_area_km2=affected_area_km2,
        affected_percentage=affected_percentage,
        population_exposed=population_exposed,
        affected_roads=affected_roads,
        affected_bridges=affected_bridges,
        affected_hospitals=affected_hospitals,
        weather=weather,
        terrain=terrain,
        alerts=alerts,
        sources=[
            "AOI GeoJSON",
            "WorldPop population raster",
            "OpenStreetMap",
            "Open-Meteo Historical Weather API",
            "Copernicus Digital Elevation Model GLO-90",
            "Government of Nepal - Department of Hydrology and Meteorology",
        ],
    )