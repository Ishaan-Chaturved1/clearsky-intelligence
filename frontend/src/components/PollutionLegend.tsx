import React from 'react';
import { Info } from 'lucide-react';

interface PollutionLegendProps {
  className?: string;
  metricLabel?: string;
}

export const PollutionLegend: React.FC<PollutionLegendProps> = ({
  className = '',
  metricLabel = 'Pollution Contours',
}) => {
  return (
    <div
      className={`glass-panel py-2 px-3.5 inline-flex flex-col gap-1.5 shadow-lg select-none backdrop-blur-md bg-white/80 border border-white/70 rounded-2xl ${className}`}
    >
      <div className="flex items-center justify-between text-[11px] font-semibold text-slate-600 gap-4">
        <span className="text-emerald-700">Low</span>
        <span className="text-rose-600 font-bold">High</span>
      </div>

      {/* Gradient bar matching seamless heatmap progression */}
      <div
        className="w-28 sm:w-36 h-2 rounded-full shadow-inner"
        style={{
          background: 'linear-gradient(to right, #22c55e 0%, #84cc16 20%, #eab308 40%, #f59e0b 60%, #f97316 80%, #dc2626 100%)',
        }}
      />

      {/* Info indicator */}
      <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium pt-0.5">
        <Info className="w-3 h-3 text-slate-400" />
        <span>{metricLabel} (Modeled)</span>
      </div>
    </div>
  );
};

export default PollutionLegend;
