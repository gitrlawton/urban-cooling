'use client';

import { useState, useEffect } from 'react';

interface TimeSliderProps {
  onChange: (hour: number) => void;
  sunrise?: number;
  sunset?: number;
  initialHour?: number;
  disabled?: boolean;
}

export default function TimeSlider({
  onChange,
  sunrise = 6,
  sunset = 20,
  initialHour = 12,
  disabled = false
}: TimeSliderProps) {
  const [hour, setHour] = useState(initialHour);

  // Update hour if initialHour changes (e.g., from parent)
  useEffect(() => {
    setHour(initialHour);
  }, [initialHour]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newHour = parseInt(e.target.value);
    setHour(newHour);
    onChange(newHour);
  };

  const formatHour = (h: number) => {
    const period = h >= 12 ? 'PM' : 'AM';
    const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${hour12}:00 ${period}`;
  };

  const isDaylight = hour >= sunrise && hour <= sunset;

  // Calculate sun position for visual indicator (0-100%)
  const sunPosition = ((hour - sunrise) / (sunset - sunrise)) * 100;
  const clampedSunPosition = Math.max(0, Math.min(100, sunPosition));

  // Calculate sun altitude indicator (peaks at solar noon)
  const solarNoon = (sunrise + sunset) / 2;
  const distanceFromNoon = Math.abs(hour - solarNoon);
  const maxDistance = (sunset - sunrise) / 2;
  const altitudePercent = Math.max(0, 100 - (distanceFromNoon / maxDistance) * 100);

  return (
    <div className={`bg-white p-4 rounded-lg shadow-lg ${disabled ? 'opacity-50' : ''}`}>
      <h3 className="font-bold text-sm mb-2">Time of Day</h3>

      {/* Sun arc visualization */}
      <div className="relative h-8 mb-2">
        <div className="absolute inset-x-0 bottom-0 h-px bg-gray-300"></div>
        {/* Sun arc path */}
        <svg
          className="absolute inset-0 w-full h-full"
          viewBox="0 0 100 32"
          preserveAspectRatio="none"
        >
          <path
            d="M 0 32 Q 50 0 100 32"
            fill="none"
            stroke="#fbbf24"
            strokeWidth="1"
            strokeDasharray="2,2"
          />
        </svg>
        {/* Sun position indicator */}
        {isDaylight && (
          <div
            className="absolute w-4 h-4 -ml-2 transition-all duration-200"
            style={{
              left: `${clampedSunPosition}%`,
              bottom: `${altitudePercent * 0.7}%`,
            }}
          >
            <div className="w-4 h-4 bg-yellow-400 rounded-full shadow-lg border-2 border-yellow-500"></div>
          </div>
        )}
      </div>

      {/* Slider */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 w-16">{formatHour(sunrise)}</span>
        <input
          type="range"
          min={sunrise}
          max={sunset}
          value={hour}
          onChange={handleChange}
          disabled={disabled}
          className="flex-1 h-2 bg-gradient-to-r from-orange-300 via-yellow-300 to-orange-300 rounded-lg appearance-none cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:h-4
            [&::-webkit-slider-thumb]:bg-blue-600
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:cursor-pointer
            [&::-webkit-slider-thumb]:shadow-md
            [&::-moz-range-thumb]:w-4
            [&::-moz-range-thumb]:h-4
            [&::-moz-range-thumb]:bg-blue-600
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:cursor-pointer
            [&::-moz-range-thumb]:border-0
            disabled:cursor-not-allowed"
        />
        <span className="text-xs text-gray-500 w-16 text-right">{formatHour(sunset)}</span>
      </div>

      {/* Current time display */}
      <div className="text-center mt-3">
        <span className="text-xl font-semibold text-gray-800">{formatHour(hour)}</span>
        <span className="ml-2 text-lg">
          {isDaylight ? '\u2600\uFE0F' : '\uD83C\uDF19'}
        </span>
      </div>

      {/* Sun altitude indicator */}
      {isDaylight && (
        <div className="mt-2 text-center">
          <span className="text-xs text-gray-500">
            Sun altitude: {Math.round(altitudePercent)}%
          </span>
        </div>
      )}
    </div>
  );
}
