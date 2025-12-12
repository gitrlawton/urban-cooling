'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import SearchForm, { AnalysisMode } from './components/SearchForm';
import { ViewMode } from './components/ViewToggle';
import { AnalyzeResponse, ShadeAnalysisResponse } from './types';

// Import components dynamically to avoid SSR issues with Leaflet
const MapView = dynamic(() => import('./components/MapView'), { ssr: false });
const ViewToggle = dynamic(() => import('./components/ViewToggle'), { ssr: false });
const TimeSlider = dynamic(() => import('./components/TimeSlider'), { ssr: false });

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatResult, setHeatResult] = useState<AnalyzeResponse | null>(null);
  const [shadeResult, setShadeResult] = useState<ShadeAnalysisResponse | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('heat');
  const [selectedHour, setSelectedHour] = useState(14);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>('heat');

  const handleAnalyze = async (location: string, mode: AnalysisMode) => {
    setLoading(true);
    setError(null);
    setAnalysisMode(mode);

    try {
      if (mode === 'heat') {
        // Heat-only analysis
        const response = await fetch('/api/analyze-heat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ location }),
        });

        if (!response.ok) {
          throw new Error('Failed to analyze heat zones');
        }

        const data = await response.json();
        setHeatResult(data);
        setShadeResult(null);
        setViewMode('heat');
      } else {
        // Combined heat + shade analysis
        const response = await fetch('/api/analyze-combined', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            location,
            hours: [14, 16, 18, 20]
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to analyze heat and shade zones');
        }

        const data: ShadeAnalysisResponse = await response.json();
        setShadeResult(data);
        setHeatResult(null);
        setViewMode('combined');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleViewChange = (newView: ViewMode) => {
    // Only allow shade/combined views if we have shade data
    if ((newView === 'shade' || newView === 'combined') && !shadeResult) {
      return;
    }
    setViewMode(newView);
  };

  const handleHourChange = (hour: number) => {
    setSelectedHour(hour);
  };

  // Determine what data is available
  const hasHeatData = heatResult && heatResult.heat_zones.length > 0;
  const hasShadeData = shadeResult && shadeResult.zones.length > 0;
  const hasAnyData = hasHeatData || hasShadeData;

  // Get location name from whichever result we have
  const locationName = heatResult?.location || shadeResult?.location || '';

  // Get zone counts
  const zoneCount = hasShadeData
    ? shadeResult.zones.length
    : (hasHeatData ? heatResult.heat_zones.length : 0);

  const totalAnalyzed = hasShadeData
    ? shadeResult.metadata.total_zones_analyzed
    : (hasHeatData ? heatResult.metadata.total_zones_analyzed : 0);

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <SearchForm onAnalyze={handleAnalyze} loading={loading} />

        {error && (
          <div className="max-w-md mx-auto mt-4 p-4 bg-red-100 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {hasAnyData && (
          <div className="mt-8">
            {/* Header with location info */}
            <div className="mb-4 text-center">
              <h2 className="text-xl font-semibold">{locationName}</h2>
              <p className="text-sm text-blue-600 mb-1">
                {analysisMode === 'combined' ? 'Heat + Shade Analysis' : 'Heat Analysis'}
              </p>
              <p className="text-gray-600">
                Found {zoneCount} zones • Analyzed {totalAnalyzed} total zones
                {hasShadeData && shadeResult.metadata.avg_shade_deficit > 0 && (
                  <span> • Avg shade deficit: {shadeResult.metadata.avg_shade_deficit}%</span>
                )}
              </p>
            </div>

            {/* Controls row */}
            <div className="flex flex-wrap justify-center items-start gap-4 mb-4">
              {/* View toggle */}
              <ViewToggle
                currentView={viewMode}
                onChange={handleViewChange}
                disabled={loading}
                shadeAvailable={!!hasShadeData}
              />

              {/* Time slider - only show for shade/combined views with shade data */}
              {hasShadeData && (viewMode === 'shade' || viewMode === 'combined') && (
                <TimeSlider
                  onChange={handleHourChange}
                  initialHour={selectedHour}
                  sunrise={6}
                  sunset={20}
                  disabled={loading}
                />
              )}
            </div>

            {/* Map */}
            <MapView
              heatZones={heatResult?.heat_zones}
              shadeZones={shadeResult?.zones}
              viewMode={viewMode}
              selectedHour={selectedHour}
            />

            {/* Hourly coverage summary for shade data */}
            {hasShadeData && shadeResult.hourly_coverage.length > 0 && (
              <div className="mt-4 max-w-2xl mx-auto">
                <h3 className="font-semibold text-sm mb-2 text-center">Hourly Shade Coverage</h3>
                <div className="flex justify-center gap-2 flex-wrap">
                  {shadeResult.hourly_coverage.map((hour) => (
                    <div
                      key={hour.hour}
                      className={`px-3 py-2 rounded text-xs ${
                        hour.hour === selectedHour
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      <div className="font-medium">{hour.hour}:00 UTC</div>
                      <div>{hour.coverage_percent.toFixed(1)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {!hasAnyData && !loading && (
          <div className="mt-8 text-center text-gray-500">
            Enter a location to see heat zones
          </div>
        )}
      </div>
    </main>
  );
}
