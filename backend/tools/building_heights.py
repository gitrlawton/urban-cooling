"""
Building Heights Tool

Fetches 3D building data from OpenStreetMap for shade simulation.
"""

import requests
from typing import Dict, List

# Average floor height in meters
FLOOR_HEIGHT_METERS = 3.0

# Default height when no data available
DEFAULT_BUILDING_HEIGHT = 10.0


def fetch_building_heights(bbox: List[float]) -> Dict:
    """
    Fetch building footprints with height data from OpenStreetMap.

    Args:
        bbox: Bounding box [west, south, east, north] in degrees

    Returns:
        Dictionary containing:
            - buildings: List of building features with height data
            - bbox: Input bounding box
            - stats: Summary statistics

    Raises:
        ValueError: If bbox format is invalid or coordinates are out of range
        RuntimeError: If API request fails or response is malformed
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

    # Query for buildings with height or levels data
    query = f"""
    [out:json][timeout:60];
    (
      way["building"]({south},{west},{north},{east});
      relation["building"]({south},{west},{north},{east});
    );
    out body geom;
    """

    try:
        response = requests.post(
            overpass_url,
            data={"data": query},
            timeout=90
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("Overpass API request timed out after 90 seconds")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch building data from Overpass API: {e}")

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

    buildings = []
    heights_found = 0
    levels_found = 0
    estimated = 0

    for element in elements:
        tags = element.get("tags", {})
        geometry = element.get("geometry", [])

        if not geometry:
            continue

        # Try to get height from tags
        height = None
        height_source = "default"

        # Check for explicit height tag
        if "height" in tags:
            try:
                height_str = tags["height"].replace("m", "").strip()
                height = float(height_str)
                height_source = "height_tag"
                heights_found += 1
            except ValueError:
                pass

        # Fall back to building:levels
        if height is None and "building:levels" in tags:
            try:
                levels = int(tags["building:levels"])
                height = levels * FLOOR_HEIGHT_METERS
                height_source = "levels_tag"
                levels_found += 1
            except ValueError:
                pass

        # Default height for buildings without data
        if height is None:
            height = DEFAULT_BUILDING_HEIGHT
            height_source = "estimated"
            estimated += 1

        buildings.append({
            "id": element.get("id"),
            "type": tags.get("building", "yes"),
            "height": height,
            "height_source": height_source,
            "geometry": geometry,
            "name": tags.get("name")
        })

    return {
        "buildings": buildings,
        "bbox": bbox,
        "stats": {
            "total_buildings": len(buildings),
            "heights_from_tag": heights_found,
            "heights_from_levels": levels_found,
            "heights_estimated": estimated
        }
    }
