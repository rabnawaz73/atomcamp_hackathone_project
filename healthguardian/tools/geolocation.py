import logging
from typing import Any
import requests

logger = logging.getLogger(__name__)


def get_location_from_ip() -> dict[str, Any]:
    """Detect city and coordinates from the server's public IP."""
    try:
        response = requests.get("http://ip-api.com/json/", timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            return {
                "city": data.get("city", "Unknown"),
                "region": data.get("regionName", ""),
                "country": data.get("country", ""),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone", "UTC"),
                "source": "ip-api",
            }
    except Exception as exc:
        logger.warning("ip-api.com failed: %s", exc)

    # Fallback to ipinfo.io if ip-api.com is blocked
    try:
        response = requests.get("https://ipinfo.io/json", timeout=8)
        response.raise_for_status()
        data = response.json()
        loc = data.get("loc", "51.5074,-0.1278").split(",")
        return {
            "city": data.get("city", "Unknown"),
            "region": data.get("region", ""),
            "country": data.get("country", ""),
            "lat": float(loc[0]),
            "lon": float(loc[1]),
            "timezone": data.get("timezone", "UTC"),
            "source": "ipinfo",
        }
    except Exception as exc:
        logger.warning("ipinfo.io failed: %s", exc)

    return {
        "city": "London",
        "region": "England",
        "country": "United Kingdom",
        "lat": 51.5074,
        "lon": -0.1278,
        "timezone": "Europe/London",
        "source": "fallback",
    }


def geocode_city(city_name: str) -> dict[str, Any] | None:
    """Get latitude and longitude for a city name using Open-Meteo."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city_name, "count": 1, "format": "json"}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "city": result.get("name"),
                "country": result.get("country"),
                "lat": result.get("latitude"),
                "lon": result.get("longitude"),
                "timezone": result.get("timezone"),
                "source": "open-meteo-geocoding"
            }
    except Exception as exc:
        logger.error("Geocoding failed for %s: %s", city_name, exc)
    
    return None
