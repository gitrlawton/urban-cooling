'use client';

import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { HeatZone } from '../types';
import HeatZoneLayer from './HeatZoneLayer';
import Legend from './Legend';

interface MapViewProps {
  heatZones: HeatZone[] | null;
  center?: [number, number];
}

export default function MapView({ heatZones, center }: MapViewProps) {
  const defaultCenter: [number, number] = center || [37.7749, -122.4194]; // San Francisco

  return (
    <div className="relative w-full h-[600px]">
      <MapContainer
        center={defaultCenter}
        zoom={12}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {heatZones && <HeatZoneLayer zones={heatZones} />}
      </MapContainer>

      {heatZones && <Legend />}
    </div>
  );
}
