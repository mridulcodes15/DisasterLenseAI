from dataclasses import dataclass


@dataclass(frozen=True)
class FloodConfig:
    """
    Configuration used by the flood detection pipeline.
    """

    water_index: str = "mndwi"
    threshold: float = 0.0
    min_area_m2: float = 100.0


DEFAULT_FLOOD_CONFIG = FloodConfig()