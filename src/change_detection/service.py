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
    Load the persisted satellite-derived change geometry and expose it
    through the shared ChangeResult contract.

    The GeoJSON polygons are the actual detected flood extent produced
    by the satellite pipeline. The AOI is not used as the change geometry.
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

    return ChangeResult(
        status="success",
        disaster_type=metadata.get("disaster_type", "flood"),
        pre_date=metadata.get("pre_date"),
        post_date=metadata.get("post_date"),
        sensor=metadata.get("sensor"),
        change_geometry=change_geometry,
        affected_area_km2=metadata.get("affected_area_km2"),
        confidence=metadata.get("confidence"),
        warnings=metadata.get("warnings", []),
        sources=[str(extent_path)],
    )
