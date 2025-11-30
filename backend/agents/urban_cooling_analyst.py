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

# Global caches to store large data between tool calls (avoids sending to LLM)
_heat_data_cache = None
_land_use_cache = None
_heat_grid_cache = None
_zones_cache = None


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


# Define the Urban Cooling Analyst Agent
root_agent = Agent(
    model="gemini-2.0-flash",
    name="urban_cooling_analyst",
    description="Identifies the hottest areas in a city that would benefit most from tree planting.",
    instruction="""You are the Urban Cooling Analyst Agent for ShadePlan.

Your role: Identify the hottest areas in a city that would benefit most from tree planting.

When a user provides a location (city name or zip code), follow this process:

1. Use geocode(location) to convert the location to coordinates and get a bounding box
2. Use get_heat_data(west, south, east, north) with the bounding box coordinates to fetch thermal imagery
3. Use get_land_use(west, south, east, north) with the same bounding box to get land features
4. Use process_thermal_data() to convert the cached heat data to a grid (no parameters needed)
5. Use score_heat_zones() to calculate heat scores (no parameters needed, uses cached data)
6. Use filter_plantable_zones() to get the top plantable hot zones (no parameters needed)

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
