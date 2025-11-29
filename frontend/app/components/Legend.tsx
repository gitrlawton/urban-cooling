'use client';

export default function Legend() {
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
