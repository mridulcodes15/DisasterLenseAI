from typing import Any


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """Keep a score inside the expected 0-100 range."""
    return max(minimum, min(value, maximum))


def _population_score(population_exposed: float | None) -> float:
    """
    Convert exposed population into a 0-100 score.

    Uses a logarithmic scale so large populations do not completely
    dominate the other evidence factors.
    """
    if population_exposed is None or population_exposed <= 0:
        return 0.0

    import math

    score = math.log10(population_exposed + 1) / math.log10(10001) * 100
    return _clamp(score)


def _infrastructure_score(context: Any) -> float:
    """Score exposed infrastructure using real detected assets."""

    roads = len(getattr(context, "affected_roads", []) or [])
    bridges = len(getattr(context, "affected_bridges", []) or [])
    hospitals = len(getattr(context, "affected_hospitals", []) or [])

    # Hospitals and bridges receive higher importance than individual roads.
    weighted_assets = (
        roads
        + (bridges * 3)
        + (hospitals * 5)
    )

    if weighted_assets <= 0:
        return 0.0

    # 100 weighted assets represents maximum infrastructure exposure.
    return _clamp(weighted_assets / 100 * 100)


def _area_score(context: Any) -> float:
    """Score the percentage of the AOI affected by the disaster."""

    percentage = getattr(context, "affected_percentage", None)

    if percentage is None or percentage <= 0:
        return 0.0

    # 20% or more of the AOI affected is treated as maximum area exposure.
    return _clamp((percentage / 20.0) * 100)


def _severity_score(change_result: Any) -> float:
    """Convert the detector severity into a 0-100 score."""

    severity = getattr(change_result, "severity", None)

    if severity is None:
        return 0.0

    try:
        severity = float(severity)
    except (TypeError, ValueError):
        return 0.0

    # Support either a 0-1 or 0-100 severity representation.
    if 0.0 <= severity <= 1.0:
        severity *= 100

    return _clamp(severity)


def _confidence_score(change_result: Any) -> float:
    """Convert detection confidence into a 0-100 score."""

    confidence = getattr(change_result, "confidence", None)

    if confidence is None:
        return 0.0

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return 0.0

    if 0.0 <= confidence <= 1.0:
        confidence *= 100

    return _clamp(confidence)


def calculate_priority_score(
    change_result: Any,
    context_result: Any,
) -> tuple[float, list[str]]:
    """
    Calculate an explainable emergency priority score.

    Returns:
        (priority_score, reasons)
    """

    population = _population_score(
        getattr(context_result, "population_exposed", None)
    )

    infrastructure = _infrastructure_score(context_result)

    area = _area_score(context_result)

    severity = _severity_score(change_result)

    confidence = _confidence_score(change_result)

    score = (
        population * 0.40
        + infrastructure * 0.25
        + area * 0.15
        + severity * 0.10
        + confidence * 0.10
    )

    score = round(_clamp(score), 2)

    roads = len(getattr(context_result, "affected_roads", []) or [])
    bridges = len(getattr(context_result, "affected_bridges", []) or [])
    hospitals = len(getattr(context_result, "affected_hospitals", []) or [])
    population_exposed = getattr(
        context_result,
        "population_exposed",
        None,
    )

    reasons = []

    if population_exposed and population_exposed > 0:
        reasons.append(
            f"{population_exposed:.2f} people estimated exposed"
        )

    if roads:
        reasons.append(f"{roads} affected roads")

    if bridges:
        reasons.append(f"{bridges} affected bridges")

    if hospitals:
        reasons.append(f"{hospitals} affected hospitals")

    affected_percentage = getattr(
        context_result,
        "affected_percentage",
        None,
    )

    if affected_percentage is not None:
        reasons.append(
            f"{affected_percentage:.2f}% of the AOI affected"
        )

    if severity > 0:
        reasons.append(
            f"change severity score: {severity:.2f}"
        )

    if confidence > 0:
        reasons.append(
            f"detection confidence: {confidence:.2f}"
        )

    return score, reasons