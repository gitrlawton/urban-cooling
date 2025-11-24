import requests
from typing import Dict, List


def fetch_land_use_data(bbox: List[float]) -> Dict:
    """
    Fetch land use data from OpenStreetMap Overpass API.

    Args:
        bbox: Bounding box as [west, south, east, north] in decimal degrees

    Returns:
        Dictionary containing categorized land use features (buildings, parks, water, forests)

    Raises:
        ValueError: If bbox format is invalid or coordinates are out of range
        requests.RequestException: If API request fails
        RuntimeError: If API response is malformed or empty
    """
    # Validate bbox format
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError(f"bbox must be a list of 4 floats, got: {bbox}")

    try:
        west, south, east, north = [float(coord) for coord in bbox]
    except (TypeError, ValueError) as e:
        raise ValueError(f"bbox coordinates must be numeric: {e}")

    # Validate coordinate ranges
    if not (-180 <= west <= 180) or not (-180 <= east <= 180):
        raise ValueError(f"Longitude values must be between -180 and 180, got: west={west}, east={east}")
    if not (-90 <= south <= 90) or not (-90 <= north <= 90):
        raise ValueError(f"Latitude values must be between -90 and 90, got: south={south}, north={north}")
    if west >= east:
        raise ValueError(f"West longitude ({west}) must be less than east longitude ({east})")
    if south >= north:
        raise ValueError(f"South latitude ({south}) must be less than north latitude ({north})")

    overpass_url = "https://overpass-api.de/api/interpreter"

    # Overpass QL query for buildings, parks, water, forests
    query = f"""
    [out:json];
    (
      way["building"]({south},{west},{north},{east});
      way["leisure"="park"]({south},{west},{north},{east});
      way["natural"="water"]({south},{west},{north},{east});
      way["landuse"="forest"]({south},{west},{north},{east});
    );
    out geom;
    """

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=30  # 30 second timeout
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Overpass API request timed out after 30 seconds")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch land use data from Overpass API: {e}")

    try:
        data = response.json()
    except ValueError as e:
        raise RuntimeError(f"Invalid JSON response from Overpass API: {e}")

    # Validate response structure
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected JSON object from Overpass API, got: {type(data)}")

    if "elements" not in data:
        raise RuntimeError("Overpass API response missing 'elements' field")

    elements = data["elements"]
    if not isinstance(elements, list):
        raise RuntimeError(f"Expected 'elements' to be a list, got: {type(elements)}")

    # Organize by type
    buildings = [e for e in elements if e.get("tags", {}).get("building")]
    parks = [e for e in elements if e.get("tags", {}).get("leisure") == "park"]
    water = [e for e in elements if e.get("tags", {}).get("natural") == "water"]
    forests = [e for e in elements if e.get("tags", {}).get("landuse") == "forest"]

    return {
        "buildings": buildings,
        "parks": parks,
        "water": water,
        "forests": forests,
        "bbox": bbox,
        "total_elements": len(elements)
    }
