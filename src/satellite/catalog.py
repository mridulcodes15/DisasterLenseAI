from dataclasses import dataclass
from typing import Optional

from src.satellite.sentinel1 import Sentinel1Scene
from src.satellite.sentinel2 import Sentinel2Scene


@dataclass
class ScenePair:
    """
    A before/after pair of satellite scenes.
    """

    before: Sentinel1Scene | Sentinel2Scene
    after: Sentinel1Scene | Sentinel2Scene


def create_scene_pair(
    before: Sentinel1Scene | Sentinel2Scene,
    after: Sentinel1Scene | Sentinel2Scene,
) -> ScenePair:
    """
    Create a validated before/after satellite scene pair.
    """
    if type(before) is not type(after):
        raise ValueError(
            "Before and after scenes must use the same satellite sensor."
        )

    if before.scene_id == after.scene_id:
        raise ValueError(
            "Before and after scenes must have different scene IDs."
        )

    if before.acquisition_date == after.acquisition_date:
        raise ValueError(
            "Before and after scenes must have different acquisition dates."
        )

    return ScenePair(
        before=before,
        after=after,
    )