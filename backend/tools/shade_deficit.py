"""
Shade Deficit Tool

Calculates shade deficit scores combining heat and shade data.
"""

from typing import Dict, List


def calculate_shade_deficit(
    shade_coverages: List[Dict],
    heat_zones: List[Dict],
    peak_hours: List[int] = None
) -> Dict:
    """
    Calculate shade deficit scores for heat zones.

    Args:
        shade_coverages: List of hourly shade coverage results
        heat_zones: List of heat zones from Phase 1 analysis
        peak_hours: Hours to weight more heavily (default: 10am-4pm, adjusted for UTC)

    Returns:
        Dictionary containing:
            - zones: Heat zones with added shade deficit scores
            - summary: Overall shade deficit statistics
    """
    # Default peak hours (these are typically local times 10am-4pm)
    # For UTC-based calculations, users should adjust based on their timezone
    if peak_hours is None:
        peak_hours = [10, 11, 12, 13, 14, 15, 16]

    # Filter to daylight hours only
    daylight_coverages = [s for s in shade_coverages if not s.get("is_night", True)]

    if not daylight_coverages:
        return {
            "zones": heat_zones,
            "summary": {"error": "No daylight shade data available"}
        }

    # Calculate average shade per grid cell across all hours
    # Weight peak hours more heavily
    first_coverage = daylight_coverages[0]
    rows = first_coverage.get("rows", 0)
    cols = first_coverage.get("cols", 0)
    bbox = first_coverage.get("bbox", [])
    grid_size = first_coverage.get("grid_size", 0.0005)

    if rows == 0 or cols == 0:
        return {
            "zones": heat_zones,
            "summary": {"error": "Invalid shade grid dimensions"}
        }

    # Initialize weighted shade grid
    weighted_shade = [[0.0 for _ in range(cols)] for _ in range(rows)]
    total_weight = 0

    for coverage in daylight_coverages:
        hour = coverage.get("hour", 12)
        grid = coverage.get("grid")

        if grid is None:
            continue

        # Weight peak hours 2x
        weight = 2.0 if hour in peak_hours else 1.0
        total_weight += weight

        for row in range(min(rows, len(grid))):
            for col in range(min(cols, len(grid[row]))):
                weighted_shade[row][col] += grid[row][col] * weight

    # Normalize
    if total_weight > 0:
        for row in range(rows):
            for col in range(cols):
                weighted_shade[row][col] /= total_weight

    # Calculate shade deficit for each heat zone
    zones_with_deficit = []

    for zone in heat_zones:
        center = zone.get("center", {})
        lat = center.get("lat", 0)
        lon = center.get("lon", 0)

        # Find corresponding shade grid cell
        if bbox and len(bbox) == 4:
            west, south, east, north = bbox
            col = int((lon - west) / grid_size)
            row = int((lat - south) / grid_size)

            col = max(0, min(col, cols - 1))
            row = max(0, min(row, rows - 1))

            shade_value = weighted_shade[row][col]
        else:
            shade_value = 0.5  # Default if can't calculate

        # Shade deficit = 1 - shade coverage (higher = less shade = worse)
        shade_deficit = 1.0 - shade_value

        # Combined score: heat_score * shade_deficit
        # High heat + low shade = highest priority
        heat_score = zone.get("heat_score", 50)
        combined_score = (heat_score / 100) * shade_deficit * 100

        zone_with_deficit = zone.copy()
        zone_with_deficit["shade_coverage"] = round(shade_value * 100, 1)
        zone_with_deficit["shade_deficit"] = round(shade_deficit * 100, 1)
        zone_with_deficit["combined_score"] = round(combined_score, 1)

        zones_with_deficit.append(zone_with_deficit)

    # Sort by combined score (highest priority first)
    zones_with_deficit.sort(key=lambda z: z["combined_score"], reverse=True)

    # Calculate summary statistics
    deficits = [z["shade_deficit"] for z in zones_with_deficit]

    return {
        "zones": zones_with_deficit,
        "summary": {
            "total_zones": len(zones_with_deficit),
            "avg_shade_deficit": round(sum(deficits) / len(deficits), 1) if deficits else 0,
            "max_shade_deficit": round(max(deficits), 1) if deficits else 0,
            "high_deficit_count": sum(1 for d in deficits if d >= 70),
            "peak_hours_analyzed": peak_hours
        }
    }


def prioritize_by_heat_and_shade(
    heat_zones: List[Dict],
    shade_deficits: Dict
) -> List[Dict]:
    """
    Re-prioritize heat zones based on combined heat + shade deficit scores.

    Args:
        heat_zones: Original heat zones from Phase 1
        shade_deficits: Shade deficit analysis results

    Returns:
        List of zones sorted by combined priority
    """
    deficit_zones = shade_deficits.get("zones", [])

    # Update priority labels based on combined score
    for zone in deficit_zones:
        combined = zone.get("combined_score", 0)

        if combined >= 70:
            zone["priority"] = "critical"
        elif combined >= 50:
            zone["priority"] = "high"
        elif combined >= 30:
            zone["priority"] = "medium"
        else:
            zone["priority"] = "low"

    return deficit_zones


def calculate_pedestrian_exposure(
    shade_coverages: List[Dict],
    pedestrian_areas: List[Dict],
    peak_pedestrian_hours: List[int] = None
) -> Dict:
    """
    Calculate shade deficit specifically for high-pedestrian-traffic areas.

    This prioritizes areas where people actually walk, such as:
    - Sidewalks along major streets
    - Transit stops
    - Parks and plazas
    - Commercial districts

    Args:
        shade_coverages: List of hourly shade coverage results
        pedestrian_areas: List of pedestrian zones with traffic estimates
        peak_pedestrian_hours: Hours when pedestrian traffic is highest
                              (default: 8-9am, 12-1pm, 5-6pm commute/lunch times)

    Returns:
        Dictionary containing:
            - areas: Pedestrian areas with exposure scores
            - summary: Overall pedestrian exposure statistics
    """
    if peak_pedestrian_hours is None:
        # Default peak pedestrian hours (morning commute, lunch, evening commute)
        peak_pedestrian_hours = [8, 9, 12, 13, 17, 18]

    daylight_coverages = [s for s in shade_coverages if not s.get("is_night", True)]

    if not daylight_coverages:
        return {
            "areas": pedestrian_areas,
            "summary": {"error": "No daylight shade data available"}
        }

    first_coverage = daylight_coverages[0]
    rows = first_coverage.get("rows", 0)
    cols = first_coverage.get("cols", 0)
    bbox = first_coverage.get("bbox", [])
    grid_size = first_coverage.get("grid_size", 0.0005)

    if rows == 0 or cols == 0:
        return {
            "areas": pedestrian_areas,
            "summary": {"error": "Invalid shade grid dimensions"}
        }

    # Build shade grid weighted by pedestrian peak hours
    weighted_shade = [[0.0 for _ in range(cols)] for _ in range(rows)]
    total_weight = 0

    for coverage in daylight_coverages:
        hour = coverage.get("hour", 12)
        grid = coverage.get("grid")

        if grid is None:
            continue

        # Weight pedestrian peak hours 3x (more important than general peak hours)
        weight = 3.0 if hour in peak_pedestrian_hours else 1.0
        total_weight += weight

        for row in range(min(rows, len(grid))):
            for col in range(min(cols, len(grid[row]))):
                weighted_shade[row][col] += grid[row][col] * weight

    # Normalize
    if total_weight > 0:
        for row in range(rows):
            for col in range(cols):
                weighted_shade[row][col] /= total_weight

    # Calculate exposure for each pedestrian area
    areas_with_exposure = []

    for area in pedestrian_areas:
        center = area.get("center", {})
        lat = center.get("lat", 0)
        lon = center.get("lon", 0)

        # Find corresponding shade grid cell
        if bbox and len(bbox) == 4:
            west, south, east, north = bbox
            col = int((lon - west) / grid_size)
            row = int((lat - south) / grid_size)

            col = max(0, min(col, cols - 1))
            row = max(0, min(row, rows - 1))

            shade_value = weighted_shade[row][col]
        else:
            shade_value = 0.5

        # Sun exposure = 1 - shade (higher = more sun = worse for pedestrians)
        sun_exposure = 1.0 - shade_value

        # Pedestrian impact score combines sun exposure with traffic estimate
        # Higher traffic + higher sun exposure = higher impact
        traffic_estimate = area.get("traffic_estimate", 50)  # 0-100 scale
        pedestrian_impact = (sun_exposure * (traffic_estimate / 100)) * 100

        area_with_exposure = area.copy()
        area_with_exposure["shade_coverage"] = round(shade_value * 100, 1)
        area_with_exposure["sun_exposure"] = round(sun_exposure * 100, 1)
        area_with_exposure["pedestrian_impact"] = round(pedestrian_impact, 1)

        # Assign priority based on pedestrian impact
        if pedestrian_impact >= 60:
            area_with_exposure["priority"] = "critical"
        elif pedestrian_impact >= 40:
            area_with_exposure["priority"] = "high"
        elif pedestrian_impact >= 20:
            area_with_exposure["priority"] = "medium"
        else:
            area_with_exposure["priority"] = "low"

        areas_with_exposure.append(area_with_exposure)

    # Sort by pedestrian impact (highest first)
    areas_with_exposure.sort(key=lambda a: a["pedestrian_impact"], reverse=True)

    # Calculate summary
    exposures = [a["sun_exposure"] for a in areas_with_exposure]
    impacts = [a["pedestrian_impact"] for a in areas_with_exposure]

    return {
        "areas": areas_with_exposure,
        "summary": {
            "total_areas": len(areas_with_exposure),
            "avg_sun_exposure": round(sum(exposures) / len(exposures), 1) if exposures else 0,
            "avg_pedestrian_impact": round(sum(impacts) / len(impacts), 1) if impacts else 0,
            "critical_areas_count": sum(1 for a in areas_with_exposure if a["priority"] == "critical"),
            "high_priority_count": sum(1 for a in areas_with_exposure if a["priority"] in ["critical", "high"]),
            "peak_pedestrian_hours": peak_pedestrian_hours
        }
    }


def identify_priority_planting_zones(
    shade_deficit_results: Dict,
    pedestrian_exposure_results: Dict = None,
    max_zones: int = 10
) -> List[Dict]:
    """
    Identify the highest priority zones for tree planting based on
    combined heat, shade deficit, and pedestrian exposure analysis.

    Args:
        shade_deficit_results: Results from calculate_shade_deficit
        pedestrian_exposure_results: Optional results from calculate_pedestrian_exposure
        max_zones: Maximum number of priority zones to return

    Returns:
        List of priority zones sorted by overall importance
    """
    priority_zones = []

    # Get zones from shade deficit analysis
    deficit_zones = shade_deficit_results.get("zones", [])

    for zone in deficit_zones:
        priority_zone = {
            "id": zone.get("id"),
            "center": zone.get("center"),
            "heat_score": zone.get("heat_score", 0),
            "shade_deficit": zone.get("shade_deficit", 0),
            "combined_score": zone.get("combined_score", 0),
            "priority": zone.get("priority", "low"),
            "reasons": []
        }

        # Add reasons for prioritization
        if zone.get("heat_score", 0) >= 70:
            priority_zone["reasons"].append("High heat zone")
        if zone.get("shade_deficit", 0) >= 70:
            priority_zone["reasons"].append("Severe shade deficit")
        if zone.get("combined_score", 0) >= 70:
            priority_zone["reasons"].append("Critical combined score")

        priority_zones.append(priority_zone)

    # If pedestrian data available, boost scores for high-traffic areas
    if pedestrian_exposure_results:
        pedestrian_areas = pedestrian_exposure_results.get("areas", [])

        for pzone in priority_zones:
            zone_center = pzone.get("center", {})
            zone_lat = zone_center.get("lat", 0)
            zone_lon = zone_center.get("lon", 0)

            # Find nearby pedestrian areas (simple proximity check)
            for parea in pedestrian_areas:
                area_center = parea.get("center", {})
                area_lat = area_center.get("lat", 0)
                area_lon = area_center.get("lon", 0)

                # Check if within ~100m (roughly 0.001 degrees)
                if abs(zone_lat - area_lat) < 0.001 and abs(zone_lon - area_lon) < 0.001:
                    # Boost combined score by pedestrian impact factor
                    pedestrian_boost = parea.get("pedestrian_impact", 0) * 0.3
                    pzone["combined_score"] = round(
                        pzone["combined_score"] + pedestrian_boost, 1
                    )
                    pzone["pedestrian_impact"] = parea.get("pedestrian_impact", 0)
                    pzone["reasons"].append("High pedestrian traffic area")

                    # Update priority if boosted significantly
                    if pzone["combined_score"] >= 70:
                        pzone["priority"] = "critical"
                    elif pzone["combined_score"] >= 50:
                        pzone["priority"] = "high"
                    break

    # Sort by combined score and return top zones
    priority_zones.sort(key=lambda z: z["combined_score"], reverse=True)

    return priority_zones[:max_zones]
