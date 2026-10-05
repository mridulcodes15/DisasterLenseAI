from dataclasses import dataclass
from typing import Optional


@dataclass
class Sentinel1Scene:
    """
    Metadata describing a Sentinel-1 scene.
    """

    scene_id: str
    acquisition_date: str
    orbit: Optional[str] = None
    polarization: Optional[str] = None
    product_type: Optional[str] = None
    source_url: Optional[str] = None


def create_scene(
    scene_id: str,
    acquisition_date: str,
    orbit: Optional[str] = None,
    polarization: Optional[str] = None,
    product_type: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Sentinel1Scene:
    """
    Create a validated Sentinel-1 scene description.
    """
    if not scene_id.strip():
        raise ValueError("Scene ID cannot be empty.")

    if not acquisition_date.strip():
        raise ValueError("Acquisition date cannot be empty.")

    return Sentinel1Scene(
        scene_id=scene_id,
        acquisition_date=acquisition_date,
        orbit=orbit,
        polarization=polarization,
        product_type=product_type,
        source_url=source_url,
    )