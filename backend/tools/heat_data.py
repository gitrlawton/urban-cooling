"""
Heat Data Fetching Tool

Fetches LANDSAT thermal imagery using Google Earth Engine.
Provides surface temperature data for urban heat analysis.
"""

import os
import ee
from typing import Dict, List


def fetch_heat_data(bbox: List[float], date_range: str = "2024-06-01,2024-08-31") -> Dict:
    """
    Fetch LANDSAT thermal imagery for given bounding box using Google Earth Engine.

    Args:
        bbox: Bounding box [west, south, east, north] in degrees
        date_range: Date range as "YYYY-MM-DD,YYYY-MM-DD" (start,end)
                   Default is summer 2024

    Returns:
        Dictionary containing:
            - source: Data source identifier
            - bbox: Input bounding box
            - date_range: Input date range
            - thermal_samples: List of sampled temperature points with geometries
            - statistics: Mean, min, max temperatures in Celsius
            - resolution: Spatial resolution in meters
            - sample_count: Number of sample points

    Raises:
        ValueError: If date range format is invalid or bbox is invalid
        ee.EEException: If Earth Engine API fails

    Example:
        >>> bbox = [-122.5, 37.7, -122.3, 37.9]  # San Francisco area
        >>> data = fetch_heat_data(bbox, "2024-07-01,2024-07-31")
        >>> print(data["statistics"]["mean_temp_celsius"])
        28.5
    """
    # Validate inputs
    if not bbox or len(bbox) != 4:
        raise ValueError("bbox must be a list of 4 values: [west, south, east, north]")

    if not all(isinstance(x, (int, float)) for x in bbox):
        raise ValueError("bbox values must be numeric")

    if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
        raise ValueError("Invalid bbox: west must be < east and south must be < north")

    # Parse and validate date range
    try:
        start_date, end_date = date_range.split(',')
        # Basic date format validation
        if len(start_date) != 10 or len(end_date) != 10:
            raise ValueError("Dates must be in YYYY-MM-DD format")
    except ValueError as e:
        raise ValueError(f"Invalid date_range format. Expected 'YYYY-MM-DD,YYYY-MM-DD': {str(e)}")

    # Get GCP project ID from environment
    gcp_project_id = os.getenv("GCP_PROJECT_ID", "shadeplan")

    try:
        # Initialize Earth Engine (uses authenticated credentials)
        ee.Initialize(project=gcp_project_id)

        # Define area of interest
        aoi = ee.Geometry.Rectangle(bbox)

        # Get LANDSAT 8/9 Collection 2 Level-2 (surface temperature data)
        # ST_B10 is the surface temperature band
        collection = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                       .filterBounds(aoi)
                       .filterDate(start_date, end_date)
                       .filter(ee.Filter.lt('CLOUD_COVER', 20)))  # Less than 20% cloud cover

        # Check if any images found
        count = collection.size().getInfo()
        if count == 0:
            raise ValueError(
                f"No LANDSAT images found for bbox {bbox} and date range {date_range}. "
                "Try expanding the date range or checking a different location."
            )

        # Select thermal band (ST_B10 = Surface Temperature)
        thermal = collection.select('ST_B10')

        # Get median composite (reduces cloud/noise effects)
        thermal_median = thermal.median()

        # Convert to Celsius
        # LANDSAT Collection 2 ST_B10: Digital Number to Kelvin = DN * 0.00341802 + 149.0
        # Then Kelvin to Celsius = K - 273.15
        thermal_celsius = thermal_median.multiply(0.00341802).add(149.0).subtract(273.15)

        # Sample the thermal data as a grid
        sample = thermal_celsius.sample(
            region=aoi,
            scale=30,  # 30m resolution (LANDSAT resolution)
            numPixels=5000,  # Maximum sample points
            geometries=True  # Include point geometries
        )

        # Get the sampled data
        samples = sample.getInfo()

        # Also get summary statistics
        stats = thermal_celsius.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                reducer2=ee.Reducer.minMax(),
                sharedInputs=True
            ),
            geometry=aoi,
            scale=30,
            maxPixels=1e9
        ).getInfo()

        return {
            "source": "LANDSAT-8/9 Collection 2",
            "bbox": bbox,
            "date_range": date_range,
            "thermal_samples": samples.get('features', []),
            "statistics": {
                "mean_temp_celsius": stats.get('ST_B10_mean'),
                "min_temp_celsius": stats.get('ST_B10_min'),
                "max_temp_celsius": stats.get('ST_B10_max')
            },
            "resolution": 30,  # meters
            "sample_count": len(samples.get('features', [])),
            "image_count": count
        }

    except ee.EEException as e:
        raise ee.EEException(f"Earth Engine API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error fetching heat data: {str(e)}")
