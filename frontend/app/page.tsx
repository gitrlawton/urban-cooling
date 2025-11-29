'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import SearchForm from './components/SearchForm';
import { AnalyzeResponse } from './types';

// Import MapView dynamically to avoid SSR issues with Leaflet
const MapView = dynamic(() => import('./components/MapView'), { ssr: false });

export default function Home() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  const handleAnalyze = async (location: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/analyze-heat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location }),
      });

      if (!response.ok) {
        throw new Error('Failed to analyze heat zones');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <SearchForm onAnalyze={handleAnalyze} loading={loading} />

        {error && (
          <div className="max-w-md mx-auto mt-4 p-4 bg-red-100 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {result && (
          <div className="mt-8">
            <div className="mb-4 text-center">
              <h2 className="text-xl font-semibold">{result.location}</h2>
              <p className="text-gray-600">
                Found {result.heat_zones.length} heat zones •
                Analyzed {result.metadata.total_zones_analyzed} total zones
              </p>
            </div>
            <MapView heatZones={result.heat_zones} />
          </div>
        )}

        {!result && !loading && (
          <div className="mt-8 text-center text-gray-500">
            Enter a location to see heat zones
          </div>
        )}
      </div>
    </main>
  );
}
