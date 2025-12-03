"""
Sun Path Calculator

Calculates solar position throughout the day for shade simulation.
Uses the NOAA solar position algorithm.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List


def calculate_sun_path(lat: float, lon: float, date: str) -> Dict:
    """
    Calculate sun positions throughout the day.

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        date: Date string in YYYY-MM-DD format

    Returns:
        Dictionary containing:
            - positions: List of hourly sun positions (azimuth, altitude)
            - sunrise: Sunrise time
            - sunset: Sunset time
            - solar_noon: Solar noon time
    """
    # Parse date
    dt = datetime.strptime(date, "%Y-%m-%d")

    positions = []
    sunrise_hour = None
    sunset_hour = None
    max_altitude = -90
    solar_noon_hour = None
    prev_altitude = None

    # Calculate position for each hour
    for hour in range(24):
        current_time = dt.replace(hour=hour, minute=0)

        azimuth, altitude = _calculate_solar_position(lat, lon, current_time)

        positions.append({
            "hour": hour,
            "azimuth": round(azimuth, 2),
            "altitude": round(altitude, 2),
            "is_daylight": altitude > 0
        })

        # Track sunrise (transition from negative to positive altitude)
        if prev_altitude is not None and prev_altitude <= 0 and altitude > 0:
            sunrise_hour = hour

        # Track sunset (transition from positive to negative altitude)
        if prev_altitude is not None and prev_altitude > 0 and altitude <= 0:
            sunset_hour = hour - 1  # Last hour with positive altitude

        # Track solar noon (maximum altitude)
        if altitude > max_altitude:
            max_altitude = altitude
            solar_noon_hour = hour

        prev_altitude = altitude

    # Find the main daylight period (longest consecutive daylight stretch)
    # This handles cases where UTC times cause day to wrap around midnight
    daylight_hours = [p["hour"] for p in positions if p["is_daylight"]]

    if daylight_hours:
        # Find consecutive sequences
        sequences = []
        current_seq = [daylight_hours[0]]

        for i in range(1, len(daylight_hours)):
            if daylight_hours[i] == daylight_hours[i-1] + 1:
                current_seq.append(daylight_hours[i])
            else:
                sequences.append(current_seq)
                current_seq = [daylight_hours[i]]
        sequences.append(current_seq)

        # Handle wrap-around: if sequence ends at 23 and starts at 0, merge them
        if len(sequences) > 1 and sequences[-1][-1] == 23 and sequences[0][0] == 0:
            # Merge last and first sequences (wrap around midnight)
            # Keep them as the main daylight sequence
            merged = sequences[-1] + sequences[0]
            sequences = [merged] + sequences[1:-1]

        # Find the longest sequence (main daylight period)
        longest_seq = max(sequences, key=len)

        # Use the longest sequence for sunrise/sunset
        sunrise_hour = longest_seq[0]
        # For sunset, find the last hour before it goes below horizon
        # If sequence wraps around (contains both high and low hours), find the actual end
        if longest_seq[-1] < longest_seq[0]:
            # Wrapped sequence - sunset is at hour before gap
            # Find where the sequence transitions from high (>12) to low (<12)
            for i, h in enumerate(longest_seq):
                if i > 0 and longest_seq[i] < longest_seq[i-1]:
                    sunset_hour = longest_seq[i-1]
                    break
            else:
                sunset_hour = longest_seq[-1]
        else:
            sunset_hour = longest_seq[-1]

    return {
        "date": date,
        "latitude": lat,
        "longitude": lon,
        "positions": positions,
        "sunrise": f"{sunrise_hour:02d}:00" if sunrise_hour else None,
        "sunset": f"{sunset_hour:02d}:00" if sunset_hour else None,
        "solar_noon": f"{solar_noon_hour:02d}:00" if solar_noon_hour else None,
        "max_altitude": round(max_altitude, 2)
    }


def _calculate_solar_position(lat: float, lon: float, dt: datetime) -> tuple:
    """
    Calculate solar azimuth and altitude for a given time and location.

    Uses simplified NOAA algorithm.

    Returns:
        Tuple of (azimuth, altitude) in degrees
    """
    # Day of year
    day_of_year = dt.timetuple().tm_yday

    # Hour as decimal
    hour = dt.hour + dt.minute / 60.0

    # Convert latitude to radians
    lat_rad = math.radians(lat)

    # Solar declination (simplified)
    declination = 23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81)))
    dec_rad = math.radians(declination)

    # Hour angle
    # Solar noon is approximately at 12:00 local solar time
    # Adjust for longitude (rough approximation)
    solar_time = hour + lon / 15.0
    hour_angle = 15 * (solar_time - 12)  # degrees
    hour_angle_rad = math.radians(hour_angle)

    # Solar altitude
    sin_altitude = (math.sin(lat_rad) * math.sin(dec_rad) +
                    math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_angle_rad))
    altitude = math.degrees(math.asin(max(-1, min(1, sin_altitude))))

    # Solar azimuth
    cos_azimuth = ((math.sin(dec_rad) - math.sin(lat_rad) * sin_altitude) /
                   (math.cos(lat_rad) * math.cos(math.radians(altitude)) + 0.0001))
    azimuth = math.degrees(math.acos(max(-1, min(1, cos_azimuth))))

    # Adjust azimuth for afternoon
    if hour_angle > 0:
        azimuth = 360 - azimuth

    return azimuth, altitude
