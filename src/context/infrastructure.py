from pathlib import Path
from typing import Any

from .bridges import find_affected_bridges
from .hospitals import find_affected_hospitals
from .roads import find_affected_roads


def analyze_infrastructure(
    change_geometry: Any,
    roads_file: str | Path,
    bridges_file: str | Path,
    hospitals_file: str | Path,
) -> dict[str, Any]:
    """
    Analyze infrastructure affected by the detected disaster area.

    Uses the existing asset-specific detectors for roads, bridges,
    and hospitals and returns their real detected features.
    """

    roads = find_affected_roads(
        change_geometry,
        roads_file,
    )

    bridges = find_affected_bridges(
        change_geometry,
        bridges_file,
    )

    hospitals = find_affected_hospitals(
        change_geometry,
        hospitals_file,
    )

    return {
        "roads": roads,
        "bridges": bridges,
        "hospitals": hospitals,
        "total_affected_assets": (
            len(roads)
            + len(bridges)
            + len(hospitals)
        ),
    }