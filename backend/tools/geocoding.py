"""
Geocoding Tool

Converts city names or zip codes to geographic coordinates and bounding boxes.
Uses Nominatim (OpenStreetMap) - free, no API key needed.
"""

import requests
from typing import Dict


def geocode_location(city_or_zip: str) -> Dict:
    """
    Convert city name or zip code to geographic coordinates.

    Args:
        city_or_zip: City name (e.g., "San Francisco, CA") or zip code (e.g., "94102")

    Returns:
        Dictionary containing:
            - location_name: Full display name of the location
            - bbox: Bounding box [west, south, east, north] in degrees
            - center: Center coordinates {"lat": float, "lon": float}

    Raises:
        ValueError: If location not found or input is invalid
        requests.RequestException: If API request fails

    Example:
        >>> result = geocode_location("San Francisco, CA")
        >>> print(result["center"])
        {"lat": 37.7749, "lon": -122.4194}
    """
    # Validate input
    if not city_or_zip or not city_or_zip.strip():
        raise ValueError("Location input cannot be empty")

    city_or_zip = city_or_zip.strip()

    # Nominatim API endpoint
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": city_or_zip,
        "format": "json",
        "limit": 1,
        "countrycodes": "us"  # Restrict to US locations
    }
    headers = {
        "User-Agent": "ShadePlan/1.0"  # Required by Nominatim usage policy
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        raise requests.RequestException(f"Request timed out while geocoding: {city_or_zip}")
    except requests.RequestException as e:
        raise requests.RequestException(f"Failed to geocode location: {str(e)}")

    results = response.json()

    if not results:
        raise ValueError(f"Location not found: {city_or_zip}")

    location = results[0]

    try:
        lat = float(location["lat"])
        lon = float(location["lon"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid coordinates in API response: {str(e)}")

    # Calculate bounding box (approx 10km x 10km)
    # 1 degree latitude ≈ 111 km
    # At mid-latitudes, 1 degree longitude ≈ 85-100 km
    # delta of 0.045 degrees ≈ 5 km
    delta = 0.045

    return {
        "location_name": location.get("display_name", city_or_zip),
        "bbox": [
            lon - delta,  # west
            lat - delta,  # south
            lon + delta,  # east
            lat + delta   # north
        ],
        "center": {
            "lat": lat,
            "lon": lon
        }
    }
