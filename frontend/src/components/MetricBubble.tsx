import React, { useState } from 'react';
import { LucideIcon, Info, TrendingUp, Clock, CheckCircle } from 'lucide-react';

export interface MetricBubbleProps {
  icon: LucideIcon;
  iconColor?: string;
  iconBgColor?: string;
  value: string | number | null | undefined;
  unit: string;
  label: string;
  provenance?: string;
  timestamp?: string;
  trendText?: string;
  description?: string;
  className?: string;
  onClick?: () => void;
}

export const MetricBubble: React.FC<MetricBubbleProps> = ({
  icon: Icon,
  iconColor = 'text-emerald-600',
  iconBgColor = 'bg-emerald-50 border-emerald-100/60',
  value,
  unit,
  label,
  provenance = 'Model / Open-Meteo',
  timestamp,
  trendText,
  description,
  className = '',
  onClick,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const displayVal = value !== null && value !== undefined && value !== '' ? value : '—';

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      setShowModal(true);
    }
  };

  return (
    <>
      <div
        onClick={handleClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`glass-bubble w-24 h-24 min-[420px]:w-28 min-[420px]:h-28 sm:w-36 sm:h-36 lg:w-40 lg:h-40 flex flex-col items-center justify-center p-1.5 sm:p-3 relative cursor-pointer select-none group text-center pointer-events-auto transition-transform duration-200 hover:scale-105 ${className}`}
        role="button"
        tabIndex={0}
        aria-label={`${label}: ${displayVal} ${unit}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            handleClick();
          }
        }}
      >
        {/* Soft icon pill at top */}
        <div
          className={`w-6 h-6 sm:w-8 sm:h-8 rounded-full flex items-center justify-center mb-0.5 sm:mb-1 border shadow-xs transition-transform group-hover:scale-110 ${iconBgColor}`}
        >
          <Icon className={`w-3 h-3 sm:w-4 sm:h-4 ${iconColor}`} />
        </div>

        {/* Prominent numeric value & unit */}
        <div className="flex items-baseline justify-center gap-0.5 sm:gap-1 font-sans">
          <span className="text-lg min-[420px]:text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-slate-800 font-tabular">
            {displayVal}
          </span>
          <span className="text-[10px] min-[420px]:text-xs sm:text-sm font-semibold text-slate-500 lowercase">
            {unit}
          </span>
        </div>

        {/* Compact uppercase label */}
        <div className="text-[8px] min-[420px]:text-[9px] sm:text-[10px] lg:text-[11px] font-bold tracking-wider text-slate-400 uppercase mt-0.5 sm:mt-1">
          {label}
        </div>

        {/* Floating Hover Tooltip */}
        {showTooltip && (
          <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-slate-900/95 text-white text-[11px] font-medium py-1 px-2.5 rounded-lg shadow-xl backdrop-blur-md pointer-events-none whitespace-nowrap z-50 animate-fade-up border border-slate-700/50">
            <span>{label}: {displayVal} {unit}</span>
            {trendText && <span className="ml-1 text-emerald-400">({trendText})</span>}
          </div>
        )}
      </div>

      {/* Metric Detail Modal */}
      {showModal && (
        <div
          className="fixed inset-0 z-[1200] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-up"
          onClick={() => setShowModal(false)}
        >
          <div
            className="glass-panel max-w-sm w-full p-6 bg-white/95 text-slate-800 shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${iconBgColor}`}>
                  <Icon className={`w-4 h-4 ${iconColor}`} />
                </div>
                <div>
                  <h3 className="font-bold text-base text-slate-900">{label} Reading</h3>
                  <p className="text-xs text-slate-400">{provenance}</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="w-7 h-7 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-colors text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="my-5 p-4 rounded-2xl bg-gradient-to-br from-slate-50 to-emerald-50/30 border border-slate-100 text-center">
              <div className="text-3xl font-black text-slate-900 font-tabular">
                {displayVal} <span className="text-base font-semibold text-slate-500">{unit}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {description || `Current recorded value for ${label.toLowerCase()} in selected location.`}
              </p>
            </div>

            <div className="space-y-2 text-xs text-slate-600">
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                <span className="flex items-center gap-1.5 text-slate-500"><Clock className="w-3.5 h-3.5" /> Updated</span>
                <span className="font-medium text-slate-700">{timestamp || 'Just now'}</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                <span className="flex items-center gap-1.5 text-slate-500"><Info className="w-3.5 h-3.5" /> Source Provenance</span>
                <span className="font-medium text-slate-700">{provenance}</span>
              </div>
              {trendText && (
                <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50">
                  <span className="flex items-center gap-1.5 text-slate-500"><TrendingUp className="w-3.5 h-3.5" /> Trend</span>
                  <span className="font-medium text-emerald-600">{trendText}</span>
                </div>
              )}
            </div>

            <button
              onClick={() => setShowModal(false)}
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

export default MetricBubble;
