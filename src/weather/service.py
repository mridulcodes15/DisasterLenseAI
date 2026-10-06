from typing import Any

from .client import fetch_historical_weather
from .rainfall import summarize_rainfall


def get_weather_context(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """
    Fetch and summarize historical weather context
    for the disaster event area.
    """

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