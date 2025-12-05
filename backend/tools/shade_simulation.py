"""
Shade Simulation Tool

Simulates shade patterns based on buildings, trees, and sun position.
"""

import math
from typing import Dict, List


def simulate_shade_coverage(
    buildings: List[Dict],
    trees: List[Dict],
    sun_position: Dict,
    bbox: List[float],
    grid_size: float = 0.0005  # ~50m grid cells
) -> Dict:
    """
    Simulate shade coverage for a given sun position.

    Args:
        buildings: List of buildings with height and geometry
        trees: List of trees with height and canopy radius
        sun_position: Sun position with azimuth and altitude
        bbox: Bounding box [west, south, east, north]
        grid_size: Size of analysis grid cells in degrees

    Returns:
        Dictionary containing:
            - grid: 2D grid of shade values (0-1)
            - coverage_percent: Overall shade coverage percentage
            - building_shade: Shade from buildings only
            - tree_shade: Shade from trees only
    """
    azimuth = sun_position["azimuth"]
    altitude = sun_position["altitude"]

    # If sun is below horizon, everything is in shade
    if altitude <= 0:
        return {
            "grid": None,
            "coverage_percent": 100.0,
            "is_night": True,
            "hour": sun_position.get("hour")
        }

    west, south, east, north = bbox

    # Create grid
    cols = int((east - west) / grid_size) + 1
    rows = int((north - south) / grid_size) + 1

    # Limit grid size
    if rows * cols > 10000:
        grid_size = math.sqrt((east - west) * (north - south) / 10000)
        cols = int((east - west) / grid_size) + 1
        rows = int((north - south) / grid_size) + 1

    # Initialize grid (0 = full sun, 1 = full shade)
    shade_grid = [[0.0 for _ in range(cols)] for _ in range(rows)]

    # Calculate shadow direction and length multiplier
    shadow_azimuth = (azimuth + 180) % 360  # Shadow points opposite to sun
    shadow_length_mult = 1 / math.tan(math.radians(max(altitude, 1)))

    # Convert azimuth to dx, dy components (in degrees, approximately)
    # 1 degree latitude ~ 111km, 1 degree longitude ~ 85km at mid-latitudes
    azimuth_rad = math.radians(shadow_azimuth)
    dx_mult = math.sin(azimuth_rad) / 85000  # per meter of shadow
    dy_mult = math.cos(azimuth_rad) / 111000  # per meter of shadow

    shaded_cells = 0
    total_cells = rows * cols
    building_shaded_cells = 0
    tree_shaded_cells = 0

    # Track which cells are shaded by buildings vs trees
    building_shade_grid = [[0.0 for _ in range(cols)] for _ in range(rows)]
    tree_shade_grid = [[0.0 for _ in range(cols)] for _ in range(rows)]

    # Process buildings
    for building in buildings:
        height = building.get("height", 10)
        shadow_length = height * shadow_length_mult

        geometry = building.get("geometry", [])
        if not geometry:
            continue

        # Get building footprint center
        lons = [p.get("lon", 0) for p in geometry]
        lats = [p.get("lat", 0) for p in geometry]
        if not lons or not lats:
            continue
        center_lon = sum(lons) / len(lons)
        center_lat = sum(lats) / len(lats)

        # Calculate shadow endpoint
        shadow_dx = shadow_length * dx_mult
        shadow_dy = shadow_length * dy_mult

        # Mark grid cells in shadow path
        _mark_shadow_cells(
            building_shade_grid, bbox, grid_size,
            center_lon, center_lat,
            center_lon + shadow_dx, center_lat + shadow_dy,
            rows, cols
        )

    # Process trees
    for tree in trees:
        height = tree.get("height", 8)
        canopy_radius = tree.get("canopy_radius", 4)
        shadow_length = height * shadow_length_mult

        lon = tree.get("lon", 0)
        lat = tree.get("lat", 0)

        # Calculate shadow endpoint
        shadow_dx = shadow_length * dx_mult
        shadow_dy = shadow_length * dy_mult

        # Mark grid cells in shadow path (with canopy spread)
        _mark_shadow_cells(
            tree_shade_grid, bbox, grid_size,
            lon, lat,
            lon + shadow_dx, lat + shadow_dy,
            rows, cols,
            spread=canopy_radius / 111000  # Convert meters to degrees
        )

    # Combine building and tree shade into main grid
    for row in range(rows):
        for col in range(cols):
            building_val = building_shade_grid[row][col]
            tree_val = tree_shade_grid[row][col]

            # Combine shade values (cap at 1.0)
            shade_grid[row][col] = min(1.0, building_val + tree_val)

            if building_val > 0:
                building_shaded_cells += 1
            if tree_val > 0:
                tree_shaded_cells += 1
            if shade_grid[row][col] > 0:
                shaded_cells += 1

    coverage_percent = (shaded_cells / total_cells) * 100 if total_cells > 0 else 0
    building_shade_percent = (building_shaded_cells / total_cells) * 100 if total_cells > 0 else 0
    tree_shade_percent = (tree_shaded_cells / total_cells) * 100 if total_cells > 0 else 0

    return {
        "grid": shade_grid,
        "rows": rows,
        "cols": cols,
        "bbox": bbox,
        "grid_size": grid_size,
        "coverage_percent": round(coverage_percent, 1),
        "building_shade_percent": round(building_shade_percent, 1),
        "tree_shade_percent": round(tree_shade_percent, 1),
        "hour": sun_position.get("hour"),
        "sun_altitude": altitude,
        "sun_azimuth": azimuth,
        "is_night": False
    }


def _mark_shadow_cells(
    grid: List[List[float]],
    bbox: List[float],
    grid_size: float,
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
    rows: int,
    cols: int,
    spread: float = 0.0
):
    """Mark grid cells along a shadow path."""
    west, south, east, north = bbox

    # Number of steps along shadow
    steps = 20

    for step in range(steps + 1):
        t = step / steps
        lon = start_lon + t * (end_lon - start_lon)
        lat = start_lat + t * (end_lat - start_lat)

        # Convert to grid coordinates
        col = int((lon - west) / grid_size)
        row = int((lat - south) / grid_size)

        # Mark cell and neighbors (for spread)
        spread_cells = int(spread / grid_size) + 1

        for dr in range(-spread_cells, spread_cells + 1):
            for dc in range(-spread_cells, spread_cells + 1):
                r, c = row + dr, col + dc
                if 0 <= r < rows and 0 <= c < cols:
                    grid[r][c] = min(1.0, grid[r][c] + 0.3)


def simulate_multiple_hours(
    buildings: List[Dict],
    trees: List[Dict],
    sun_path: Dict,
    bbox: List[float],
    hours: List[int] = None,
    grid_size: float = 0.0005
) -> List[Dict]:
    """
    Simulate shade coverage for multiple hours of the day.

    Args:
        buildings: List of buildings with height and geometry
        trees: List of trees with height and canopy radius
        sun_path: Sun path data with hourly positions
        bbox: Bounding box [west, south, east, north]
        hours: List of hours to simulate (default: daylight hours)
        grid_size: Size of analysis grid cells in degrees

    Returns:
        List of shade coverage results for each hour
    """
    positions = sun_path.get("positions", [])

    # If no hours specified, use all daylight hours
    if hours is None:
        hours = [p["hour"] for p in positions if p.get("is_daylight", False)]

    results = []

    for hour in hours:
        # Find sun position for this hour
        sun_position = next((p for p in positions if p["hour"] == hour), None)

        if sun_position is None:
            continue

        result = simulate_shade_coverage(
            buildings, trees, sun_position, bbox, grid_size
        )
        results.append(result)

    return results


def get_shade_summary(hourly_results: List[Dict]) -> Dict:
    """
    Generate a summary of shade coverage across all hours.

    Args:
        hourly_results: List of hourly shade simulation results

    Returns:
        Summary statistics for shade coverage
    """
    daylight_results = [r for r in hourly_results if not r.get("is_night", True)]

    if not daylight_results:
        return {
            "error": "No daylight hours in results",
            "total_hours": len(hourly_results)
        }

    coverages = [r.get("coverage_percent", 0) for r in daylight_results]
    building_coverages = [r.get("building_shade_percent", 0) for r in daylight_results]
    tree_coverages = [r.get("tree_shade_percent", 0) for r in daylight_results]

    # Define peak hours (10am - 4pm)
    peak_hours = [10, 11, 12, 13, 14, 15, 16]
    peak_results = [r for r in daylight_results if r.get("hour") in peak_hours]
    peak_coverages = [r.get("coverage_percent", 0) for r in peak_results]

    return {
        "total_daylight_hours": len(daylight_results),
        "avg_coverage_percent": round(sum(coverages) / len(coverages), 1) if coverages else 0,
        "min_coverage_percent": round(min(coverages), 1) if coverages else 0,
        "max_coverage_percent": round(max(coverages), 1) if coverages else 0,
        "avg_building_shade_percent": round(sum(building_coverages) / len(building_coverages), 1) if building_coverages else 0,
        "avg_tree_shade_percent": round(sum(tree_coverages) / len(tree_coverages), 1) if tree_coverages else 0,
        "peak_hours_avg_coverage": round(sum(peak_coverages) / len(peak_coverages), 1) if peak_coverages else 0,
        "worst_hour": min(daylight_results, key=lambda r: r.get("coverage_percent", 0)).get("hour") if daylight_results else None,
        "best_hour": max(daylight_results, key=lambda r: r.get("coverage_percent", 0)).get("hour") if daylight_results else None
    }
