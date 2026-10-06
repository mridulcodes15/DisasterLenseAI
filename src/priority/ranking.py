from collections.abc import Sequence

from src.core.models import PriorityZone


def rank_priority_zones(
    zones: Sequence[PriorityZone],
) -> list[PriorityZone]:
    """
    Rank priority zones from highest to lowest priority score.

    Does not modify the original sequence.
    """

    return sorted(
        zones,
        key=lambda zone: zone.priority_score,
        reverse=True,
    )