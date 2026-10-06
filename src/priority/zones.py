from typing import Any

from src.core.models import ChangeResult, ContextResult, PriorityZone

from .scoring import calculate_priority_score


def create_priority_zone(
    change_result: ChangeResult,
    context_result: ContextResult,
) -> PriorityZone:
    """
    Create a priority zone from the detected disaster area
    and its real-world context.
    """

    geometry = change_result.change_geometry

    if geometry is None:
        raise ValueError(
            "ChangeResult.change_geometry is required "
            "to create a priority zone."
        )

    priority_score, reasons = calculate_priority_score(
        change_result,
        context_result,
    )

    roads = len(context_result.affected_roads)
    bridges = len(context_result.affected_bridges)
    hospitals = len(context_result.affected_hospitals)

    infrastructure_count = roads + bridges + hospitals

    population_exposed = (
        context_result.population_exposed
        if context_result.population_exposed is not None
        else 0.0
    )

    confidence = (
        change_result.confidence
        if change_result.confidence is not None
        else 0.0
    )

    if 0.0 <= confidence <= 1.0:
        confidence *= 100

    return PriorityZone(
        zone_id="zone-1",
        geometry=geometry,
        priority_score=priority_score,
        confidence=confidence,
        population_exposed=float(population_exposed),
        infrastructure_count=infrastructure_count,
        reasons=reasons,
    )