
from typing import Any

from src.core.models import ContextResult


def extract_rainfall_evidence(
    context_result: ContextResult,
) -> dict[str, Any]:
    """
    Extract historical rainfall evidence from the context pipeline.

    Reads the actual structure returned by src/weather/service.py.
    Does not generate or assume rainfall measurements.
    """

    weather = context_result.weather or {}
    rainfall = weather.get("rainfall", {}) or {}

    return {
        "total_rainfall_mm": rainfall.get("total_rainfall_mm"),
        "max_daily_rainfall_mm": rainfall.get("max_daily_rainfall_mm"),
        "peak_rainfall_date": rainfall.get("peak_rainfall_date"),
        "daily_rainfall": rainfall.get("daily_rainfall", []),
        "start_date": weather.get("start_date"),
        "end_date": weather.get("end_date"),
        "source": weather.get("source"),
    }
