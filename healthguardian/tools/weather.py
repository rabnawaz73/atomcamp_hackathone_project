import logging
from typing import Any

import requests

from healthguardian.config import get_settings

logger = logging.getLogger(__name__)


def _parse_weather_code(code: int) -> str:
    """Map WMO weather codes to human-readable strings."""
    if code == 0: return "Clear sky"
    if code in [1, 2, 3]: return "Mainly clear, partly cloudy, or overcast"
    if code in [45, 48]: return "Fog"
    if code in [51, 53, 55]: return "Drizzle"
    if code in [56, 57]: return "Freezing Drizzle"
    if code in [61, 63, 65]: return "Rain"
    if code in [66, 67]: return "Freezing Rain"
    if code in [71, 73, 75]: return "Snow fall"
    if code == 77: return "Snow grains"
    if code in [80, 81, 82]: return "Rain showers"
    if code in [85, 86]: return "Snow showers"
    if code == 95: return "Thunderstorm"
    if code in [96, 99]: return "Thunderstorm with heavy hail"
    return "Unknown"


def fetch_weather(lat: float, lon: float, city: str) -> dict[str, Any]:
    """Fetch current weather from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()["current"]
    
    return {
        "temperature_c": round(data["temperature_2m"], 1),
        "feels_like_c": round(data["apparent_temperature"], 1),
        "humidity": data["relative_humidity_2m"],
        "description": _parse_weather_code(data["weather_code"]),
        "wind_speed_ms": data["wind_speed_10m"],
        "uv_index": None,
        "source": "open-meteo",
    }


def fetch_air_quality(lat: float, lon: float) -> dict[str, Any]:
    """Fetch air quality index from Open-Meteo."""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "us_aqi",
        "timezone": "auto"
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    aqi = response.json()["current"]["us_aqi"]
    
    return {
        "aqi": aqi,
        "category": _aqi_category(aqi),
        "dominant_pollutant": "PM2.5/O3/etc",
        "source": "open-meteo",
    }


def build_city_report(city_override: str | None = None) -> dict[str, Any]:
    """Build a complete city environment report."""
    from healthguardian.tools.geolocation import get_location_from_ip, geocode_city

    if city_override:
        geo = geocode_city(city_override)
        if geo:
            location = geo
            location["source"] = "user_override_geocoded"
        else:
            location = get_location_from_ip()
            location["city"] = city_override
            location["source"] = "user_override_fallback"
    else:
        location = get_location_from_ip()

    lat = location.get("lat") or 51.5074
    lon = location.get("lon") or -0.1278
    city = location.get("city", "Unknown City")

    weather = fetch_weather(lat, lon, city)
    air_quality = fetch_air_quality(lat, lon)

    outdoor_safe = (
        "rain" not in weather.get("description", "").lower()
        and "thunderstorm" not in weather.get("description", "").lower()
        and "snow" not in weather.get("description", "").lower()
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



