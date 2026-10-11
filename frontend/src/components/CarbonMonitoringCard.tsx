import React from 'react';
import {
  LineChart,
  Line,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Leaf } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface CarbonMonitoringCardProps {
  netCarbonOffset?: string;
  waterSavedLiters?: number | null;
  className?: string;
  isElevated?: boolean;
  peekMode?: boolean;
  onClick?: () => void;
}

export const CarbonMonitoringCard: React.FC<CarbonMonitoringCardProps> = ({
  netCarbonOffset = 'Baseline (Telemetry Pending)',
  waterSavedLiters,
  className = '',
  isElevated = false,
  peekMode = true,
  onClick,
}) => {
  // If waterSavedLiters is provided, format a calculated CO2 offset estimate (approx 0.0003 kg CO2e / liter pumping savings)
  const displayOffset =
    waterSavedLiters !== undefined && waterSavedLiters !== null
      ? `${(waterSavedLiters * 0.00028).toLocaleString('en-US', { maximumFractionDigits: 0 })} kg CO2e`
      : netCarbonOffset;

  // Comparative dual-series wave dataset matching the screenshot
  const comparisonData = [
    { name: 'P1', current: 140000, baseline: 120000 },
    { name: 'P2', current: 125000, baseline: 145000 },
    { name: 'P3', current: 160000, baseline: 110000 },
    { name: 'P4', current: 180000, baseline: 80000 },
    { name: 'P5', current: 170000, baseline: 130000 },
    { name: 'P6', current: 195000, baseline: 105000 },
    { name: 'P7', current: 185000, baseline: 110000 },
  ];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900/95 text-white text-[11px] p-2 rounded-xl shadow-xl backdrop-blur-md border border-slate-700/60 pointer-events-none">
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold mb-0.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            <span>Current: {(payload[0]?.value / 1000).toFixed(0)}k</span>
          </div>
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
            <span>Baseline: {(payload[1]?.value / 1000).toFixed(0)}k</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard depthLevel={3} isElevated={isElevated} peekMode={peekMode} onClick={onClick} className={`flex flex-col justify-between ${className}`}>
      {/* Header with Title, Preview Badge and Legend */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm sm:text-base text-slate-800 tracking-tight">
            Carbon Monitoring
          </h3>
          <span className="hidden sm:inline-flex text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Offset
          </span>
        </div>

        {/* Legend dots */}
        <div className="flex items-center gap-3 text-[11px] font-semibold">
          <div className="flex items-center gap-1.5 text-slate-600">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
            <span>Current</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
            <span>Baseline</span>
          </div>
        </div>
      </div>

      {/* Comparative Wave Line Chart with Axis Ticks */}
      <div className="w-full h-24 sm:h-28 relative my-auto">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={comparisonData} margin={{ top: 8, right: 8, left: -26, bottom: 4 }}>
            <YAxis
              domain={[0, 220000]}
              ticks={[0, 100000, 200000]}
              tickFormatter={(v) => (v === 0 ? '0' : `${v / 1000}k`)}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 9, fill: '#94a3b8', fontWeight: 600 }}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* Green Current Series */}
            <Line
              type="monotone"
              dataKey="current"
              stroke="#22c55e"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4, fill: '#22c55e', stroke: '#fff', strokeWidth: 2 }}
            />
            {/* Yellow Baseline Series */}
            <Line
              type="monotone"
              dataKey="baseline"
              stroke="#eab308"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4, fill: '#eab308', stroke: '#fff', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Light Carbon Summary Tile matching background */}
      <div className="bg-slate-50/90 rounded-2xl p-3 sm:p-3.5 flex items-center gap-3.5 shadow-xs border border-slate-200/80 select-none">
        {/* Glowing Leaf Icon Badge */}
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shrink-0 shadow-md shadow-emerald-600/20">
          <Leaf className="w-5 h-5 text-white" />
        </div>

        {/* Text */}
        <div className="flex flex-col overflow-hidden">
          <span className="text-[11px] font-semibold text-slate-500 tracking-wide">
            Net Carbon Offset
          </span>
          <span className="text-sm sm:text-base font-extrabold text-emerald-700 tracking-tight truncate font-tabular">
            {displayOffset}
          </span>
        </div>
      </div>
    </GlassCard>
  );
};

export default CarbonMonitoringCard;
