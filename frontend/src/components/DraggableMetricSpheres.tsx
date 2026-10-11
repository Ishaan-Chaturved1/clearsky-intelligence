import React, { useState, useEffect, useRef, useCallback } from 'react';
import { CloudRain, Droplets, Thermometer, Sparkles, RotateCcw, Clock, Info, TrendingUp } from 'lucide-react';
import { MetricBubble } from './MetricBubble';

export interface DraggableMetricSpheresProps {
  rainfallMm?: number | null;
  humidityPercent?: number | null;
  temperatureC?: number | null;
  aqiOrPm25?: number | string | null;
  containerRef: React.RefObject<HTMLDivElement>;
  onResetLayoutCallback?: () => void;
}

interface SphereCoords {
  xPercent: number; // 0% to 100% of container width
  yPercent: number; // 0% to 100% of container height
}

type SphereId = 'rainfall' | 'humidity' | 'temperature' | 'aqi';

// Default resting positions (calibrated for open map area above bottom cards)
const DEFAULT_POSITIONS: Record<SphereId, SphereCoords> = {
  rainfall: { xPercent: 3.5, yPercent: 4 },
  humidity: { xPercent: 54, yPercent: 4 },
  temperature: { xPercent: 3.5, yPercent: 35 },
  aqi: { xPercent: 70, yPercent: 35 },
};

const STORAGE_KEY = 'clearsky_metric_spheres_v2';

export const DraggableMetricSpheres: React.FC<DraggableMetricSpheresProps> = ({
  rainfallMm = 0,
  humidityPercent = 84,
  temperatureC = 23,
  aqiOrPm25 = 5,
  containerRef,
}) => {
  // Load saved positions or use defaults
  const [positions, setPositions] = useState<Record<SphereId, SphereCoords>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (
          parsed.rainfall?.xPercent !== undefined &&
          parsed.humidity?.xPercent !== undefined &&
          parsed.temperature?.xPercent !== undefined &&
          parsed.aqi?.xPercent !== undefined
        ) {
          return parsed;
        }
      }
    } catch {
      // Fallback to defaults
    }
    return DEFAULT_POSITIONS;
  });

  const [activeDragging, setActiveDragging] = useState<SphereId | null>(null);
  const [isCustomized, setIsCustomized] = useState<boolean>(() => {
    return Boolean(localStorage.getItem(STORAGE_KEY));
  });
  const [selectedModalSphere, setSelectedModalSphere] = useState<any | null>(null);

  const preventClickRef = useRef(false);

  // Track drag start and moved distance
  const dragInfoRef = useRef<{
    sphereId: SphereId | null;
    pointerId: number | null;
    startX: number;
    startY: number;
    initialPxX: number;
    initialPxY: number;
    hasMoved: boolean;
  }>({
    sphereId: null,
    pointerId: null,
    startX: 0,
    startY: 0,
    initialPxX: 0,
    initialPxY: 0,
    hasMoved: false,
  });

  const positionsRef = useRef(positions);
  positionsRef.current = positions;

  // Persist positions to localStorage
  const savePositions = useCallback((newPos: Record<SphereId, SphereCoords>) => {
    setPositions(newPos);
    setIsCustomized(true);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newPos));
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Reset positions back to defaults
  const handleResetLayout = useCallback(() => {
    setPositions(DEFAULT_POSITIONS);
    setIsCustomized(false);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Listen for global reset events (e.g. from MapControls)
  useEffect(() => {
    const handleCustomReset = () => {
      handleResetLayout();
    };
    window.addEventListener('clearsky-reset-spheres', handleCustomReset);
    return () => {
      window.removeEventListener('clearsky-reset-spheres', handleCustomReset);
    };
  }, [handleResetLayout]);

  // Pointer Down: Initiate drag on sphere
  const handlePointerDown = (id: SphereId, e: React.PointerEvent<HTMLDivElement>) => {
    // Prevent Leaflet map from starting panning
    e.stopPropagation();

    const container = containerRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const currentCoords = positionsRef.current[id];
    const initialPxX = (currentCoords.xPercent / 100) * containerRect.width;
    const initialPxY = (currentCoords.yPercent / 100) * containerRect.height;

    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {
      // Ignore if setPointerCapture fails on some test environments
    }

    dragInfoRef.current = {
      sphereId: id,
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      initialPxX,
      initialPxY,
      hasMoved: false,
    };

    setActiveDragging(id);
  };

  // Pointer Move: Dragging sphere within container bounds
  const handlePointerMove = (id: SphereId, e: React.PointerEvent<HTMLDivElement>) => {
    if (dragInfoRef.current.sphereId !== id) return;

    const deltaX = e.clientX - dragInfoRef.current.startX;
    const deltaY = e.clientY - dragInfoRef.current.startY;

    if (Math.hypot(deltaX, deltaY) > 5) {
      dragInfoRef.current.hasMoved = true;
      preventClickRef.current = true;
    }

    const container = containerRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const sphereEl = e.currentTarget;
    const sphereWidth = sphereEl.offsetWidth || 112;
    const sphereHeight = sphereEl.offsetHeight || 112;

    const rawPxX = dragInfoRef.current.initialPxX + deltaX;
    const rawPxY = dragInfoRef.current.initialPxY + deltaY;

    // Strict boundary clamping so spheres remain completely visible in the open upper map area
    const maxAllowedY = containerRect.height > 550 ? containerRect.height - 240 - sphereHeight : containerRect.height - sphereHeight - 6;
    const clampedPxX = Math.max(6, Math.min(rawPxX, containerRect.width - sphereWidth - 6));
    const clampedPxY = Math.max(6, Math.min(rawPxY, Math.max(60, maxAllowedY)));

    const xPercent = (clampedPxX / containerRect.width) * 100;
    const yPercent = (clampedPxY / containerRect.height) * 100;

    setPositions((prev) => ({
      ...prev,
      [id]: { xPercent, yPercent },
    }));
  };

  // Pointer Up: Release sphere and save
  const handlePointerUp = (id: SphereId, e: React.PointerEvent<HTMLDivElement>) => {
    if (dragInfoRef.current.sphereId !== id) return;

    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {
      // Ignore
    }

    if (dragInfoRef.current.hasMoved) {
      savePositions(positionsRef.current);
      setTimeout(() => {
        preventClickRef.current = false;
      }, 250);
    }

    dragInfoRef.current.sphereId = null;
    dragInfoRef.current.pointerId = null;
    setActiveDragging(null);
  };

  const handlePointerCancel = (id: SphereId, e: React.PointerEvent<HTMLDivElement>) => {
    handlePointerUp(id, e);
  };

  // Metric configuration
  const spheresConfig: Array<{
    id: SphereId;
    icon: any;
    iconColor: string;
    iconBgColor: string;
    value: number | string;
    unit: string;
    label: string;
    description: string;
    trendText: string;
    floatClass: string;
  }> = [
    {
      id: 'rainfall',
      icon: CloudRain,
      iconColor: 'text-emerald-500',
      iconBgColor: 'bg-emerald-50 border-emerald-100/70',
      value: rainfallMm !== null && rainfallMm !== undefined ? rainfallMm : 0,
      unit: 'mm',
      label: 'RAINFALL',
      description: 'Real-time precipitation estimate from meteorological feed.',
      trendText: 'Stable',
      floatClass: 'animate-float-1',
    },
    {
      id: 'humidity',
      icon: Droplets,
      iconColor: 'text-sky-500',
      iconBgColor: 'bg-sky-50 border-sky-100/70',
      value: humidityPercent !== null && humidityPercent !== undefined ? humidityPercent : 84,
      unit: '%',
      label: 'HUMIDITY',
      description: 'Relative atmospheric humidity measured in the active locality.',
      trendText: 'Elevated',
      floatClass: 'animate-float-2',
    },
    {
      id: 'temperature',
      icon: Thermometer,
      iconColor: 'text-amber-500',
      iconBgColor: 'bg-amber-50 border-amber-100/70',
      value: temperatureC !== null && temperatureC !== undefined ? Math.round(temperatureC) : 23,
      unit: '°c',
      label: 'TEMPERATURE',
      description: 'Ambient surface temperature recorded at nearby station.',
      trendText: 'Optimal',
      floatClass: 'animate-float-3',
    },
    {
      id: 'aqi',
      icon: Sparkles,
      iconColor: 'text-emerald-600',
      iconBgColor: 'bg-emerald-50 border-emerald-100/70',
      value: aqiOrPm25 !== null && aqiOrPm25 !== undefined ? aqiOrPm25 : 5,
      unit: 'idx',
      label: 'PM2.5/AIR',
      description: 'Composite particulate matter severity index for airborne dust.',
      trendText: 'Monitored',
      floatClass: 'animate-float-4',
    },
  ];

  // Keyboard accessibility: Nudge sphere position using Arrow keys, or Open Modal with Enter
  const handleKeyDown = (id: SphereId, e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelectedModalSphere(spheresConfig.find((s) => s.id === id) || null);
      return;
    }

    const step = e.shiftKey ? 5 : 2;
    let dx = 0;
    let dy = 0;

    if (e.key === 'ArrowLeft') dx = -step;
    else if (e.key === 'ArrowRight') dx = step;
    else if (e.key === 'ArrowUp') dy = -step;
    else if (e.key === 'ArrowDown') dy = step;
    else return;

    e.preventDefault();
    e.stopPropagation();

    const current = positionsRef.current[id];
    const newX = Math.max(2, Math.min(current.xPercent + dx, 82));
    const newY = Math.max(2, Math.min(current.yPercent + dy, 80));

    const updated = {
      ...positionsRef.current,
      [id]: { xPercent: newX, yPercent: newY },
    };

    savePositions(updated);
  };

  return (
    <>
      {/* 1. Draggable Metric Spheres */}
      {spheresConfig.map((sphere, index) => {
        const pos = positions[sphere.id];
        const isDraggingThis = activeDragging === sphere.id;

        return (
          <div
            key={sphere.id}
            role="button"
            tabIndex={0}
            aria-label={`${sphere.label}: ${sphere.value} ${sphere.unit}. Draggable metric sphere. Position at ${Math.round(pos.xPercent)}% horizontal, ${Math.round(pos.yPercent)}% vertical. Use arrow keys to reposition.`}
            onPointerDown={(e) => handlePointerDown(sphere.id, e)}
            onPointerMove={(e) => handlePointerMove(sphere.id, e)}
            onPointerUp={(e) => handlePointerUp(sphere.id, e)}
            onPointerCancel={(e) => handlePointerCancel(sphere.id, e)}
            onKeyDown={(e) => handleKeyDown(sphere.id, e)}
            style={{
              position: 'absolute',
              left: `${pos.xPercent}%`,
              top: `${pos.yPercent}%`,
              touchAction: 'none',
              zIndex: isDraggingThis ? 1100 : 900 + index,
            }}
            className={`pointer-events-auto select-none cursor-grab active:cursor-grabbing transition-transform duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 rounded-full ${
              isDraggingThis
                ? 'sphere-dragging'
                : `${sphere.floatClass} animate-bubble`
            }`}
          >
            <MetricBubble
              icon={sphere.icon}
              iconColor={sphere.iconColor}
              iconBgColor={sphere.iconBgColor}
              value={sphere.value}
              unit={sphere.unit}
              label={sphere.label}
              description={sphere.description}
              trendText={sphere.trendText}
              className={isDraggingThis ? 'pointer-events-none' : ''}
              onClick={() => {
                if (!preventClickRef.current) {
                  setSelectedModalSphere(sphere);
                }
              }}
            />
          </div>
        );
      })}

      {/* 2. Accessible "Reset Layout" button (visible when customized) */}
      {isCustomized && (
        <div className="absolute left-3 sm:left-6 top-3 sm:top-5 z-[990] pointer-events-auto animate-fade-up">
          <button
            type="button"
            onClick={handleResetLayout}
            title="Reset spheres to default positions"
            aria-label="Reset Spheres Layout"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold text-slate-700 bg-white/92 hover:bg-white border border-white/80 shadow-md backdrop-blur-md transition-all active:scale-95 group focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-500 group-hover:rotate-[-45deg] transition-transform text-emerald-600" />
            <span className="hidden min-[480px]:inline">Reset Layout</span>
          </button>
        </div>
      )}

      {/* 3. Metric Detail Modal when clicked */}
      {selectedModalSphere && (
        <div
          className="fixed inset-0 z-[1250] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up pointer-events-auto"
          onClick={() => setSelectedModalSphere(null)}
        >
          <div
            className="glass-panel max-w-sm w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative rounded-3xl border border-white/90"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${selectedModalSphere.iconBgColor}`}
                >
                  <selectedModalSphere.icon className={`w-4 h-4 ${selectedModalSphere.iconColor}`} />
                </div>
                <div>
                  <h3 className="font-bold text-base text-slate-900">
                    {selectedModalSphere.label} Reading
                  </h3>
                  <p className="text-xs text-slate-400">Model / Open-Meteo</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedModalSphere(null)}
                className="w-7 h-7 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="my-5 p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-emerald-50/30 border border-slate-100 text-center">
              <div className="text-3xl font-black text-slate-900 font-tabular">
                {selectedModalSphere.value}{' '}
                <span className="text-base font-semibold text-slate-500">
                  {selectedModalSphere.unit}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {selectedModalSphere.description}
              </p>
            </div>

            <div className="space-y-2 text-xs text-slate-600">
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                <span className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="w-3.5 h-3.5" /> Updated
                </span>
                <span className="font-medium text-slate-700">Just now</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                <span className="flex items-center gap-1.5 text-slate-500">
                  <Info className="w-3.5 h-3.5" /> Source Provenance
                </span>
                <span className="font-medium text-slate-700">Telemetry Feed</span>
              </div>
              {selectedModalSphere.trendText && (
                <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                  <span className="flex items-center gap-1.5 text-slate-500">
                    <TrendingUp className="w-3.5 h-3.5" /> Trend
                  </span>
                  <span className="font-medium text-emerald-600">
                    {selectedModalSphere.trendText}
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => setSelectedModalSphere(null)}
              className="mt-5 w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs shadow-md transition-all"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default DraggableMetricSpheres;
