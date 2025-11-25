"""
Analysis Tools

Tools for processing thermal data and identifying heat zones suitable for tree planting.
"""

from typing import Dict, List, Tuple
import math


def process_heat_raster(heat_data: Dict) -> Dict:
    """
    Convert thermal sample data into a regular grid structure for analysis.

    Takes the scattered thermal samples from LANDSAT and organizes them into
    a grid structure that can be used for heat zone identification.

    Args:
        heat_data: Dictionary from fetch_heat_data containing:
            - thermal_samples: List of GeoJSON features with temperature values
            - bbox: Bounding box [west, south, east, north]
            - statistics: Mean, min, max temperatures

    Returns:
        Dictionary containing:
            - grid: 2D list of grid cells with temperature data
            - cell_size: Size of each cell in degrees
            - rows: Number of rows in grid
            - cols: Number of columns in grid
            - bbox: Original bounding box
            - statistics: Temperature statistics

    Raises:
        ValueError: If heat_data is missing required fields or is empty

    Example:
        >>> heat_data = fetch_heat_data(bbox, date_range)
        >>> grid = process_heat_raster(heat_data)
        >>> print(f"Grid: {grid['rows']}x{grid['cols']} cells")
    """
    # Validate input
    if not heat_data:
        raise ValueError("heat_data cannot be empty")

    if not isinstance(heat_data, dict):
        raise ValueError("heat_data must be a dictionary")

    required_fields = ["thermal_samples", "bbox", "statistics"]
    for field in required_fields:
        if field not in heat_data:
            raise ValueError(f"heat_data missing required field: {field}")

    thermal_samples = heat_data["thermal_samples"]
    bbox = heat_data["bbox"]
    statistics = heat_data["statistics"]

    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("bbox must be a list of 4 values")

    west, south, east, north = bbox

    # Define grid cell size (~100m ≈ 0.001 degrees at mid-latitudes)
    cell_size = 0.001

    # Calculate grid dimensions
    cols = max(1, int(math.ceil((east - west) / cell_size)))
    rows = max(1, int(math.ceil((north - south) / cell_size)))

    # Limit grid size to prevent memory issues
    max_cells = 10000
    if rows * cols > max_cells:
        scale_factor = math.sqrt(max_cells / (rows * cols))
        cell_size = cell_size / scale_factor
        cols = max(1, int(math.ceil((east - west) / cell_size)))
        rows = max(1, int(math.ceil((north - south) / cell_size)))

    # Initialize grid with empty cells
    grid = [[{
        "temps": [],
        "avg_temp": None,
        "sample_count": 0,
        "center_lat": south + (row + 0.5) * cell_size,
        "center_lon": west + (col + 0.5) * cell_size,
        "row": row,
        "col": col
    } for col in range(cols)] for row in range(rows)]

    # Populate grid with thermal samples
    for feature in thermal_samples:
        if not feature or "geometry" not in feature or "properties" not in feature:
            continue

        geometry = feature["geometry"]
        properties = feature["properties"]

        # Get coordinates (GeoJSON Point)
        if geometry.get("type") != "Point" or "coordinates" not in geometry:
            continue

        coords = geometry["coordinates"]
        if len(coords) < 2:
            continue

        lon, lat = coords[0], coords[1]

        # Get temperature value
        temp = properties.get("ST_B10")
        if temp is None:
            continue

        # Calculate grid cell indices
        col = int((lon - west) / cell_size)
        row = int((lat - south) / cell_size)

        # Ensure within bounds
        col = max(0, min(col, cols - 1))
        row = max(0, min(row, rows - 1))

        # Add temperature to cell
        grid[row][col]["temps"].append(temp)
        grid[row][col]["sample_count"] += 1

    # Calculate average temperature for each cell
    cells_with_data = 0
    for row in range(rows):
        for col in range(cols):
            cell = grid[row][col]
            if cell["temps"]:
                cell["avg_temp"] = sum(cell["temps"]) / len(cell["temps"])
                cells_with_data += 1
            # Remove raw temps to save memory
            del cell["temps"]

    return {
        "grid": grid,
        "cell_size": cell_size,
        "rows": rows,
        "cols": cols,
        "bbox": bbox,
        "statistics": statistics,
        "cells_with_data": cells_with_data,
        "total_cells": rows * cols
    }


def calculate_heat_scores(heat_grid: Dict, land_use: Dict) -> Dict:
    """
    Calculate heat scores for each grid cell based on temperature and land use context.

    Higher scores indicate hotter areas that may benefit more from cooling interventions.
    Scores are normalized to 0-100 scale.

    Args:
        heat_grid: Dictionary from process_heat_raster containing:
            - grid: 2D list of grid cells with temperature data
            - statistics: Temperature statistics
            - cell_size, rows, cols, bbox

        land_use: Dictionary from fetch_land_use_data containing:
            - buildings: List of building features
            - parks: List of park features
            - water: List of water features
            - forests: List of forest features

    Returns:
        Dictionary containing:
            - zones: List of zone dictionaries with heat scores and metadata
            - statistics: Summary statistics about the zones
            - bbox: Original bounding box

    Raises:
        ValueError: If inputs are missing required fields

    Example:
        >>> grid = process_heat_raster(heat_data)
        >>> land_use = fetch_land_use_data(bbox)
        >>> scores = calculate_heat_scores(grid, land_use)
        >>> hot_zones = [z for z in scores["zones"] if z["heat_score"] >= 80]
    """
    # Validate heat_grid input
    if not heat_grid or not isinstance(heat_grid, dict):
        raise ValueError("heat_grid must be a non-empty dictionary")

    required_grid_fields = ["grid", "statistics", "rows", "cols", "bbox", "cell_size"]
    for field in required_grid_fields:
        if field not in heat_grid:
            raise ValueError(f"heat_grid missing required field: {field}")

    # Validate land_use input
    if not land_use or not isinstance(land_use, dict):
        raise ValueError("land_use must be a non-empty dictionary")

    grid = heat_grid["grid"]
    stats = heat_grid["statistics"]
    rows = heat_grid["rows"]
    cols = heat_grid["cols"]
    bbox = heat_grid["bbox"]
    cell_size = heat_grid["cell_size"]

    # Get temperature range for normalization
    min_temp = stats.get("min_temp_celsius")
    max_temp = stats.get("max_temp_celsius")
    mean_temp = stats.get("mean_temp_celsius")

    # Handle case where stats are None or invalid
    if min_temp is None or max_temp is None:
        # Collect all temperatures from grid
        all_temps = []
        for row in range(rows):
            for col in range(cols):
                cell = grid[row][col]
                if cell["avg_temp"] is not None:
                    all_temps.append(cell["avg_temp"])

        if not all_temps:
            raise ValueError("No temperature data available in grid")

        min_temp = min(all_temps)
        max_temp = max(all_temps)
        mean_temp = sum(all_temps) / len(all_temps)

    temp_range = max_temp - min_temp if max_temp != min_temp else 1.0

    # Calculate land use density per cell (simplified - count features that might overlap)
    building_density = _calculate_feature_density(
        land_use.get("buildings", []), bbox, rows, cols, cell_size
    )

    zones = []
    zone_id = 1

    for row in range(rows):
        for col in range(cols):
            cell = grid[row][col]

            if cell["avg_temp"] is None:
                continue

            temp = cell["avg_temp"]

            # Base heat score from temperature (0-100 scale)
            temp_score = ((temp - min_temp) / temp_range) * 100

            # Adjust score based on building density (urban areas get a small boost)
            density = building_density.get((row, col), 0)
            urban_factor = min(1.2, 1.0 + (density * 0.02))

            heat_score = min(100, temp_score * urban_factor)

            # Determine priority based on score
            if heat_score >= 80:
                priority = "critical"
            elif heat_score >= 60:
                priority = "high"
            elif heat_score >= 40:
                priority = "medium"
            else:
                priority = "low"

            # Calculate cell bounds for geometry
            west_bound = bbox[0] + col * cell_size
            south_bound = bbox[1] + row * cell_size
            east_bound = west_bound + cell_size
            north_bound = south_bound + cell_size

            # Approximate area in square meters
            # At mid-latitudes, 1 degree ≈ 111 km latitude, ~85-100 km longitude
            lat_meters = cell_size * 111000
            lon_meters = cell_size * 85000 * math.cos(math.radians(cell["center_lat"]))
            area_sqm = lat_meters * lon_meters

            zone = {
                "id": zone_id,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [west_bound, south_bound],
                        [east_bound, south_bound],
                        [east_bound, north_bound],
                        [west_bound, north_bound],
                        [west_bound, south_bound]  # Close the polygon
                    ]]
                },
                "heat_score": round(heat_score, 2),
                "temp_celsius": round(temp, 2),
                "priority": priority,
                "area_sqm": round(area_sqm, 2),
                "center": {
                    "lat": cell["center_lat"],
                    "lon": cell["center_lon"]
                },
                "building_density": density,
                "row": row,
                "col": col
            }

            zones.append(zone)
            zone_id += 1

    # Sort by heat score descending
    zones.sort(key=lambda z: z["heat_score"], reverse=True)

    # Calculate summary statistics
    scores = [z["heat_score"] for z in zones]
    summary_stats = {
        "total_zones": len(zones),
        "critical_count": sum(1 for z in zones if z["priority"] == "critical"),
        "high_count": sum(1 for z in zones if z["priority"] == "high"),
        "medium_count": sum(1 for z in zones if z["priority"] == "medium"),
        "low_count": sum(1 for z in zones if z["priority"] == "low"),
        "avg_heat_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "max_heat_score": round(max(scores), 2) if scores else 0,
        "min_heat_score": round(min(scores), 2) if scores else 0
    }

    return {
        "zones": zones,
        "statistics": summary_stats,
        "bbox": bbox,
        "temp_range": {
            "min_celsius": round(min_temp, 2),
            "max_celsius": round(max_temp, 2),
            "mean_celsius": round(mean_temp, 2) if mean_temp else None
        }
    }


def _calculate_feature_density(
    features: List[Dict],
    bbox: List[float],
    rows: int,
    cols: int,
    cell_size: float
) -> Dict[Tuple[int, int], int]:
    """
    Calculate simplified feature density per grid cell.

    Args:
        features: List of OSM features with geometry
        bbox: Bounding box [west, south, east, north]
        rows: Number of grid rows
        cols: Number of grid columns
        cell_size: Size of each cell in degrees

    Returns:
        Dictionary mapping (row, col) to feature count
    """
    density = {}
    west, south, east, north = bbox

    for feature in features:
        if not feature or "geometry" not in feature:
            continue

        geometry = feature.get("geometry", [])
        if not geometry:
            continue

        # Use first point of geometry to determine cell
        first_point = geometry[0] if isinstance(geometry, list) else None
        if not first_point:
            continue

        lon = first_point.get("lon", 0)
        lat = first_point.get("lat", 0)

        # Calculate grid cell
        col = int((lon - west) / cell_size)
        row = int((lat - south) / cell_size)

        # Ensure within bounds
        col = max(0, min(col, cols - 1))
        row = max(0, min(row, rows - 1))

        key = (row, col)
        density[key] = density.get(key, 0) + 1

    return density


def filter_plantable_areas(zones: Dict, land_use: Dict) -> Dict:
    """
    Filter heat zones to only include areas suitable for tree planting.

    Removes zones that are:
    - Water bodies
    - Existing dense forests
    - Building footprints

    Keeps zones that are:
    - Open land
    - Parks (good candidates for additional planting)
    - Sparse vegetation areas
    - Parking lots and paved areas (could be converted)

    Args:
        zones: Dictionary from calculate_heat_scores containing:
            - zones: List of zone dictionaries with heat scores
            - statistics: Summary statistics
            - bbox: Bounding box

        land_use: Dictionary from fetch_land_use_data containing:
            - buildings: List of building features
            - parks: List of park features
            - water: List of water features
            - forests: List of forest features

    Returns:
        Dictionary containing:
            - zones: Filtered list of plantable zones (top 20 by heat score)
            - statistics: Updated summary statistics
            - filtered_stats: Statistics about filtering
            - bbox: Original bounding box

    Raises:
        ValueError: If inputs are missing required fields

    Example:
        >>> scores = calculate_heat_scores(grid, land_use)
        >>> plantable = filter_plantable_areas(scores, land_use)
        >>> print(f"Found {len(plantable['zones'])} plantable hot zones")
    """
    # Validate zones input
    if not zones or not isinstance(zones, dict):
        raise ValueError("zones must be a non-empty dictionary")

    if "zones" not in zones:
        raise ValueError("zones dictionary missing 'zones' field")

    # Validate land_use input
    if not land_use or not isinstance(land_use, dict):
        raise ValueError("land_use must be a non-empty dictionary")

    zone_list = zones.get("zones", [])
    bbox = zones.get("bbox", [])

    # Get non-plantable features
    water_features = land_use.get("water", [])
    forest_features = land_use.get("forests", [])
    building_features = land_use.get("buildings", [])
    park_features = land_use.get("parks", [])

    # Create spatial index of non-plantable areas (simplified approach)
    water_cells = _get_feature_cells(water_features, bbox)
    forest_cells = _get_feature_cells(forest_features, bbox)
    building_cells = _get_feature_cells(building_features, bbox)
    park_cells = _get_feature_cells(park_features, bbox)

    plantable_zones = []
    excluded_water = 0
    excluded_forest = 0
    excluded_building = 0
    marked_park = 0

    for zone in zone_list:
        row = zone.get("row")
        col = zone.get("col")
        cell_key = (row, col)

        # Check if zone overlaps with water
        if cell_key in water_cells:
            excluded_water += 1
            continue

        # Check if zone is densely forested (skip - already has trees)
        if cell_key in forest_cells:
            excluded_forest += 1
            continue

        # Check if zone is primarily buildings
        building_density = zone.get("building_density", 0)
        if cell_key in building_cells and building_density > 5:
            excluded_building += 1
            continue

        # Mark if zone is in/near a park (good candidate)
        zone_copy = zone.copy()
        zone_copy["in_park"] = cell_key in park_cells
        zone_copy["plantable"] = True

        plantable_zones.append(zone_copy)
        if zone_copy["in_park"]:
            marked_park += 1

    # Sort by heat score descending and take top 20
    plantable_zones.sort(key=lambda z: z["heat_score"], reverse=True)
    top_zones = plantable_zones[:20]

    # Recalculate statistics for filtered zones
    if top_zones:
        scores = [z["heat_score"] for z in top_zones]
        filtered_stats = {
            "total_zones": len(top_zones),
            "critical_count": sum(1 for z in top_zones if z["priority"] == "critical"),
            "high_count": sum(1 for z in top_zones if z["priority"] == "high"),
            "medium_count": sum(1 for z in top_zones if z["priority"] == "medium"),
            "low_count": sum(1 for z in top_zones if z["priority"] == "low"),
            "avg_heat_score": round(sum(scores) / len(scores), 2),
            "max_heat_score": round(max(scores), 2),
            "min_heat_score": round(min(scores), 2),
            "zones_in_parks": sum(1 for z in top_zones if z.get("in_park", False))
        }
    else:
        filtered_stats = {
            "total_zones": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "avg_heat_score": 0,
            "max_heat_score": 0,
            "min_heat_score": 0,
            "zones_in_parks": 0
        }

    filtering_summary = {
        "original_count": len(zone_list),
        "plantable_count": len(plantable_zones),
        "returned_count": len(top_zones),
        "excluded_water": excluded_water,
        "excluded_forest": excluded_forest,
        "excluded_building": excluded_building,
        "marked_in_parks": marked_park
    }

    return {
        "zones": top_zones,
        "statistics": filtered_stats,
        "filtering_summary": filtering_summary,
        "bbox": bbox,
        "temp_range": zones.get("temp_range", {})
    }


def _get_feature_cells(
    features: List[Dict],
    bbox: List[float],
    cell_size: float = 0.001
) -> set:
    """
    Get set of grid cells that contain features.

    Args:
        features: List of OSM features with geometry
        bbox: Bounding box [west, south, east, north]
        cell_size: Size of each cell in degrees

    Returns:
        Set of (row, col) tuples for cells containing features
    """
    if not bbox or len(bbox) != 4:
        return set()

    cells = set()
    west, south, east, north = bbox

    for feature in features:
        if not feature or "geometry" not in feature:
            continue

        geometry = feature.get("geometry", [])
        if not geometry:
            continue

        # Process all points in geometry
        for point in geometry:
            if not isinstance(point, dict):
                continue

            lon = point.get("lon", 0)
            lat = point.get("lat", 0)

            if lon < west or lon > east or lat < south or lat > north:
                continue

            col = int((lon - west) / cell_size)
            row = int((lat - south) / cell_size)

            cells.add((row, col))

    return cells
