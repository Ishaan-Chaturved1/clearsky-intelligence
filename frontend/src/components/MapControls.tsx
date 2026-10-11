import React from 'react';
import { Layers, Crosshair, Plus, Minus, RotateCcw } from 'lucide-react';

interface MapControlsProps {
  onToggleContours?: () => void;
  showContours?: boolean;
  onToggleStations?: () => void;
  showStations?: boolean;
  onRecenter?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetLayout?: () => void;
  className?: string;
}

export const MapControls: React.FC<MapControlsProps> = ({
  onToggleContours,
  showContours = true,
  onRecenter,
  onZoomIn,
  onZoomOut,
  onResetLayout,
  className = '',
}) => {
  return (
    <div className={`flex flex-col gap-2 pointer-events-auto select-none ${className}`}>
      {/* Layer switcher */}
      {onToggleContours && (
        <button
          onClick={onToggleContours}
          type="button"
          title="Toggle Heat Contours"
          className={`w-9 h-9 sm:w-10 sm:h-10 rounded-2xl flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-90 backdrop-blur-md shadow-md border ${
            showContours
              ? 'bg-slate-900 text-white border-slate-800'
              : 'bg-white/90 text-slate-600 hover:text-slate-900 border-white/80'
          }`}
        >
          <Layers className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
        </button>
      )}

      {/* Recenter */}
      {onRecenter && (
        <button
          onClick={onRecenter}
          type="button"
          title="Recenter Map"
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-white/90 hover:bg-white text-slate-600 hover:text-slate-900 flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-90 backdrop-blur-md shadow-md border border-white/80"
        >
          <Crosshair className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
        </button>
      )}

      {/* Reset Metric Spheres Layout */}
      {onResetLayout && (
        <button
          onClick={onResetLayout}
          type="button"
          title="Reset Spheres Layout"
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-white/90 hover:bg-white text-slate-600 hover:text-slate-900 flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-90 backdrop-blur-md shadow-md border border-white/80"
        >
          <RotateCcw className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
        </button>
      )}

      {/* Zoom in */}
      {onZoomIn && (
        <button
          onClick={onZoomIn}
          type="button"
          title="Zoom In"
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-white/90 hover:bg-white text-slate-600 hover:text-slate-900 flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-90 backdrop-blur-md shadow-md border border-white/80 font-bold"
        >
          <Plus className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
        </button>
      )}

      {/* Zoom out */}
      {onZoomOut && (
        <button
          onClick={onZoomOut}
          type="button"
          title="Zoom Out"
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-white/90 hover:bg-white text-slate-600 hover:text-slate-900 flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-90 backdrop-blur-md shadow-md border border-white/80 font-bold"
        >
          <Minus className="w-4 h-4 sm:w-4.5 sm:h-4.5" />
        </button>
      )}
    </div>
  );
};

export default MapControls;
