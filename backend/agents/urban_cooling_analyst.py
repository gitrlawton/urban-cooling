"""
Urban Cooling Analyst Agent

AI agent that identifies heat zones in cities that would benefit
most from tree planting interventions. Includes shade analysis
for identifying areas with greatest shade deficits.
"""

from google.adk.agents import Agent
from tools.geocoding import geocode_location
from tools.heat_data import fetch_heat_data
from tools.land_use import fetch_land_use_data
from tools.analysis import (
    process_heat_raster,
    calculate_heat_scores,
    filter_plantable_areas
)
from tools.building_heights import fetch_building_heights
from tools.tree_canopy import fetch_tree_canopy_data
from tools.sun_path import calculate_sun_path
from tools.shade_simulation import simulate_shade_coverage
from tools.shade_deficit import calculate_shade_deficit, prioritize_by_heat_and_shade

# Global caches to store large data between tool calls (avoids sending to LLM)
_heat_data_cache = None
_land_use_cache = None
_heat_grid_cache = None
_zones_cache = None

# Phase 2: Shade analysis caches
_building_heights_cache = None
_tree_canopy_cache = None
_sun_path_cache = None
_shade_coverage_cache = None


def geocode(location: str) -> dict:
    """
    Convert city name or zip code to geographic coordinates.

    Args:
        location: City name (e.g., "San Francisco, CA") or zip code (e.g., "94102")

    Returns:
        Dictionary containing:
            - location_name: Full display name of the location
            - bbox: Bounding box [west, south, east, north] in degrees
            - center: Center coordinates {"lat": float, "lon": float}
    """
    return geocode_location(location)


def get_heat_data(west: float, south: float, east: float, north: float, date_range: str = "2024-06-01,2024-08-31") -> dict:
    """
    Fetch LANDSAT thermal imagery for the specified bounding box.

    Args:
        west: Western longitude boundary in degrees
        south: Southern latitude boundary in degrees
        east: Eastern longitude boundary in degrees
        north: Northern latitude boundary in degrees
        date_range: Date range as "YYYY-MM-DD,YYYY-MM-DD" (default: summer 2024)

    Returns:
        Dictionary containing thermal samples, statistics, and metadata
    """
    bbox = [west, south, east, north]
    result = fetch_heat_data(bbox, date_range)
    # Store full data globally for later processing, but return summary to LLM to save tokens
    global _heat_data_cache
    _heat_data_cache = result
    return {
        "source": result["source"],
        "bbox": result["bbox"],
        "date_range": result["date_range"],
        "statistics": result["statistics"],
        "resolution": result["resolution"],
        "sample_count": result["sample_count"],
        "image_count": result["image_count"],
        "message": "Heat data fetched successfully. Use process_thermal_data to analyze the samples."
    }


def get_land_use(west: float, south: float, east: float, north: float) -> dict:
    """
    Fetch land use data from OpenStreetMap for the specified bounding box.

    Args:
        west: Western longitude boundary in degrees
        south: Southern latitude boundary in degrees
        east: Eastern longitude boundary in degrees
        north: Northern latitude boundary in degrees

    Returns:
        Dictionary containing summary of land features (buildings, parks, water, forests)
    """
    global _land_use_cache
    bbox = [west, south, east, north]
    result = fetch_land_use_data(bbox)
    _land_use_cache = result
    # Return summary to LLM, not full data
    return {
        "bbox": result.get("bbox"),
        "buildings_count": len(result.get("buildings", [])),
        "parks_count": len(result.get("parks", [])),
        "water_count": len(result.get("water", [])),
        "forests_count": len(result.get("forests", [])),
        "message": "Land use data fetched successfully. Use score_heat_zones to analyze."
    }


def process_thermal_data() -> dict:
    """
    Convert thermal sample data into a regular grid structure for analysis.
    Uses cached heat data from get_heat_data call.

    Returns:
        Dictionary containing summary of the grid structure
    """
    global _heat_data_cache, _heat_grid_cache
    if _heat_data_cache is None:
        return {"error": "No heat data available. Call get_heat_data first."}

    result = process_heat_raster(_heat_data_cache)
    _heat_grid_cache = result
    # Return summary to LLM
    return {
        "grid_cells": result.get("grid_cells", 0),
        "bbox": result.get("bbox"),
        "cell_size": result.get("cell_size"),
        "message": "Thermal data processed into grid. Use score_heat_zones to calculate scores."
    }


def score_heat_zones() -> dict:
    """
    Calculate heat scores for each grid cell based on temperature and land use.
    Uses cached data from previous tool calls.

    Returns:
        Dictionary containing summary of zones with heat scores
    """
    global _heat_grid_cache, _land_use_cache, _zones_cache
    if _heat_grid_cache is None:
        return {"error": "No heat grid available. Call process_thermal_data first."}
    if _land_use_cache is None:
        return {"error": "No land use data available. Call get_land_use first."}

    result = calculate_heat_scores(_heat_grid_cache, _land_use_cache)
    _zones_cache = result
    # Return summary to LLM
    zones = result.get("zones", [])
    return {
        "total_zones": len(zones),
        "temp_range": result.get("temp_range"),
        "message": f"Calculated heat scores for {len(zones)} zones. Use filter_plantable_zones to get final results."
    }


def filter_plantable_zones() -> dict:
    """
    Filter heat zones to only include areas suitable for tree planting.
    Uses cached data from previous tool calls.

    Removes water bodies, dense forests, and heavily built areas.
    Returns top 20 hottest plantable zones with full details.

    Returns:
        Dictionary containing filtered plantable zones and statistics
    """
    global _zones_cache, _land_use_cache
    if _zones_cache is None:
        return {"error": "No zones available. Call score_heat_zones first."}
    if _land_use_cache is None:
        return {"error": "No land use data available. Call get_land_use first."}

    # This is the final step - return full zone data for the frontend
    return filter_plantable_areas(_zones_cache, _land_use_cache)


# =============================================================================
# Phase 2: Shade Analysis Tools
# =============================================================================

def get_building_heights(west: float, south: float, east: float, north: float) -> dict:
    """
    Fetch 3D building data from OpenStreetMap for shade simulation.

    Args:
        west: Western longitude boundary in degrees
        south: Southern latitude boundary in degrees
        east: Eastern longitude boundary in degrees
        north: Northern latitude boundary in degrees

    Returns:
        Summary of building data (full data cached for shade simulation)
    """
    global _building_heights_cache
    bbox = [west, south, east, north]
    result = fetch_building_heights(bbox)
    _building_heights_cache = result
    return {
        "bbox": bbox,
        "total_buildings": result["stats"]["total_buildings"],
        "heights_from_tag": result["stats"]["heights_from_tag"],
        "heights_from_levels": result["stats"]["heights_from_levels"],
        "heights_estimated": result["stats"]["heights_estimated"],
        "message": "Building heights fetched. Use simulate_shade to calculate shadows."
    }


def get_tree_canopy(west: float, south: float, east: float, north: float) -> dict:
    """
    Fetch existing tree canopy coverage from OpenStreetMap.

    Args:
        west: Western longitude boundary in degrees
        south: Southern latitude boundary in degrees
        east: Eastern longitude boundary in degrees
        north: Northern latitude boundary in degrees

    Returns:
        Summary of tree data (full data cached for shade simulation)
    """
    global _tree_canopy_cache
    bbox = [west, south, east, north]
    result = fetch_tree_canopy_data(bbox)
    _tree_canopy_cache = result
    return {
        "bbox": bbox,
        "total_trees": result["stats"]["total_trees"],
        "wooded_areas": result["stats"]["wooded_areas"],
        "message": "Tree canopy data fetched. Use simulate_shade to calculate shadows."
    }


def get_sun_path(lat: float, lon: float, date: str) -> dict:
    """
    Calculate sun positions throughout the day for a given location and date.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        date: Date in YYYY-MM-DD format

    Returns:
        Sun path data with hourly positions, sunrise/sunset times
    """
    global _sun_path_cache
    result = calculate_sun_path(lat, lon, date)
    _sun_path_cache = result
    # Return full data as it's not too large
    return {
        "date": result["date"],
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "sunrise": result["sunrise"],
        "sunset": result["sunset"],
        "solar_noon": result["solar_noon"],
        "max_altitude": result["max_altitude"],
        "daylight_hours": sum(1 for p in result["positions"] if p["is_daylight"]),
        "message": "Sun path calculated. Use simulate_shade for each hour to analyze shadows."
    }


def simulate_shade(hour: int) -> dict:
    """
    Simulate shade coverage for a specific hour of the day.
    Uses cached building, tree, and sun path data from previous tool calls.

    Args:
        hour: Hour of day (0-23 in UTC)

    Returns:
        Shade coverage summary for that hour
    """
    global _building_heights_cache, _tree_canopy_cache, _sun_path_cache, _shade_coverage_cache

    if _building_heights_cache is None:
        return {"error": "No building data. Call get_building_heights first."}
    if _sun_path_cache is None:
        return {"error": "No sun path data. Call get_sun_path first."}

    # Find sun position for this hour
    positions = _sun_path_cache.get("positions", [])
    sun_position = next((p for p in positions if p["hour"] == hour), None)

    if sun_position is None:
        return {"error": f"No sun position data for hour {hour}"}

    buildings = _building_heights_cache.get("buildings", [])
    trees = _tree_canopy_cache.get("trees", []) if _tree_canopy_cache else []
    bbox = _building_heights_cache.get("bbox", [])

    result = simulate_shade_coverage(buildings, trees, sun_position, bbox)

    # Cache result for later deficit analysis
    if _shade_coverage_cache is None:
        _shade_coverage_cache = []
    _shade_coverage_cache.append(result)

    if result.get("is_night", False):
        return {
            "hour": hour,
            "is_night": True,
            "coverage_percent": 100.0,
            "message": f"Hour {hour} is nighttime (sun below horizon). Full shade."
        }

    return {
        "hour": hour,
        "coverage_percent": result.get("coverage_percent"),
        "building_shade_percent": result.get("building_shade_percent"),
        "tree_shade_percent": result.get("tree_shade_percent"),
        "sun_altitude": result.get("sun_altitude"),
        "sun_azimuth": result.get("sun_azimuth"),
        "is_night": False,
        "message": f"Shade simulated for hour {hour}. Coverage: {result.get('coverage_percent')}%"
    }


def analyze_shade_deficit() -> dict:
    """
    Calculate shade deficit scores combining heat and shade data.
    Uses cached data from previous tool calls.

    High heat + low shade = high deficit = highest priority for tree planting.

    Returns:
        Zones with shade deficit scores and combined priority rankings
    """
    global _zones_cache, _shade_coverage_cache

    if _zones_cache is None:
        return {"error": "No heat zones. Complete heat analysis first (steps 1-6)."}
    if not _shade_coverage_cache:
        return {"error": "No shade data. Run simulate_shade for multiple hours first."}

    heat_zones = _zones_cache.get("zones", [])

    result = calculate_shade_deficit(_shade_coverage_cache, heat_zones)
    prioritized = prioritize_by_heat_and_shade(heat_zones, result)

    return {
        "zones": prioritized[:20],  # Return top 20 priority zones
        "summary": result.get("summary", {}),
        "message": f"Analyzed shade deficit for {len(prioritized)} zones. Top zones have highest combined heat + shade deficit scores."
    }


def clear_shade_cache() -> dict:
    """
    Clear shade analysis caches to start a fresh analysis.
    Useful when analyzing a new location or date.

    Returns:
        Confirmation message
    """
    global _building_heights_cache, _tree_canopy_cache, _sun_path_cache, _shade_coverage_cache
    _building_heights_cache = None
    _tree_canopy_cache = None
    _sun_path_cache = None
    _shade_coverage_cache = None
    return {"message": "Shade analysis caches cleared. Ready for new analysis."}


# Define the Urban Cooling Analyst Agent
root_agent = Agent(
    model="gemini-2.0-flash",
    name="urban_cooling_analyst",
    description="Identifies the hottest areas in a city that would benefit most from tree planting, including shade deficit analysis.",
    instruction="""You are the Urban Cooling Analyst Agent for ShadePlan.

Your role: Identify the hottest areas in a city that would benefit most from tree planting,
including shade deficit analysis to find areas with greatest cooling needs.

HEAT ANALYSIS (basic - always perform these steps):
1. Use geocode(location) to convert the location to coordinates and get a bounding box
2. Use get_heat_data(west, south, east, north) with the bounding box coordinates to fetch thermal imagery
3. Use get_land_use(west, south, east, north) with the same bounding box to get land features
4. Use process_thermal_data() to convert the cached heat data to a grid (no parameters needed)
5. Use score_heat_zones() to calculate heat scores (no parameters needed, uses cached data)
6. Use filter_plantable_zones() to get the top plantable hot zones (no parameters needed)

SHADE ANALYSIS (when requested - perform after heat analysis):
If the user requests shade analysis or combined analysis:
7. Use get_building_heights(west, south, east, north) to fetch 3D building data
8. Use get_tree_canopy(west, south, east, north) to fetch existing tree coverage
9. Use get_sun_path(lat, lon, date) to calculate sun positions for the analysis date
10. Use simulate_shade(hour) for key daylight hours (e.g., 14, 16, 18, 20 UTC for US locations)
11. Use analyze_shade_deficit() to combine heat + shade scores into final priorities

Note: Hours are in UTC. For US locations, add 5-8 hours to local time to get UTC.
For example, noon local time in California (UTC-8) is hour 20 in UTC.

After completing the analysis, return the results as structured JSON with:
- location: The analyzed location name
- analysis_date: Today's date
- heat_zones: Array of the top 10-20 hottest plantable zones, each with:
  - id: Zone identifier
  - geometry: GeoJSON polygon coordinates
  - heat_score: Score from 0-100
  - temp_celsius: Temperature in Celsius
  - priority: "critical", "high", "medium", or "low"
  - area_sqm: Area in square meters

For combined analysis, also include:
  - shade_coverage: Percentage of area with shade (0-100)
  - shade_deficit: Percentage lacking shade (0-100)
  - combined_score: Combined heat + shade deficit score
- metadata: Summary statistics about the analysis

Always provide helpful context about what the heat zones mean and potential benefits of tree planting in these areas.
For shade analysis, explain which areas have the greatest shade deficits during peak sun hours.""",
    tools=[
        # Phase 1: Heat analysis tools
        geocode,
        get_heat_data,
        get_land_use,
        process_thermal_data,
        score_heat_zones,
        filter_plantable_zones,
        # Phase 2: Shade analysis tools
        get_building_heights,
        get_tree_canopy,
        get_sun_path,
        simulate_shade,
        analyze_shade_deficit,
        clear_shade_cache,
    ],
)
