"""
ShadePlan FastAPI Application

Provides REST API endpoints for urban heat analysis.
"""

import logging
import os
from datetime import date
from typing import Any, Optional

# Configure logging for ADK observability
# Captures agent decisions, tool calls, and LLM interactions
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent.parent / '.internal_docs' / 'logs'
logs_dir.mkdir(parents=True, exist_ok=True)

# Create timestamped log file on first server start
# All worker processes will share the same file via the global attribute
if not hasattr(logging, '_shadeplan_log_file'):
    logging._shadeplan_log_file = logs_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    # Write header to new log file
    with open(logging._shadeplan_log_file, 'w') as f:
        f.write(f"=== ShadePlan Agent Log - Started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

log_filename = logging._shadeplan_log_file

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, mode='a'),  # Append mode
        logging.StreamHandler()  # Also print to console
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to: {log_filename}")

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.urban_cooling_analyst import root_agent, clear_shade_cache


# CORS origins - allow localhost for development and Vercel for production
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://*.vercel.app",
]

# Add production domain if configured
if os.getenv("FRONTEND_URL"):
    CORS_ORIGINS.append(os.getenv("FRONTEND_URL"))


# Pydantic models for request/response
class AnalyzeRequest(BaseModel):
    """Request body for heat analysis endpoint"""
    location: str = Field(..., description="City name or zip code to analyze", min_length=1)


class HeatZone(BaseModel):
    """A single heat zone identified by the analysis"""
    id: int
    geometry: dict
    heat_score: float
    temp_celsius: float
    priority: str
    area_sqm: float
    center: Optional[dict] = None
    in_park: Optional[bool] = None
    plantable: Optional[bool] = None


class AnalysisMetadata(BaseModel):
    """Metadata about the analysis"""
    total_zones_analyzed: int = 0
    data_source: str = "LANDSAT-8/9 Collection 2"
    filtering_summary: Optional[dict] = None
    temp_range: Optional[dict] = None


class AnalyzeResponse(BaseModel):
    """Response body for heat analysis endpoint"""
    location: str
    analysis_date: str
    heat_zones: list[HeatZone]
    metadata: AnalysisMetadata


# Phase 2: Shade Analysis Models
class ShadeRequest(BaseModel):
    """Request body for shade analysis endpoint"""
    location: str = Field(..., description="City name or zip code to analyze", min_length=1)
    date: Optional[str] = Field(default=None, description="Date for analysis (YYYY-MM-DD). Defaults to today.")
    hours: list[int] = Field(default=[14, 16, 18, 20], description="Hours to simulate (UTC)")


class ShadeZone(BaseModel):
    """A zone with shade deficit data"""
    id: int
    geometry: Optional[dict] = None
    heat_score: float
    temp_celsius: Optional[float] = None
    shade_coverage: float
    shade_deficit: float
    combined_score: float
    priority: str
    area_sqm: Optional[float] = None
    center: Optional[dict] = None


class HourlyCoverage(BaseModel):
    """Shade coverage data for a specific hour"""
    hour: int
    coverage_percent: float
    building_shade_percent: Optional[float] = None
    tree_shade_percent: Optional[float] = None
    is_night: bool = False


class ShadeMetadata(BaseModel):
    """Metadata about the shade analysis"""
    total_zones_analyzed: int = 0
    avg_shade_deficit: float = 0
    high_deficit_count: int = 0
    buildings_analyzed: int = 0
    trees_analyzed: int = 0
    simulation_date: str = ""


class ShadeResponse(BaseModel):
    """Response body for shade analysis endpoint"""
    location: str
    analysis_date: str
    simulation_date: str
    zones: list[ShadeZone]
    hourly_coverage: list[HourlyCoverage]
    metadata: ShadeMetadata


class CombinedRequest(BaseModel):
    """Request body for combined heat + shade analysis endpoint"""
    location: str = Field(..., description="City name or zip code to analyze", min_length=1)
    date: Optional[str] = Field(default=None, description="Date for shade simulation (YYYY-MM-DD). Defaults to today.")
    hours: list[int] = Field(default=[14, 16, 18, 20], description="Hours to simulate (UTC)")


# Create FastAPI app
app = FastAPI(
    title="ShadePlan API",
    description="Urban heat analysis API for identifying areas that would benefit from tree planting",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the agent runner
runner = InMemoryRunner(
    agent=root_agent,
    app_name="shadeplan"
)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_heat(request: AnalyzeRequest):
    """
    Analyze urban heat zones for a given location.

    This endpoint uses the Urban Cooling Analyst agent to:
    1. Geocode the location to get coordinates
    2. Fetch LANDSAT thermal imagery
    3. Analyze land use data from OpenStreetMap
    4. Identify the hottest areas suitable for tree planting

    Returns the top 10-20 heat zones with scores and geometries.
    """
    try:
        # Create a new session for this request
        session = await runner.session_service.create_session(
            app_name="shadeplan",
            user_id="api_user"
        )

        # Create the user message
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Analyze heat zones for: {request.location}")]
        )

        # Run the agent and collect responses
        final_response_text = ""
        filter_zones_response = None
        location_name = request.location

        async for event in runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=user_message
        ):
            # Collect text from agent responses
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_response_text = part.text
                    # Capture function responses - these contain the actual structured data
                    if hasattr(part, 'function_response') and part.function_response is not None:
                        func_resp = part.function_response
                        if func_resp.name == 'filter_plantable_zones':
                            filter_zones_response = func_resp.response
                        elif func_resp.name == 'geocode':
                            # Get the proper location name from geocode
                            location_name = func_resp.response.get('location_name', request.location)

        # Use the function response data directly if available (more reliable than LLM text)
        if filter_zones_response:
            heat_zones = _parse_function_response(filter_zones_response, location_name)
        else:
            # Fall back to parsing the agent's text response
            heat_zones = _parse_agent_response(final_response_text, location_name)

        return heat_zones

    except Exception as e:
        import traceback
        print(f"Error in analyze_heat: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


def _parse_function_response(data: dict, location: str) -> AnalyzeResponse:
    """
    Parse the filter_plantable_zones function response directly.

    This is more reliable than parsing the LLM's text output since it
    captures the actual structured data from the tool call.
    """
    # Extract zones from the function response
    zones_data = data.get("zones", [])

    heat_zones = []
    for zone in zones_data[:20]:  # Limit to 20 zones
        heat_zones.append(HeatZone(
            id=zone.get("id", len(heat_zones) + 1),
            geometry=zone.get("geometry", {}),
            heat_score=zone.get("heat_score", 0),
            temp_celsius=zone.get("temp_celsius", 0),
            priority=zone.get("priority", "medium"),
            area_sqm=zone.get("area_sqm", 0),
            center=zone.get("center"),
            in_park=zone.get("in_park"),
            plantable=zone.get("plantable")
        ))

    # Extract metadata from the function response
    stats = data.get("statistics", {})
    filtering = data.get("filtering_summary", {})

    return AnalyzeResponse(
        location=location,
        analysis_date=date.today().isoformat(),
        heat_zones=heat_zones,
        metadata=AnalysisMetadata(
            total_zones_analyzed=filtering.get("original_count", stats.get("total_zones", len(heat_zones))),
            filtering_summary=filtering if filtering else None,
            temp_range=data.get("temp_range")
        )
    )


def _parse_agent_response(response_text: str, location: str) -> AnalyzeResponse:
    """
    Parse the agent's response text to extract heat zone data.

    The agent should return structured JSON, but we handle various formats.
    """
    import json
    import re

    # Try to extract JSON from the response
    json_match = re.search(r'\{[\s\S]*\}', response_text)

    if json_match:
        try:
            data = json.loads(json_match.group())

            # Extract heat zones from various possible structures
            zones_data = data.get("zones", data.get("heat_zones", []))

            heat_zones = []
            for zone in zones_data[:20]:  # Limit to 20 zones
                heat_zones.append(HeatZone(
                    id=zone.get("id", len(heat_zones) + 1),
                    geometry=zone.get("geometry", {}),
                    heat_score=zone.get("heat_score", 0),
                    temp_celsius=zone.get("temp_celsius", 0),
                    priority=zone.get("priority", "medium"),
                    area_sqm=zone.get("area_sqm", 0),
                    center=zone.get("center"),
                    in_park=zone.get("in_park"),
                    plantable=zone.get("plantable")
                ))

            # Extract metadata
            stats = data.get("statistics", data.get("filtering_summary", {}))

            return AnalyzeResponse(
                location=data.get("location", location),
                analysis_date=date.today().isoformat(),
                heat_zones=heat_zones,
                metadata=AnalysisMetadata(
                    total_zones_analyzed=stats.get("original_count", stats.get("total_zones", len(heat_zones))),
                    filtering_summary=data.get("filtering_summary"),
                    temp_range=data.get("temp_range")
                )
            )
        except json.JSONDecodeError:
            pass

    # If we couldn't parse JSON, return empty result with error info
    return AnalyzeResponse(
        location=location,
        analysis_date=date.today().isoformat(),
        heat_zones=[],
        metadata=AnalysisMetadata(
            total_zones_analyzed=0,
            data_source="Analysis incomplete - could not parse agent response"
        )
    )


# =============================================================================
# Phase 2: Shade Analysis Endpoints
# =============================================================================

@app.post("/shade", response_model=ShadeResponse)
async def analyze_shade(request: ShadeRequest):
    """
    Analyze shade coverage for a given location.

    This endpoint uses the Urban Cooling Analyst agent to:
    1. Geocode the location to get coordinates
    2. Fetch building heights from OpenStreetMap
    3. Fetch existing tree canopy data
    4. Calculate sun positions for the specified date
    5. Simulate shade coverage for specified hours

    Returns shade coverage data and identifies areas with shade deficits.
    Note: This is shade-only analysis. Use /analyze-combined for heat + shade.
    """
    try:
        # Clear any previous shade cache
        clear_shade_cache()

        # Determine simulation date
        simulation_date = request.date or date.today().isoformat()

        # Format hours for the prompt
        hours_str = ", ".join(str(h) for h in request.hours)

        # Create a new session for this request
        session = await runner.session_service.create_session(
            app_name="shadeplan",
            user_id="api_user"
        )

        # Create the user message for shade-only analysis
        prompt = f"""Analyze shade coverage for: {request.location}

Please perform shade analysis only (skip heat analysis):
1. First geocode the location
2. Get building heights for the bounding box
3. Get tree canopy data for the same area
4. Calculate sun path for {simulation_date}
5. Simulate shade for hours: {hours_str} (UTC)

Return the results as JSON with hourly shade coverage percentages."""

        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )

        # Run the agent and collect responses
        final_response_text = ""
        async for event in runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=user_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_response_text = part.text

        # Parse the shade response
        return _parse_shade_response(final_response_text, request.location, simulation_date)

    except Exception as e:
        import traceback
        logger.error(f"Error in analyze_shade: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Shade analysis failed: {str(e)}"
        )


@app.post("/analyze-combined", response_model=ShadeResponse)
async def analyze_combined(request: CombinedRequest):
    """
    Analyze heat zones with shade deficit analysis.

    This endpoint combines Phase 1 heat analysis with Phase 2 shade simulation:
    1. Geocode the location
    2. Fetch and analyze LANDSAT thermal imagery
    3. Identify heat zones and plantable areas
    4. Fetch building heights and tree canopy
    5. Simulate shade coverage
    6. Calculate combined heat + shade deficit scores

    Returns zones prioritized by both heat intensity and shade deficit.
    High heat + low shade = highest priority for tree planting.
    """
    try:
        # Clear any previous shade cache
        clear_shade_cache()

        # Determine simulation date
        simulation_date = request.date or date.today().isoformat()

        # Format hours for the prompt
        hours_str = ", ".join(str(h) for h in request.hours)

        # Create a new session for this request
        session = await runner.session_service.create_session(
            app_name="shadeplan",
            user_id="api_user"
        )

        # Create the user message for combined analysis
        prompt = f"""Analyze heat zones with shade deficit for: {request.location}

Please perform BOTH heat analysis AND shade analysis:

HEAT ANALYSIS:
1. Geocode the location
2. Get heat data for the bounding box
3. Get land use data
4. Process thermal data
5. Score heat zones
6. Filter plantable zones

SHADE ANALYSIS:
7. Get building heights for the same bounding box
8. Get tree canopy data
9. Calculate sun path for {simulation_date}
10. Simulate shade for hours: {hours_str} (UTC)
11. Analyze shade deficit to combine heat and shade scores

Return the results as JSON with:
- zones: Array of zones with heat_score, shade_coverage, shade_deficit, combined_score, and priority
- summary: Statistics about the analysis
- hourly_coverage: Shade coverage for each simulated hour"""

        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        )

        # Run the agent and collect responses
        final_response_text = ""
        async for event in runner.run_async(
            user_id="api_user",
            session_id=session.id,
            new_message=user_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        final_response_text = part.text

        # Parse the combined response
        return _parse_shade_response(final_response_text, request.location, simulation_date)

    except Exception as e:
        import traceback
        logger.error(f"Error in analyze_combined: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Combined analysis failed: {str(e)}"
        )


def _parse_shade_response(response_text: str, location: str, simulation_date: str) -> ShadeResponse:
    """
    Parse the agent's response text to extract shade analysis data.
    """
    import json
    import re

    # Try to extract JSON from the response
    json_match = re.search(r'\{[\s\S]*\}', response_text)

    if json_match:
        try:
            data = json.loads(json_match.group())

            # Extract zones
            zones_data = data.get("zones", [])
            zones = []
            for zone in zones_data[:20]:
                zones.append(ShadeZone(
                    id=zone.get("id", len(zones) + 1),
                    geometry=zone.get("geometry"),
                    heat_score=zone.get("heat_score", 0),
                    temp_celsius=zone.get("temp_celsius"),
                    shade_coverage=zone.get("shade_coverage", 0),
                    shade_deficit=zone.get("shade_deficit", 0),
                    combined_score=zone.get("combined_score", 0),
                    priority=zone.get("priority", "medium"),
                    area_sqm=zone.get("area_sqm"),
                    center=zone.get("center")
                ))

            # Extract hourly coverage
            hourly_data = data.get("hourly_coverage", [])
            hourly_coverage = []
            for hour_data in hourly_data:
                hourly_coverage.append(HourlyCoverage(
                    hour=hour_data.get("hour", 0),
                    coverage_percent=hour_data.get("coverage_percent", 0),
                    building_shade_percent=hour_data.get("building_shade_percent"),
                    tree_shade_percent=hour_data.get("tree_shade_percent"),
                    is_night=hour_data.get("is_night", False)
                ))

            # Extract summary/metadata
            summary = data.get("summary", {})

            return ShadeResponse(
                location=data.get("location", location),
                analysis_date=date.today().isoformat(),
                simulation_date=simulation_date,
                zones=zones,
                hourly_coverage=hourly_coverage,
                metadata=ShadeMetadata(
                    total_zones_analyzed=summary.get("total_zones", len(zones)),
                    avg_shade_deficit=summary.get("avg_shade_deficit", 0),
                    high_deficit_count=summary.get("high_deficit_count", 0),
                    buildings_analyzed=summary.get("buildings_analyzed", 0),
                    trees_analyzed=summary.get("trees_analyzed", 0),
                    simulation_date=simulation_date
                )
            )
        except json.JSONDecodeError:
            pass

    # If we couldn't parse JSON, return empty result
    return ShadeResponse(
        location=location,
        analysis_date=date.today().isoformat(),
        simulation_date=simulation_date,
        zones=[],
        hourly_coverage=[],
        metadata=ShadeMetadata(
            simulation_date=simulation_date
        )
    )


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8080, reload=True)
