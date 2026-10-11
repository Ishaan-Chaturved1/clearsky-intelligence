import React from 'react';
import { Wind, Leaf, AlertCircle } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface AirFlowCardProps {
  windSpeedKmh?: number | null;
  windSpeedMs?: number | null;
  windDirectionDeg?: number | null;
  boundaryLayerHeight?: number | null;
  className?: string;
  isElevated?: boolean;
  peekMode?: boolean;
  onClick?: () => void;
}

export const AirFlowCard: React.FC<AirFlowCardProps> = ({
  windSpeedKmh = null,
  windSpeedMs = null,
  windDirectionDeg = null,
  boundaryLayerHeight = null,
  className = '',
  isElevated = false,
  peekMode = true,
  onClick,
}) => {
  const hasData = windSpeedKmh !== null && windSpeedKmh !== undefined;
  const speedKmhDisplay = hasData ? windSpeedKmh.toFixed(1) : '--';
  const speedMsDisplay =
    windSpeedMs !== null && windSpeedMs !== undefined
      ? windSpeedMs.toFixed(1)
      : hasData
      ? (windSpeedKmh! / 3.6).toFixed(1)
      : '--';

  const deg = windDirectionDeg !== null && windDirectionDeg !== undefined ? windDirectionDeg : 0;

  // Derive atmospheric status based on speed & boundary layer
  const isFavorable = hasData && Number(speedKmhDisplay) >= 5 && (boundaryLayerHeight ?? 400) >= 300;
  const statusTitle = !hasData ? 'Awaiting Wind Telemetry' : isFavorable ? 'Fresh Air Movement!' : 'Stagnant Boundary Layer!';
  const statusSubtitle = !hasData
    ? 'Surface meteorological feed standby.'
    : isFavorable
    ? 'Wind circulation is helping reduce pollutant.'
    : 'Low wind speed is trapping surface pollutants.';

  return (
    <GlassCard depthLevel={2} isElevated={isElevated} peekMode={peekMode} onClick={onClick} className={`flex flex-col justify-between ${className}`}>
      {/* Title & Preview Badge */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm sm:text-base text-slate-800 tracking-tight">
            Air Flow Status
          </h3>
          <span className="hidden sm:inline-flex text-[10px] font-semibold text-slate-700 bg-slate-100 border border-slate-200/80 px-2 py-0.5 rounded-full items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            {speedKmhDisplay} km/h
          </span>
        </div>
      </div>

      {/* Main Content: Wind Speed & Circular Compass */}
      <div className="flex items-center justify-between gap-4 my-auto py-1">
        {/* Left: Speed in km/h */}
        <div className="flex flex-col">
          <span className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight font-tabular">
            {speedKmhDisplay}
          </span>
          <span className="text-xs font-semibold text-slate-500 lowercase mt-0.5">
            km/hours
          </span>
        </div>

        {/* Right: Circular Compass / Wind Rose */}
        <div className="relative w-28 h-28 sm:w-32 sm:h-32 flex items-center justify-center select-none">
          {/* Compass Outer Ring with Degree Markers */}
          <div className="absolute inset-0 rounded-full border border-slate-200/80 bg-gradient-to-br from-white/90 to-slate-50/80 shadow-inner flex items-center justify-center">
            {/* Degree ticks circle */}
            <svg viewBox="0 0 100 100" className="w-full h-full p-1 opacity-40">
              <circle cx="50" cy="50" r="44" stroke="#94a3b8" strokeWidth="1" fill="none" strokeDasharray="1.5 6.5" />
            </svg>

            {/* Cardinal Direction Indicators */}
            {/* North */}
            <div className="absolute top-1.5 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-emerald-600 text-white text-[9px] font-bold flex items-center justify-center shadow-xs">
              N
            </div>
            {/* South */}
            <div className="absolute bottom-1.5 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[9px] font-bold flex items-center justify-center shadow-xs">
              S
            </div>
            {/* West */}
            <div className="absolute left-1.5 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[9px] font-bold flex items-center justify-center shadow-xs">
              W
            </div>
            {/* East */}
            <div className="absolute right-1.5 top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-slate-200 text-slate-700 text-[9px] font-bold flex items-center justify-center shadow-xs">
              E
            </div>

            {/* Rotating Wind Needle pointing along windDirectionDeg */}
            <div
              className="absolute inset-0 flex items-center justify-center pointer-events-none transition-transform duration-700 ease-out"
              style={{ transform: `rotate(${deg}deg)` }}
            >
              <div className="w-1.5 h-10 rounded-full bg-gradient-to-t from-transparent via-emerald-500/60 to-emerald-600 shadow-xs -translate-y-2 relative">
                {/* Pointer tip */}
                <div className="w-3 h-3 bg-emerald-500 rotate-45 rounded-xs absolute -top-1 left-1/2 -translate-x-1/2" />
              </div>
            </div>

            {/* Center Hub displaying speed in m/s */}
            <div className="relative z-10 w-14 h-14 rounded-full bg-white/95 border border-slate-200/90 shadow-md flex flex-col items-center justify-center backdrop-blur-md">
              <Wind className="w-3 h-3 text-emerald-600 mb-0.5" />
              <div className="text-[11px] font-extrabold text-slate-800 leading-none font-tabular">
                {speedMsDisplay}
              </div>
              <div className="text-[8px] font-bold text-slate-400">m/s</div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Contextual Status Strip */}
      <div
        className={`flex items-center gap-2.5 p-2 sm:p-2.5 rounded-2xl border transition-all ${
          isFavorable
            ? 'bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-teal-500/10 border-emerald-500/20 text-emerald-950'
            : 'bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-orange-500/10 border-amber-500/20 text-amber-950'
        }`}
      >
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
            isFavorable ? 'bg-emerald-500/20 text-emerald-700' : 'bg-amber-500/20 text-amber-700'
          }`}
        >
          {isFavorable ? <Leaf className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
        </div>
        <div className="overflow-hidden">
          <div className="text-[11px] font-bold truncate leading-tight">{statusTitle}</div>
          <div className="text-[10px] text-slate-500 truncate leading-tight mt-0.5">
            {statusSubtitle}
          </div>
        </div>
      </div>
    </GlassCard>
  );
};

export default AirFlowCard;
