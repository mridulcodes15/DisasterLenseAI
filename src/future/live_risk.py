
from typing import Any


def assess_live_weather_risk(
    live_weather: dict[str, Any],
) -> dict[str, Any]:
    """Calculate a transparent, preliminary weather-concern indicator."""
    alerts = live_weather.get("alerts") or []

    def unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "INSUFFICIENT_DATA",
            "score": None,
            "indicator": "UNAVAILABLE",
            "reasons": [reason],
            "official_alerts": alerts,
            "source": live_weather.get("source"),
            "is_validated_flood_prediction": False,
        }

    recent = live_weather.get("recent_24h_rainfall_mm")
    forecast = live_weather.get("forecast_next_24h_rainfall_mm")
    probability = live_weather.get(
        "forecast_next_24h_precipitation_probability_max"
    )

    if recent is None or forecast is None:
        return unavailable("Recent or forecast rainfall data is missing.")

    try:
        recent = float(recent)
        forecast = float(forecast)
    except (TypeError, ValueError):
        return unavailable("Rainfall data is invalid.")

    if recent < 0 or forecast < 0:
        return unavailable("Rainfall cannot be negative.")

    try:
        recent_hours = int(live_weather.get("recent_24h_hours_available", 0))
        forecast_hours = int(
            live_weather.get("forecast_next_24h_hours_available", 0)
        )
    except (TypeError, ValueError):
        return unavailable("Hourly data coverage is invalid.")

    if recent_hours < 18 or forecast_hours < 18:
        return unavailable(
            "Insufficient hourly coverage for the 24-hour windows."
        )

    if probability is not None:
        try:
            probability = float(probability)
        except (TypeError, ValueError):
            probability = None

        if probability is not None and not 0 <= probability <= 100:
            probability = None

    score = 0
    reasons: list[str] = []

    # Illustrative thresholds only. Validate these before operational use.
    if recent >= 100:
        score += 2
        reasons.append("High recent 24-hour rainfall.")
    elif recent >= 50:
        score += 1
        reasons.append("Elevated recent 24-hour rainfall.")

    if forecast >= 100:
        score += 2
        reasons.append("High forecast 24-hour rainfall.")
    elif forecast >= 50:
        score += 1
        reasons.append("Elevated forecast 24-hour rainfall.")

    if probability is not None and probability >= 70:
        score += 1
        reasons.append("High provider-estimated probability of precipitation.")

    if score >= 4:
        indicator = "HIGH_WEATHER_CONCERN"
    elif score >= 2:
        indicator = "MODERATE_WEATHER_CONCERN"
    else:
        indicator = "LOWER_WEATHER_CONCERN"

    if not reasons:
        reasons.append(
            "Configured rainfall and precipitation-probability "
            "thresholds were not reached."
        )

    return {
        "status": "OK",
        "score": score,
        "indicator": indicator,
        "reasons": reasons,
        "recent_24h_rainfall_mm": round(recent, 2),
        "forecast_next_24h_rainfall_mm": round(forecast, 2),
        "forecast_next_24h_precipitation_probability_max": probability,
        "official_alerts": alerts,
        "source": live_weather.get("source", "Open-Meteo Forecast API"),
        "is_validated_flood_prediction": False,
        "warning": (
            "Illustrative weather indicator only, not a validated flood "
            "forecast. Consult official local disaster alerts."
        ),
    }
