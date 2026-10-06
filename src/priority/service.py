from src.core.models import (
    ChangeResult,
    ContextResult,
    PriorityResult,
)

from .ranking import rank_priority_zones
from .zones import create_priority_zone


def build_priority(
    change_result: ChangeResult,
    context_result: ContextResult,
) -> PriorityResult:
    """
    Build emergency priority information from detected change
    and real-world context.
    """

    if change_result is None:
        raise ValueError("change_result is required.")

    if context_result is None:
        raise ValueError("context_result is required.")

    zone = create_priority_zone(
        change_result,
        context_result,
    )

    ranked_zones = rank_priority_zones([zone])

    priority_scores = {
        item.zone_id: item.priority_score
        for item in ranked_zones
    }

    reasons = {
        item.zone_id: "; ".join(item.reasons)
        for item in ranked_zones
    }

    confidence_values = [
        item.confidence
        for item in ranked_zones
    ]

    confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else None
    )

    return PriorityResult(
        disaster_type=change_result.disaster_type,
        zones=ranked_zones,
        priority_scores=priority_scores,
        confidence=confidence,
        reasons=reasons,
    )