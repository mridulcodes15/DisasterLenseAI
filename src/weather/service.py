
from datetime import datetime, timedelta
from typing import Any

from .client import fetch_historical_weather, fetch_live_weather
from .rainfall import summarize_rainfall


def get_weather_context(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Existing historical weather context; retained for past incidents."""
    raw_weather = fetch_historical_weather(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    rainfall_summary = summarize_rainfall(raw_weather)

    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "rainfall": rainfall_summary,
        "source": "Open-Meteo Historical Weather API",
    }


def get_live_weather_context(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """Create a live monitoring snapshot from Open-Meteo."""
    raw = fetch_live_weather(latitude, longitude)

    current = raw.get("current") or {}
    hourly = raw.get("hourly") or {}
    daily = raw.get("daily") or {}

    current_time = current.get("time")
    if not current_time:
        raise ValueError("Missing current weather observation time.")

    try:
        now = datetime.fromisoformat(current_time)
    except (TypeError, ValueError):
        raise ValueError("Invalid current weather timestamp.") from None

    times = hourly.get("time") or []
    rainfall = hourly.get("precipitation") or []
    probabilities = hourly.get("precipitation_probability") or []

    recent_24h = 0.0
    recent_hours_available = 0
    forecast_24h = 0.0
    forecast_hours_available = 0
    forecast_probabilities: list[float] = []

    for index, timestamp in enumerate(times):
        try:
            hour = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError):
            continue

        amount = rainfall[index] if index < len(rainfall) else None

        if amount is not None:
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                continue

            if amount < 0:
                continue

            if now - timedelta(hours=24) < hour <= now:
                recent_24h += amount
                recent_hours_available += 1

            if now < hour <= now + timedelta(hours=24):
                forecast_24h += amount
                forecast_hours_available += 1

        probability = (
            probabilities[index]
            if index < len(probabilities)
            else None
        )

        if probability is not None and now < hour <= now + timedelta(hours=24):
            try:
                probability = float(probability)
            except (TypeError, ValueError):
                continue

            if 0 <= probability <= 100:
                forecast_probabilities.append(probability)

    daily_times = daily.get("time") or []
    daily_rainfall = daily.get("precipitation_sum") or []
    daily_probabilities = (
        daily.get("precipitation_probability_max") or []
    )
    daily_codes = daily.get("weather_code") or []

    daily_forecast: list[dict[str, Any]] = []

    for index, date in enumerate(daily_times):
        # Past-day data is useful for recent rainfall but not a forecast.
        if date < now.date().isoformat():
            continue

        daily_forecast.append(
            {
                "date": date,
                "precipitation_sum_mm": (
                    daily_rainfall[index]
                    if index < len(daily_rainfall)
                    else None
                ),
                "precipitation_probability_max": (
                    daily_probabilities[index]
                    if index < len(daily_probabilities)
                    else None
                ),
                "weather_code": (
                    daily_codes[index]
                    if index < len(daily_codes)
                    else None
                ),
            }
        )

    return {
        "mode": "live_monitoring",
        "latitude": latitude,
        "longitude": longitude,
        "observed_at": current_time,
        "timezone": raw.get("timezone"),
        "location": raw.get("location") or {},
        "current": current,
        "recent_24h_rainfall_mm": round(recent_24h, 2),
        "recent_24h_hours_available": recent_hours_available,
        "forecast_next_24h_rainfall_mm": round(forecast_24h, 2),
        "forecast_next_24h_hours_available": forecast_hours_available,
        "forecast_next_24h_precipitation_probability_max": (
            max(forecast_probabilities)
            if forecast_probabilities
            else None
        ),
        "daily_forecast": daily_forecast,
        "source": raw.get("source", "Open-Meteo Forecast API"),
        "warning": (
            "Weather-model data supports situational awareness; "
            "it does not establish flood occurrence or route safety."
        ),
    }
