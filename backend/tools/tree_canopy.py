"""
Tree Canopy Tool

Fetches existing tree coverage data from OpenStreetMap.
"""

import requests
from typing import Dict, List

# Default canopy radius in meters by tree type
CANOPY_RADIUS = {
    "default": 4.0,
    "oak": 8.0,
    "maple": 6.0,
    "pine": 4.0,
    "palm": 3.0,
    "small": 2.5,
    "large": 10.0
}


def fetch_tree_canopy_data(bbox: List[float]) -> Dict:
    """
    Fetch existing tree canopy data from OpenStreetMap.

    Args:
        bbox: Bounding box [west, south, east, north] in degrees

    Returns:
        Dictionary containing:
            - trees: List of individual trees with canopy data
            - wooded_areas: List of forest/wood polygons
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

    # Query for trees, tree rows, and wooded areas
    query = f"""
    [out:json][timeout:60];
    (
      node["natural"="tree"]({south},{west},{north},{east});
      way["natural"="tree_row"]({south},{west},{north},{east});
      way["landuse"="forest"]({south},{west},{north},{east});
      way["natural"="wood"]({south},{west},{north},{east});
      relation["landuse"="forest"]({south},{west},{north},{east});
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
        raise RuntimeError(f"Failed to fetch tree canopy data from Overpass API: {e}")

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

    trees = []
    wooded_areas = []

    for element in elements:
        tags = element.get("tags", {})
        elem_type = element.get("type")

        if elem_type == "node" and tags.get("natural") == "tree":
            # Individual tree
            tree_type = tags.get("species", tags.get("genus", "default")).lower()

            # Determine canopy radius
            canopy_radius = CANOPY_RADIUS.get(tree_type, CANOPY_RADIUS["default"])

            # Check for explicit diameter tag
            if "diameter_crown" in tags:
                try:
                    canopy_radius = float(tags["diameter_crown"].replace("m", "")) / 2
                except ValueError:
                    pass

            trees.append({
                "id": element.get("id"),
                "lat": element.get("lat"),
                "lon": element.get("lon"),
                "species": tags.get("species"),
                "genus": tags.get("genus"),
                "canopy_radius": canopy_radius,
                "height": _estimate_tree_height(tags)
            })

        elif tags.get("landuse") == "forest" or tags.get("natural") == "wood":
            # Wooded area
            geometry = element.get("geometry", [])
            if geometry:
                wooded_areas.append({
                    "id": element.get("id"),
                    "type": tags.get("landuse") or tags.get("natural"),
                    "geometry": geometry,
                    "name": tags.get("name")
                })

        elif tags.get("natural") == "tree_row":
            # Tree row - extract individual points along the way
            geometry = element.get("geometry", [])
            for i, point in enumerate(geometry):
                trees.append({
                    "id": f"{element.get('id')}_row_{i}",
                    "lat": point.get("lat"),
                    "lon": point.get("lon"),
                    "species": tags.get("species"),
                    "genus": tags.get("genus"),
                    "canopy_radius": CANOPY_RADIUS["default"],
                    "height": _estimate_tree_height(tags),
                    "is_tree_row": True
                })

    return {
        "trees": trees,
        "wooded_areas": wooded_areas,
        "bbox": bbox,
        "stats": {
            "total_trees": len(trees),
            "wooded_areas": len(wooded_areas)
        }
    }


def _estimate_tree_height(tags: Dict) -> float:
    """Estimate tree height from tags or use default."""
    if "height" in tags:
        try:
            return float(tags["height"].replace("m", ""))
        except ValueError:
            pass
    return 8.0  # Default tree height in meters
