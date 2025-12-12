'use client';

import { useState } from 'react';

export type AnalysisMode = 'heat' | 'combined';

interface SearchFormProps {
  onAnalyze: (location: string, mode: AnalysisMode) => void;
  loading: boolean;
}

export default function SearchForm({ onAnalyze, loading }: SearchFormProps) {
  const [location, setLocation] = useState('');
  const [mode, setMode] = useState<AnalysisMode>('heat');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (location.trim()) {
      onAnalyze(location, mode);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">ShadePlan</h1>
      <p className="text-gray-600 mb-4">
        Identify the hottest areas in your city that need trees
      </p>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Enter city or zip code..."
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !location.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      {/* Analysis mode toggle */}
      <div className="flex items-center justify-center gap-4">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="mode"
            value="heat"
            checked={mode === 'heat'}
            onChange={() => setMode('heat')}
            disabled={loading}
            className="w-4 h-4 text-blue-600"
          />
          <span className="text-sm">Heat Only</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="mode"
            value="combined"
            checked={mode === 'combined'}
            onChange={() => setMode('combined')}
            disabled={loading}
            className="w-4 h-4 text-blue-600"
          />
          <span className="text-sm">Heat + Shade</span>
        </label>
      </div>

      {mode === 'combined' && (
        <p className="mt-2 text-xs text-gray-500 text-center">
          Combined analysis includes shade simulation (takes longer)
        </p>
      )}

      {loading && (
        <p className="mt-4 text-sm text-gray-600 text-center">
          {mode === 'combined'
            ? 'Analyzing heat zones and simulating shade coverage...'
            : 'Fetching heat data and analyzing zones...'}
        </p>
      )}
    </form>
  );
}
