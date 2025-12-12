'use client';

import { useEffect } from 'react';
import { Polygon, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import { ShadeZone } from '../types';

type ColorMode = 'coverage' | 'deficit' | 'combined' | 'heat';

interface ShadeLayerProps {
  zones: ShadeZone[];
  selectedHour?: number;
  colorMode?: ColorMode;
}

export default function ShadeLayer({
  zones,
  selectedHour,
  colorMode = 'combined'
}: ShadeLayerProps) {
  const map = useMap();

  // Fit map to show all zones
  useEffect(() => {
    if (zones.length > 0) {
      const validBounds: [number, number][] = [];

      zones.forEach(zone => {
        if (zone.geometry && zone.geometry.coordinates) {
          // Add polygon coordinates
          zone.geometry.coordinates[0].forEach(coord => {
            validBounds.push([coord[1], coord[0]]);
          });
        } else if (zone.center) {
          // Add center point
          validBounds.push([zone.center.lat, zone.center.lon]);
        }
      });

      if (validBounds.length > 0) {
        const bounds = L.latLngBounds(validBounds);
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    }
  }, [zones, map]);

  // Color based on heat score (same as HeatZoneLayer)
  const getHeatColor = (heatScore: number) => {
    if (heatScore >= 80) return '#dc2626'; // red-600
    if (heatScore >= 60) return '#f97316'; // orange-500
    return '#fbbf24'; // yellow-400
  };

  // Color based on shade coverage (green = good shade, red = poor shade)
  const getShadeColor = (shadeCoverage: number) => {
    if (shadeCoverage >= 70) return '#16a34a'; // green-600 - good shade
    if (shadeCoverage >= 40) return '#ca8a04'; // yellow-600 - moderate shade
    return '#dc2626'; // red-600 - poor shade
  };

  // Color based on shade deficit (red = high deficit, green = low deficit)
  const getDeficitColor = (shadeDeficit: number) => {
    if (shadeDeficit >= 70) return '#dc2626'; // red-600 - critical deficit
    if (shadeDeficit >= 40) return '#f97316'; // orange-500 - high deficit
    return '#16a34a'; // green-600 - low deficit
  };

  // Combined score color (for priority visualization)
  const getCombinedColor = (combinedScore: number) => {
    if (combinedScore >= 70) return '#dc2626'; // red-600 - critical priority
    if (combinedScore >= 50) return '#f97316'; // orange-500 - high priority
    if (combinedScore >= 30) return '#ca8a04'; // yellow-600 - medium priority
    return '#16a34a'; // green-600 - low priority
  };

  const getColor = (zone: ShadeZone) => {
    switch (colorMode) {
      case 'heat':
        return getHeatColor(zone.heat_score);
      case 'coverage':
        return getShadeColor(zone.shade_coverage);
      case 'deficit':
        return getDeficitColor(zone.shade_deficit);
      case 'combined':
      default:
        return getCombinedColor(zone.combined_score);
    }
  };

  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'critical': return 'Critical';
      case 'high': return 'High';
      case 'medium': return 'Medium';
      case 'low': return 'Low';
      default: return priority;
    }
  };

  return (
    <>
      {zones.map((zone) => {
        // Handle zones with geometry (polygons)
        if (zone.geometry && zone.geometry.coordinates) {
          return (
            <Polygon
              key={zone.id}
              positions={zone.geometry.coordinates[0].map(coord => [coord[1], coord[0]])}
              pathOptions={{
                color: getColor(zone),
                fillColor: getColor(zone),
                fillOpacity: 0.5,
                weight: 2
              }}
            >
              <Popup>
                <div className="text-sm min-w-[180px]">
                  <p className="font-bold text-base mb-2">Zone #{zone.id}</p>

                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Heat Score:</span>
                      <span className="font-medium">{zone.heat_score.toFixed(1)}</span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-600">Shade Coverage:</span>
                      <span className="font-medium">{zone.shade_coverage.toFixed(1)}%</span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-600">Shade Deficit:</span>
                      <span className="font-medium text-red-600">{zone.shade_deficit.toFixed(1)}%</span>
                    </div>

                    <div className="flex justify-between border-t pt-1 mt-1">
                      <span className="text-gray-600">Combined Score:</span>
                      <span className="font-bold">{zone.combined_score.toFixed(1)}</span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-gray-600">Priority:</span>
                      <span className={`font-medium ${
                        zone.priority === 'critical' ? 'text-red-600' :
                        zone.priority === 'high' ? 'text-orange-500' :
                        zone.priority === 'medium' ? 'text-yellow-600' :
                        'text-green-600'
                      }`}>
                        {getPriorityLabel(zone.priority)}
                      </span>
                    </div>

                    {zone.temp_celsius && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Temperature:</span>
                        <span className="font-medium">{zone.temp_celsius.toFixed(1)}°C</span>
                      </div>
                    )}

                    {zone.area_sqm && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Area:</span>
                        <span className="font-medium">{zone.area_sqm.toFixed(0)} m²</span>
                      </div>
                    )}
                  </div>

                  {selectedHour !== undefined && (
                    <p className="text-xs text-gray-500 mt-2 pt-2 border-t">
                      Showing shade at {selectedHour}:00 UTC
                    </p>
                  )}
                </div>
              </Popup>
            </Polygon>
          );
        }

        // Handle zones with only center point (circles)
        if (zone.center) {
          return (
            <Circle
              key={zone.id}
              center={[zone.center.lat, zone.center.lon]}
              radius={50}
              pathOptions={{
                color: getColor(zone),
                fillColor: getColor(zone),
                fillOpacity: 0.5,
                weight: 2
              }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold">Zone #{zone.id}</p>
                  <p>Heat Score: {zone.heat_score.toFixed(1)}</p>
                  <p>Shade Coverage: {zone.shade_coverage.toFixed(1)}%</p>
                  <p>Shade Deficit: {zone.shade_deficit.toFixed(1)}%</p>
                  <p>Combined Score: {zone.combined_score.toFixed(1)}</p>
                  <p>Priority: {getPriorityLabel(zone.priority)}</p>
                </div>
              </Popup>
            </Circle>
          );
        }

        return null;
      })}
    </>
  );
}
