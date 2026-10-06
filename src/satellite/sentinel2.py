from dataclasses import dataclass
from typing import Optional


@dataclass
class Sentinel2Scene:
    """
    Metadata describing a Sentinel-2 scene.
    """

    scene_id: str
    acquisition_date: str
    cloud_cover: Optional[float] = None
    processing_level: Optional[str] = None
    source_url: Optional[str] = None


def create_scene(
    scene_id: str,
    acquisition_date: str,
    cloud_cover: Optional[float] = None,
    processing_level: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Sentinel2Scene:
    """
    Create a validated Sentinel-2 scene description.
    """
    if not scene_id.strip():
        raise ValueError("Scene ID cannot be empty.")

    if not acquisition_date.strip():
        raise ValueError("Acquisition date cannot be empty.")

    if cloud_cover is not None and not 0.0 <= cloud_cover <= 100.0:
        raise ValueError("Cloud cover must be between 0 and 100.")

    return Sentinel2Scene(
        scene_id=scene_id,
        acquisition_date=acquisition_date,
        cloud_cover=cloud_cover,
        processing_level=processing_level,
        source_url=source_url,
    )