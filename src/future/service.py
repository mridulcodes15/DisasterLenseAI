
from src.core.models import ContextResult, FutureImpact, PriorityResult
from .impact import assess_future_impact


def build_future_impact(
    context_result: ContextResult,
    priority_result: PriorityResult,
) -> FutureImpact:
    """Build a future-impact assessment from existing pipeline evidence."""
    if context_result is None:
        raise ValueError("context_result is required.")
    if priority_result is None:
        raise ValueError("priority_result is required.")

    assessment = assess_future_impact(context_result, priority_result)

    rainfall_factor = assessment["rainfall_factor"]
    alert_factor = assessment["alert_factor"]

    # Evidence-based indicator, not a trained prediction.
    indicators = [
        factor
        for factor in (rainfall_factor, alert_factor)
        if factor is not None
    ]

    if not indicators:
        severity = "UNKNOWN"
    else:
        combined_indicator = max(indicators)

        if combined_indicator >= 0.85:
            severity = "HIGH"
        elif combined_indicator >= 0.50:
            severity = "MODERATE"
        else:
            severity = "LOW"

    # This is not a statistically calibrated model confidence.
    evidence_count = sum(
        value is not None
        for value in (rainfall_factor, alert_factor)
    )
    confidence = evidence_count / 2 if evidence_count else 0.0

    return FutureImpact(
        severity=severity,
        affected_zones=assessment["affected_zones"],
        rainfall_factor=rainfall_factor,
        alert_factor=alert_factor,
        confidence=confidence,
        assumptions=assessment["assumptions"],
    )
