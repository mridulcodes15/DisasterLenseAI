import json
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

from src.core.models import ChangeResult


DEFAULT_FLOOD_EXTENT = Path("data/demo/flood/flood_extent.geojson")


def load_change_result(
    extent_path: str | Path = DEFAULT_FLOOD_EXTENT,
) -> ChangeResult:
    """
    Load a supplied change extent through the shared ChangeResult contract.

    The bundled default GeoJSON is prepared demo geometry. Its embedded
    dates, sensor, area, and confidence are not verified satellite evidence.
    Custom extents are passed through with their supplied metadata.
    """
    extent_path = Path(extent_path)

    if not extent_path.exists():
        raise FileNotFoundError(
            f"Flood extent file not found: {extent_path}"
        )

    with extent_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("type") != "FeatureCollection":
        raise ValueError(
            "Change extent must be a GeoJSON FeatureCollection."
        )

    metadata = data.get("metadata", {})
    is_bundled_demo = extent_path.resolve() == DEFAULT_FLOOD_EXTENT.resolve()
    features = data.get("features", [])

    geometries = [
        shape(feature["geometry"])
        for feature in features
        if feature.get("geometry")
    ]

    if not geometries:
        raise ValueError(
            "Change extent contains no valid geometries."
        )

    change_geometry = unary_union(geometries)

    warnings = list(metadata.get("warnings", []))
    if is_bundled_demo:
        warnings.append(
            "Prepared demo geometry only; embedded dates, sensor, area and "
            "confidence are unverified and must not be presented as "
            "satellite-detected output."
        )

    return ChangeResult(
        status="demo_unverified" if is_bundled_demo else "success",
        disaster_type=metadata.get("disaster_type", "flood"),
        pre_date=None if is_bundled_demo else metadata.get("pre_date"),
        post_date=None if is_bundled_demo else metadata.get("post_date"),
        sensor=None if is_bundled_demo else metadata.get("sensor"),
        change_geometry=change_geometry,
        affected_area_km2=(None if is_bundled_demo else metadata.get("affected_area_km2")),
        confidence=None if is_bundled_demo else metadata.get("confidence"),
        warnings=warnings,
        sources=[str(extent_path)],
    )
