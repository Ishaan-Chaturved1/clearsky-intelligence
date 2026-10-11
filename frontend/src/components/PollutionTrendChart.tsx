import React, { useState } from 'react';
import {
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { GlassCard } from './GlassCard';

type TimeRange = 'REAL TIME' | 'WEEKLY' | 'MONTHLY' | 'YEARLY';

interface PollutionTrendChartProps {
  currentAqi?: number;
  currentSeverity?: string;
  className?: string;
  isElevated?: boolean;
  peekMode?: boolean;
  onClick?: () => void;
}

export const PollutionTrendChart: React.FC<PollutionTrendChartProps> = ({
  currentAqi = 42,
  currentSeverity = 'Moderate Pollution',
  className = '',
  isElevated = false,
  peekMode = true,
  onClick,
}) => {
  const [activeRange, setActiveRange] = useState<TimeRange>('REAL TIME');

  // Time series datasets tailored to range
  const realTimeData = [
    { time: '06.00', value: 28, forecast: null, isCurrent: false },
    { time: '08.00', value: 46, forecast: null, isCurrent: false },
    { time: '10.00', value: 34, forecast: null, isCurrent: false },
    { time: '12.00', value: 44, forecast: null, isCurrent: false },
    { time: '14.00', value: currentAqi, forecast: currentAqi, isCurrent: true },
    { time: '16.00', value: null, forecast: 48, isCurrent: false },
    { time: '18.00', value: null, forecast: 38, isCurrent: false },
    { time: '20.00', value: null, forecast: 45, isCurrent: false },
  ];

  const weeklyData = [
    { time: 'Mon', value: 32, forecast: null, isCurrent: false },
    { time: 'Tue', value: 38, forecast: null, isCurrent: false },
    { time: 'Wed', value: 45, forecast: null, isCurrent: false },
    { time: 'Thu', value: 42, forecast: null, isCurrent: false },
    { time: 'Today', value: currentAqi, forecast: currentAqi, isCurrent: true },
    { time: 'Sat', value: null, forecast: 39, isCurrent: false },
    { time: 'Sun', value: null, forecast: 35, isCurrent: false },
  ];

  const monthlyData = [
    { time: 'W1', value: 36, forecast: null, isCurrent: false },
    { time: 'W2', value: 44, forecast: null, isCurrent: false },
    { time: 'W3', value: currentAqi, forecast: currentAqi, isCurrent: true },
    { time: 'W4', value: null, forecast: 41, isCurrent: false },
  ];

  const yearlyData = [
    { time: 'Q1', value: 48, forecast: null, isCurrent: false },
    { time: 'Q2', value: 39, forecast: null, isCurrent: false },
    { time: 'Q3', value: currentAqi, forecast: currentAqi, isCurrent: true },
    { time: 'Q4', value: null, forecast: 36, isCurrent: false },
  ];

  const chartData =
    activeRange === 'REAL TIME'
      ? realTimeData
      : activeRange === 'WEEKLY'
      ? weeklyData
      : activeRange === 'MONTHLY'
      ? monthlyData
      : yearlyData;

  const currentTimeLabel = activeRange === 'REAL TIME' ? '14.00' : activeRange === 'WEEKLY' ? 'Today' : activeRange === 'MONTHLY' ? 'W3' : 'Q3';

  // Custom Floating Tooltip matching the screenshot
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      const val = dataPoint.value ?? dataPoint.forecast;
      const isFc = dataPoint.value === null;

      return (
        <div className="bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-200/80 shadow-xl text-left pointer-events-none animate-fade-up">
          <div className="text-[10px] text-slate-400 font-semibold flex items-center justify-between gap-3 mb-1">
            <span>{new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            <span>{label}</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-sm ${
                val > 60 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
            />
            <span className="text-xs font-semibold text-slate-800">
              {currentSeverity}
            </span>
            <span className="text-xs font-bold text-slate-900 bg-slate-100 px-1.5 py-0.5 rounded font-tabular">
              AQI {val} {isFc ? '(fc)' : ''}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <GlassCard depthLevel={1} isElevated={isElevated} peekMode={peekMode} onClick={onClick} className={`flex flex-col justify-between ${className}`}>
      {/* Header with Title, Preview Badge and Range Switcher */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-bold text-sm sm:text-base text-slate-800 tracking-tight">
            Pollution Trend Analysis
          </h3>
          <span className="hidden sm:inline-flex text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-2 py-0.5 rounded-full items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            AQI {currentAqi}
          </span>
        </div>

        {/* Range Selector Pills */}
        <div className="flex items-center gap-1 bg-slate-100/80 p-0.5 rounded-full border border-slate-200/60 text-[10px] sm:text-[11px]">
          {(['REAL TIME', 'WEEKLY', 'MONTHLY', 'YEARLY'] as TimeRange[]).map((range) => (
            <button
              key={range}
              onClick={(e) => {
                e.stopPropagation();
                setActiveRange(range);
              }}
              className={`px-2 sm:px-2.5 py-1 rounded-full font-semibold transition-all ${
                activeRange === range
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Trend Chart */}
      <div className="w-full h-36 sm:h-44 relative">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 12, right: 10, left: -26, bottom: 0 }}>
            <defs>
              <linearGradient id="trendGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#22c55e" stopOpacity={0.25} />
                <stop offset="60%" stopColor="#eab308" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#f97316" stopOpacity={0.08} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="time"
              axisLine={false}
              tickLine={false}
              tick={({ x, y, payload }) => {
                const isSelected = payload.value === currentTimeLabel;
                return (
                  <text
                    x={x}
                    y={y + 12}
                    textAnchor="middle"
                    fill={isSelected ? '#0f172a' : '#94a3b8'}
                    fontSize={10}
                    fontWeight={isSelected ? 700 : 500}
                  >
                    {payload.value}
                  </text>
                );
              }}
            />
            <YAxis hide domain={[10, 80]} />
            <Tooltip content={<CustomTooltip />} />

            {/* Vertical Yellow Reference Line at Current Time */}
            <ReferenceLine
              x={currentTimeLabel}
              stroke="#eab308"
              strokeWidth={2}
              strokeDasharray=""
            />

            {/* Historical Recorded Area (smooth curve) */}
            <Area
              type="monotone"
              dataKey="value"
              stroke="#22c55e"
              strokeWidth={2.5}
              fill="url(#trendGradient)"
              activeDot={{ r: 5, fill: '#eab308', stroke: '#ffffff', strokeWidth: 2 }}
            />

            {/* Forecast dashed line continuing from current */}
            <Line
              type="monotone"
              dataKey="forecast"
              stroke="#f97316"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 3, fill: '#f97316' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
};

export default PollutionTrendChart;
