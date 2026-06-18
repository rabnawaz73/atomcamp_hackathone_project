import logging
from typing import Any

import requests

from healthguardian.config import get_settings

logger = logging.getLogger(__name__)


def fetch_weather(lat: float, lon: float, city: str) -> dict[str, Any]:
    """Fetch current weather from OpenWeatherMap."""
    settings = get_settings()
    if not settings.openweathermap_api_key:
        return _mock_weather(city)

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": settings.openweathermap_api_key,
            "units": "metric",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "temperature_c": round(data["main"]["temp"], 1),
            "feels_like_c": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].title(),
            "wind_speed_ms": data["wind"]["speed"],
            "uv_index": None,
            "source": "openweathermap",
        }
    except Exception as exc:
        logger.warning("Weather fetch failed: %s", exc)
        return _mock_weather(city)


def fetch_air_quality(lat: float, lon: float) -> dict[str, Any]:
    """Fetch air quality index from WAQI or OpenWeatherMap."""
    settings = get_settings()

    if settings.waqi_api_key:
        try:
            url = f"https://api.waqi.info/feed/geo:{lat};{lon}/"
            response = requests.get(url, params={"token": settings.waqi_api_key}, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "ok":
                aqi = data["data"]["aqi"]
                return {
                    "aqi": aqi,
                    "category": _aqi_category(aqi),
                    "dominant_pollutant": data["data"].get("dominentpol", "N/A"),
                    "source": "waqi",
                }
        except Exception as exc:
            logger.warning("WAQI fetch failed: %s", exc)

    if settings.openweathermap_api_key:
        try:
            url = "https://api.openweathermap.org/data/2.5/air_pollution"
            params = {"lat": lat, "lon": lon, "appid": settings.openweathermap_api_key}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            pollution = response.json()["list"][0]
            aqi = pollution["main"]["aqi"] * 20
            return {
                "aqi": aqi,
                "category": _aqi_category(aqi),
                "dominant_pollutant": "PM2.5",
                "source": "openweathermap",
            }
        except Exception as exc:
            logger.warning("Air quality fetch failed: %s", exc)

    return {"aqi": 42, "category": "Good", "dominant_pollutant": "N/A", "source": "mock"}


def build_city_report(city_override: str | None = None) -> dict[str, Any]:
    """Build a complete city environment report."""
    from healthguardian.tools.geolocation import get_location_from_ip

    location = get_location_from_ip()
    if city_override:
        location["city"] = city_override
        location["source"] = "user_override"

    lat = location.get("lat") or 51.5074
    lon = location.get("lon") or -0.1278
    city = location["city"]

    weather = fetch_weather(lat, lon, city)
    air_quality = fetch_air_quality(lat, lon)

    outdoor_safe = (
        weather.get("description", "").lower() not in ("rain", "thunderstorm", "snow")
        and air_quality.get("aqi", 100) < 100
    )

    return {
        "location": location,
        "weather": weather,
        "air_quality": air_quality,
        "pollen_count": "Low",
        "outdoor_exercise_recommended": outdoor_safe,
        "lifestyle_notes": (
            f"Typical diet in {city} includes local seasonal produce. "
            f"Consider morning walks when AQI is {air_quality.get('category', 'moderate')}."
        ),
    }


def _aqi_category(aqi: int | float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    return "Very Unhealthy"


def _mock_weather(city: str) -> dict[str, Any]:
    return {
        "temperature_c": 22.0,
        "feels_like_c": 21.0,
        "humidity": 55,
        "description": "Partly Cloudy",
        "wind_speed_ms": 3.5,
        "uv_index": 5,
        "source": "mock",
    }
