
from typing import Any

import requests


HISTORICAL_BASE_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)
FORECAST_BASE_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 30


def _get_json(
    url: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Request JSON safely and report useful errors without secrets."""
    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Weather request failed: {type(exc).__name__}"
        ) from None
    except ValueError:
        raise RuntimeError(
            "Weather provider returned invalid JSON."
        ) from None

    if not isinstance(data, dict):
        raise RuntimeError(
            "Weather provider returned an unexpected response."
        )

    if "error" in data and data["error"]:
        reason = data.get("reason", "Unknown provider error")
        raise RuntimeError(f"Weather provider error: {reason}")

    return data


def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Preserve the existing historical-weather interface."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum",
        "timezone": "Asia/Kathmandu",
    }

    return _get_json(HISTORICAL_BASE_URL, params)


def fetch_live_weather(
    latitude: float,
    longitude: float,
) -> dict[str, Any]:
    """
    Fetch current conditions, hourly rainfall and forecast data.

    Includes one past day of hourly data, so the service can calculate
    recent rainfall without a separate API request or API key.
    """
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "rain,"
            "showers,"
            "weather_code,"
            "wind_speed_10m,"
            "wind_gusts_10m"
        ),
        "hourly": (
            "precipitation,"
            "precipitation_probability,"
            "temperature_2m"
        ),
        "daily": (
            "precipitation_sum,"
            "precipitation_probability_max,"
            "weather_code"
        ),
        "past_days": 1,
        "forecast_days": 3,
        "timezone": "auto",
    }

    data = _get_json(FORECAST_BASE_URL, params)

    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    daily = data.get("daily") or {}

    if not current.get("time"):
        raise RuntimeError(
            "Weather provider response is missing current observation time."
        )

    hourly_times = hourly.get("time") or []
    hourly_precipitation = hourly.get("precipitation") or []
    hourly_probability = (
        hourly.get("precipitation_probability") or []
    )
    hourly_temperature = hourly.get("temperature_2m") or []

    if not hourly_times or not hourly_precipitation:
        raise RuntimeError(
            "Weather provider response is missing hourly rainfall data."
        )

    return {
        "current": current,
        "hourly": {
            "time": hourly_times,
            "precipitation": hourly_precipitation,
            "precipitation_probability": hourly_probability,
            "temperature_2m": hourly_temperature,
        },
        "daily": {
            "time": daily.get("time") or [],
            "precipitation_sum": daily.get("precipitation_sum") or [],
            "precipitation_probability_max": (
                daily.get("precipitation_probability_max") or []
            ),
            "weather_code": daily.get("weather_code") or [],
        },
        "timezone": data.get("timezone"),
        "location": {
            "latitude": data.get("latitude", latitude),
            "longitude": data.get("longitude", longitude),
            "elevation": data.get("elevation"),
        },
        "source": "Open-Meteo Forecast API",
    }
