'use client';

import { useState } from 'react';

interface SearchFormProps {
  onAnalyze: (location: string) => void;
  loading: boolean;
}

export default function SearchForm({ onAnalyze, loading }: SearchFormProps) {
  const [location, setLocation] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (location.trim()) {
      onAnalyze(location);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">ShadePlan</h1>
      <p className="text-gray-600 mb-4">
        Identify the hottest areas in your city that need trees
      </p>

      <div className="flex gap-2">
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

      {loading && (
        <p className="mt-4 text-sm text-gray-600">
          Fetching heat data and analyzing zones...
        </p>
      )}
    </form>
  );
}
