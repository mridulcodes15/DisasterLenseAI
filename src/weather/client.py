import requests


BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Fetch real historical weather data from Open-Meteo.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum",
        "timezone": "Asia/Kathmandu",
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()