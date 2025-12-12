'use client';

import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { HeatZone, ShadeZone } from '../types';
import HeatZoneLayer from './HeatZoneLayer';
import ShadeLayer from './ShadeLayer';
import Legend from './Legend';
import { ViewMode } from './ViewToggle';

interface MapViewProps {
  heatZones?: HeatZone[] | null;
  shadeZones?: ShadeZone[] | null;
  viewMode: ViewMode;
  selectedHour?: number;
  center?: [number, number];
}

export default function MapView({
  heatZones,
  shadeZones,
  viewMode,
  selectedHour,
  center
}: MapViewProps) {
  const defaultCenter: [number, number] = center || [37.7749, -122.4194]; // San Francisco

  // Determine which layer to show based on view mode
  const hasHeatZones = heatZones && heatZones.length > 0;
  const hasShadeZones = shadeZones && shadeZones.length > 0;

  // Show HeatZoneLayer only when we have heat-only data
  const showHeatLayer = viewMode === 'heat' && hasHeatZones;

  // Show ShadeLayer for shade/combined views, OR for heat view when we only have shade data
  const showShadeLayer = hasShadeZones && (
    viewMode === 'shade' ||
    viewMode === 'combined' ||
    (viewMode === 'heat' && !hasHeatZones)
  );

  // Determine color mode for shade layer
  // Use 'heat' mode when viewing heat with shade data
  const shadeColorMode = viewMode === 'heat' ? 'heat' :
    viewMode === 'shade' ? 'coverage' : 'combined';

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

        {showHeatLayer && <HeatZoneLayer zones={heatZones} />}
        {showShadeLayer && (
          <ShadeLayer
            zones={shadeZones}
            selectedHour={selectedHour}
            colorMode={shadeColorMode}
          />
        )}
      </MapContainer>

      {(showHeatLayer || showShadeLayer) && (
        <Legend viewMode={viewMode} />
      )}
    </div>
  );
}
