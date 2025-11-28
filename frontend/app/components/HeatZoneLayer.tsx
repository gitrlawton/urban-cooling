'use client';

import { Polygon, Popup, useMap } from 'react-leaflet';
import { HeatZone } from '../types';
import { useEffect } from 'react';
import L from 'leaflet';

interface HeatZoneLayerProps {
  zones: HeatZone[];
}

export default function HeatZoneLayer({ zones }: HeatZoneLayerProps) {
  const map = useMap();

  // Fit map to show all zones
  useEffect(() => {
    if (zones.length > 0) {
      const bounds = zones.map(zone =>
        zone.geometry.coordinates[0].map(coord => [coord[1], coord[0]] as [number, number])
      );
      const allBounds = L.latLngBounds(bounds.flat());
      map.fitBounds(allBounds);
    }
  }, [zones, map]);

  const getColor = (score: number) => {
    if (score >= 80) return '#dc2626'; // red-600
    if (score >= 60) return '#f97316'; // orange-500
    return '#fbbf24'; // yellow-400
  };

  return (
    <>
      {zones.map((zone) => (
        <Polygon
          key={zone.id}
          positions={zone.geometry.coordinates[0].map(coord => [coord[1], coord[0]])}
          pathOptions={{
            color: getColor(zone.heat_score),
            fillColor: getColor(zone.heat_score),
            fillOpacity: 0.5,
            weight: 2
          }}
        >
          <Popup>
            <div className="text-sm">
              <p className="font-bold">Heat Zone #{zone.id}</p>
              <p>Heat Score: {zone.heat_score.toFixed(1)}</p>
              <p>Temperature: {zone.temp_celsius.toFixed(1)}°C</p>
              <p>Priority: {zone.priority}</p>
              <p>Area: {zone.area_sqm.toFixed(0)} m²</p>
            </div>
          </Popup>
        </Polygon>
      ))}
    </>
  );
}
