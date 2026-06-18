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
        if data.get("status") != "success":
            raise ValueError(data.get("message", "Geolocation failed"))
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
        logger.warning("IP geolocation failed: %s", exc)
        return {
            "city": "London",
            "region": "England",
            "country": "United Kingdom",
            "lat": 51.5074,
            "lon": -0.1278,
            "timezone": "Europe/London",
            "source": "fallback",
        }
