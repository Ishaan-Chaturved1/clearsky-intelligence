import React from 'react';
import {
  ResponsiveContainer,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Line,
  ComposedChart
} from 'recharts';
import { DailyTrendItem } from '../types';
import { formatInteger } from '../utils/formatters';

interface WaterAnalyticsChartProps {
  data: DailyTrendItem[];
  litersPerOp: number;
}

export const WaterAnalyticsChart: React.FC<WaterAnalyticsChartProps> = ({ data, litersPerOp }) => {
  return (
    <div className="w-full h-72 sm:h-80">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E8DDD0" vertical={false} />
          
          <XAxis
            dataKey="label"
            stroke="#A08B72"
            tick={{ fill: '#7A6651', fontSize: 11, fontFamily: 'Source Serif 4' }}
            tickLine={false}
          />
          
          <YAxis
            yAxisId="ops"
            stroke="#A08B72"
            tick={{ fill: '#7A6651', fontSize: 11, fontFamily: 'IBM Plex Mono' }}
            tickLine={false}
            label={{ value: 'Runs', angle: -90, position: 'insideLeft', fill: '#A08B72', fontSize: 10 }}
          />

          <YAxis
            yAxisId="water"
            orientation="right"
            stroke="#A08B72"
            tick={{ fill: '#3DA88E', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
            tickLine={false}
            tickFormatter={(val) => `${(val / 1000).toFixed(0)}kL`}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFDF7',
              borderColor: '#E8DDD0',
              borderRadius: '12px',
              color: '#3E3025',
              fontSize: '12px',
              fontFamily: 'Source Serif 4',
              boxShadow: '0 4px 14px rgba(157,122,78,0.10)'
            }}
            formatter={(value: any, name: string) => {
              if (name === 'Water Saved (Liters)') {
                return [`${formatInteger(Number(value))} Liters`, name];
              }
              return [`${value} operations`, name];
            }}
          />

          <Legend
            wrapperStyle={{ paddingTop: '10px', fontSize: '11px' }}
            iconType="circle"
          />

          {/* Baseline fixed schedule runs */}
          <Bar
            yAxisId="ops"
            dataKey="baseline_ops"
            name="Baseline Schedule Runs"
            fill="#D4C5B3"
            radius={[6, 6, 0, 0]}
          />

          {/* Actual recommended targeted runs */}
          <Bar
            yAxisId="ops"
            dataKey="recommended_ops"
            name="Recommended Dust Runs"
            fill="#F06B42"
            radius={[6, 6, 0, 0]}
          />

          {/* Water Saved Liters Line */}
          <Line
            yAxisId="water"
            type="monotone"
            dataKey="water_saved_liters"
            name="Water Saved (Liters)"
            stroke="#3DA88E"
            strokeWidth={2.5}
            dot={{ fill: '#3DA88E', r: 3 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
