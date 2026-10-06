
from datetime import datetime, timedelta

import pytest

from src.weather import client
from src.weather import service
from src.future.live_risk import assess_live_weather_risk


def test_fetch_live_weather_normalizes_open_meteo_response(monkeypatch):
    now = datetime(2026, 10, 6, 12, 0)

    mock_data = {
        "latitude": 27.66,
        "longitude": 85.30,
        "timezone": "Asia/Kathmandu",
        "current": {
            "time": now.isoformat(),
            "temperature_2m": 24.0,
            "precipitation": 0.2,
        },
        "hourly": {
            "time": [now.isoformat()],
            "precipitation": [0.2],
            "precipitation_probability": [40],
            "temperature_2m": [24.0],
        },
        "daily": {
            "time": ["2026-10-06"],
            "precipitation_sum": [8.5],
            "precipitation_probability_max": [60],
            "weather_code": [61],
        },
    }

    def fake_get_json(url, params):
        assert url == client.FORECAST_BASE_URL
        assert params["past_days"] == 1
        assert params["forecast_days"] == 3
        assert params["timezone"] == "auto"
        return mock_data

    monkeypatch.setattr(client, "_get_json", fake_get_json)

    result = client.fetch_live_weather(27.66, 85.30)

    assert result["source"] == "Open-Meteo Forecast API"
    assert result["current"]["temperature_2m"] == 24.0
    assert result["hourly"]["precipitation"] == [0.2]
    assert result["daily"]["precipitation_sum"] == [8.5]


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 0), (0, 181), (-91, 0), (0, -181)],
)
def test_fetch_live_weather_rejects_invalid_coordinates(
    latitude, longitude
):
    with pytest.raises(ValueError):
        client.fetch_live_weather(latitude, longitude)


def test_live_weather_context_calculates_recent_and_forecast_rainfall(
    monkeypatch,
):
    now = datetime(2026, 10, 6, 12, 0)
    times = [
        (now - timedelta(hours=hour)).isoformat()
        for hour in range(24, -1, -1)
    ] + [
        (now + timedelta(hours=hour)).isoformat()
        for hour in range(1, 25)
    ]

    raw = {
        "current": {
            "time": now.isoformat(),
            "temperature_2m": 24.0,
        },
        "hourly": {
            "time": times,
            "precipitation": [1.0] * len(times),
            "precipitation_probability": [50] * len(times),
        },
        "daily": {
            "time": ["2026-10-05", "2026-10-06", "2026-10-07"],
            "precipitation_sum": [20.0, 10.0, 15.0],
            "precipitation_probability_max": [80, 60, 70],
            "weather_code": [61, 61, 61],
        },
        "timezone": "Asia/Kathmandu",
        "source": "Open-Meteo Forecast API",
    }

    monkeypatch.setattr(service, "fetch_live_weather", lambda *_: raw)

    result = service.get_live_weather_context(27.66, 85.30)

    assert result["recent_24h_rainfall_mm"] == 24.0
    assert result["forecast_next_24h_rainfall_mm"] == 24.0
    assert result["recent_24h_hours_available"] == 24
    assert result["forecast_next_24h_hours_available"] == 24
    assert result["forecast_next_24h_precipitation_probability_max"] == 50.0
    assert all(
        day["date"] >= "2026-10-06"
        for day in result["daily_forecast"]
    )


def test_live_risk_reports_insufficient_hourly_coverage():
    result = assess_live_weather_risk({
        "recent_24h_rainfall_mm": 80,
        "forecast_next_24h_rainfall_mm": 90,
        "recent_24h_hours_available": 10,
        "forecast_next_24h_hours_available": 24,
    })

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["score"] is None


def test_live_risk_returns_indicator_for_sufficient_data():
    result = assess_live_weather_risk({
        "recent_24h_rainfall_mm": 120,
        "forecast_next_24h_rainfall_mm": 110,
        "forecast_next_24h_precipitation_probability_max": 80,
        "recent_24h_hours_available": 24,
        "forecast_next_24h_hours_available": 24,
        "source": "Open-Meteo Forecast API",
    })

    assert result["status"] == "OK"
    assert result["score"] == 5
    assert result["indicator"] == "HIGH_WEATHER_CONCERN"
    assert result["is_validated_flood_prediction"] is False
