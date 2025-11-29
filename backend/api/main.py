"""
ShadePlan FastAPI Application

Provides REST API endpoints for urban heat analysis.
"""

import os
from datetime import date
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.urban_cooling_analyst import root_agent


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

        # Parse the agent's response to extract heat zones
        # The agent should return structured JSON
        heat_zones = _parse_agent_response(final_response_text, request.location)

        return heat_zones

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
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


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8080, reload=True)
