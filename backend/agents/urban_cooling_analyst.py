"""
Urban Cooling Analyst Agent

AI agent that identifies heat zones in cities that would benefit
most from tree planting interventions.
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
    return fetch_heat_data(bbox, date_range)


def get_land_use(west: float, south: float, east: float, north: float) -> dict:
    """
    Fetch land use data from OpenStreetMap for the specified bounding box.

    Args:
        west: Western longitude boundary in degrees
        south: Southern latitude boundary in degrees
        east: Eastern longitude boundary in degrees
        north: Northern latitude boundary in degrees

    Returns:
        Dictionary containing categorized land features (buildings, parks, water, forests)
    """
    bbox = [west, south, east, north]
    return fetch_land_use_data(bbox)


def process_thermal_data(heat_data_json: str) -> dict:
    """
    Convert thermal sample data into a regular grid structure for analysis.

    Args:
        heat_data_json: JSON string of heat data from get_heat_data

    Returns:
        Dictionary containing the grid structure with temperature data per cell
    """
    import json
    heat_data = json.loads(heat_data_json) if isinstance(heat_data_json, str) else heat_data_json
    return process_heat_raster(heat_data)


def score_heat_zones(heat_grid_json: str, land_use_json: str) -> dict:
    """
    Calculate heat scores for each grid cell based on temperature and land use.

    Args:
        heat_grid_json: JSON string of heat grid from process_thermal_data
        land_use_json: JSON string of land use data from get_land_use

    Returns:
        Dictionary containing zones with heat scores, priorities, and geometries
    """
    import json
    heat_grid = json.loads(heat_grid_json) if isinstance(heat_grid_json, str) else heat_grid_json
    land_use = json.loads(land_use_json) if isinstance(land_use_json, str) else land_use_json
    return calculate_heat_scores(heat_grid, land_use)


def filter_plantable_zones(zones_json: str, land_use_json: str) -> dict:
    """
    Filter heat zones to only include areas suitable for tree planting.

    Removes water bodies, dense forests, and heavily built areas.
    Returns top 20 hottest plantable zones.

    Args:
        zones_json: JSON string of scored zones from score_heat_zones
        land_use_json: JSON string of land use data from get_land_use

    Returns:
        Dictionary containing filtered plantable zones and statistics
    """
    import json
    zones = json.loads(zones_json) if isinstance(zones_json, str) else zones_json
    land_use = json.loads(land_use_json) if isinstance(land_use_json, str) else land_use_json
    return filter_plantable_areas(zones, land_use)


# Define the Urban Cooling Analyst Agent
root_agent = Agent(
    model="gemini-2.0-flash",
    name="urban_cooling_analyst",
    description="Identifies the hottest areas in a city that would benefit most from tree planting.",
    instruction="""You are the Urban Cooling Analyst Agent for ShadePlan.

Your role: Identify the hottest areas in a city that would benefit most from tree planting.

When a user provides a location (city name or zip code), follow this process:

1. Use the geocode tool to convert the location to coordinates and get a bounding box
2. Use get_heat_data with the bounding box coordinates to fetch thermal imagery
3. Use get_land_use with the same bounding box to get land features
4. Use process_thermal_data to convert the heat data to a grid
5. Use score_heat_zones with the grid and land use data to calculate heat scores
6. Use filter_plantable_zones to get the top plantable hot zones

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
- metadata: Summary statistics about the analysis

Always provide helpful context about what the heat zones mean and potential benefits of tree planting in these areas.""",
    tools=[
        geocode,
        get_heat_data,
        get_land_use,
        process_thermal_data,
        score_heat_zones,
        filter_plantable_zones
    ],
)
