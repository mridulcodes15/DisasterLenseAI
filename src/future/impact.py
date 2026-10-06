
from typing import Any

from src.core.models import ContextResult, PriorityResult

from .forecast import extract_rainfall_evidence


def assess_future_impact(
    context_result: ContextResult,
    priority_result: PriorityResult,
) -> dict[str, Any]:
    """
    Assess evidence indicators associated with potential future impact.

    Uses observed historical rainfall, official alerts, and the
    priority engine's output. This is an evidence-based heuristic,
    not a trained future-disaster prediction model.
    """

    rainfall = extract_rainfall_evidence(context_result)

    total_rainfall = rainfall["total_rainfall_mm"]
    max_daily_rainfall = rainfall["max_daily_rainfall_mm"]

    alerts = context_result.alerts or []

    # Normalize official alert severity to an indicator from 0 to 1.
    alert_levels = {
        "low": 0.25,
        "moderate": 0.50,
        "high": 0.75,
        "very_high": 0.90,
        "extremely_high": 1.0,
    }

    alert_factors = []

    for alert in alerts:
        if not isinstance(alert, dict):
            continue

        severity = str(alert.get("severity", "")).strip().lower()

        if severity in alert_levels:
            alert_factors.append(alert_levels[severity])

    alert_factor = max(alert_factors) if alert_factors else None

    # Rainfall indicator: scale historical measurements against
    # explicit reference levels. These are scoring thresholds,
    # not forecasts or official flood-warning thresholds.
    rainfall_factor = None

    if total_rainfall is not None and max_daily_rainfall is not None:
        total_factor = min(max(float(total_rainfall), 0.0) / 200.0, 1.0)
        daily_factor = min(max(float(max_daily_rainfall), 0.0) / 100.0, 1.0)

        rainfall_factor = round(
            (total_factor + daily_factor) / 2.0,
            3,
        )

    priority_scores = list(
        (priority_result.priority_scores or {}).values()
    )

    highest_priority = max(priority_scores) if priority_scores else None

    affected_zones = [
        zone.zone_id
        for zone in priority_result.zones
    ]

    assumptions = [
        "Historical rainfall describes the supplied event period, not future rainfall.",
        "Rainfall reference levels are heuristic scoring thresholds, not official warning thresholds.",
        "Official alert severity is used only when present in the supplied alert data.",
        "No trained predictive model or future weather forecast is used by this assessment.",
    ]

    return {
        "rainfall": rainfall,
        "rainfall_factor": rainfall_factor,
        "alert_factor": alert_factor,
        "highest_priority_score": highest_priority,
        "affected_zones": affected_zones,
        "assumptions": assumptions,
    }
