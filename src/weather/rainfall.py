from typing import Any


def summarize_rainfall(weather_data: dict[str, Any]) -> dict[str, Any]:
    """
    Summarize historical rainfall data returned by Open-Meteo.
    """

    daily = weather_data.get("daily", {})

    dates = daily.get("time", [])
    precipitation = daily.get("precipitation_sum", [])

    if not dates or not precipitation:
        return {
            "total_rainfall_mm": 0.0,
            "max_daily_rainfall_mm": 0.0,
            "peak_rainfall_date": None,
            "daily_rainfall": [],
        }

    rainfall_values = [
        float(value or 0.0)
        for value in precipitation
    ]

    total_rainfall = sum(rainfall_values)
    max_rainfall = max(rainfall_values)

    peak_index = rainfall_values.index(max_rainfall)

    daily_rainfall = [
        {
            "date": date,
            "rainfall_mm": rainfall,
        }
        for date, rainfall in zip(
            dates,
            rainfall_values,
        )
    ]

    return {
        "total_rainfall_mm": round(total_rainfall, 2),
        "max_daily_rainfall_mm": round(max_rainfall, 2),
        "peak_rainfall_date": dates[peak_index],
        "daily_rainfall": daily_rainfall,
    }