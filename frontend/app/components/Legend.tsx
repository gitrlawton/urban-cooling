'use client';

import { ViewMode } from './ViewToggle';

interface LegendProps {
  viewMode?: ViewMode;
}

export default function Legend({ viewMode = 'heat' }: LegendProps) {
  if (viewMode === 'heat') {
    return (
      <div className="absolute bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg z-[1000]">
        <h3 className="font-bold text-sm mb-2">Heat Score</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-600 rounded"></div>
            <span>High (80-100)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-orange-500 rounded"></div>
            <span>Medium (60-79)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-400 rounded"></div>
            <span>Low (40-59)</span>
          </div>
        </div>
      </div>
    );
  }

  if (viewMode === 'shade') {
    return (
      <div className="absolute bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg z-[1000]">
        <h3 className="font-bold text-sm mb-2">Shade Coverage</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-600 rounded"></div>
            <span>Good (70%+)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-600 rounded"></div>
            <span>Moderate (40-69%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-600 rounded"></div>
            <span>Poor (&lt;40%)</span>
          </div>
        </div>
      </div>
    );
  }

  // Combined view
  return (
    <div className="absolute bottom-4 right-4 bg-white p-4 rounded-lg shadow-lg z-[1000]">
      <h3 className="font-bold text-sm mb-2">Priority Score</h3>
      <p className="text-xs text-gray-500 mb-2">Heat + Shade Deficit</p>
      <div className="space-y-1 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-600 rounded"></div>
          <span>Critical (70+)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-500 rounded"></div>
          <span>High (50-69)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-yellow-600 rounded"></div>
          <span>Medium (30-49)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-600 rounded"></div>
          <span>Low (&lt;30)</span>
        </div>
      </div>
    </div>
  );
}
