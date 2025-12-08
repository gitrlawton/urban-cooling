'use client';

export type ViewMode = 'heat' | 'shade' | 'combined';

interface ViewToggleProps {
  currentView: ViewMode;
  onChange: (view: ViewMode) => void;
  disabled?: boolean;
  shadeAvailable?: boolean;
}

interface ViewOption {
  id: ViewMode;
  label: string;
  icon: string;
  description: string;
}

const views: ViewOption[] = [
  {
    id: 'heat',
    label: 'Heat',
    icon: '\uD83D\uDD25',
    description: 'Surface temperature hotspots'
  },
  {
    id: 'shade',
    label: 'Shade',
    icon: '\uD83C\uDF33',
    description: 'Current shade coverage'
  },
  {
    id: 'combined',
    label: 'Combined',
    icon: '\uD83D\uDCCA',
    description: 'Heat + shade deficit priority'
  },
];

export default function ViewToggle({
  currentView,
  onChange,
  disabled = false,
  shadeAvailable = true
}: ViewToggleProps) {
  return (
    <div className={`bg-white p-2 rounded-lg shadow-lg ${disabled ? 'opacity-50' : ''}`}>
      <div className="flex gap-1">
        {views.map((view) => {
          const isActive = currentView === view.id;
          const isDisabled = disabled || (!shadeAvailable && view.id !== 'heat');

          return (
            <button
              key={view.id}
              onClick={() => !isDisabled && onChange(view.id)}
              disabled={isDisabled}
              title={view.description}
              className={`
                px-3 py-2 rounded text-sm font-medium transition-all duration-200
                flex items-center gap-1.5
                ${isActive
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }
                ${isDisabled && !isActive
                  ? 'opacity-50 cursor-not-allowed hover:bg-gray-100'
                  : 'cursor-pointer'
                }
              `}
            >
              <span className="text-base">{view.icon}</span>
              <span>{view.label}</span>
            </button>
          );
        })}
      </div>

      {/* Description of current view */}
      <div className="mt-2 px-1">
        <p className="text-xs text-gray-500">
          {views.find(v => v.id === currentView)?.description}
        </p>
      </div>

      {/* Shade unavailable message */}
      {!shadeAvailable && currentView === 'heat' && (
        <div className="mt-2 px-1">
          <p className="text-xs text-amber-600">
            Run combined analysis to enable shade views
          </p>
        </div>
      )}
    </div>
  );
}
