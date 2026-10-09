import React from 'react';
import { Wind, Droplets, Thermometer, ChevronRight, HardHat, Flame } from 'lucide-react';
import { ZoneWithLatest } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatNumber } from '../utils/formatters';

interface ZoneCardProps {
  item: ZoneWithLatest;
  onSelect: (item: ZoneWithLatest) => void;
  isSelected?: boolean;
}

export const ZoneCard: React.FC<ZoneCardProps> = ({
  item,
  onSelect,
  isSelected = false
}) => {
  const { zone, latest_reading, latest_decision } = item;
  const pm25 = latest_reading?.pm25?.value;
  const pm10 = latest_reading?.pm10?.value;
  const ratio = latest_reading?.pm_ratio;
  const weather = latest_reading?.weather;
  const hasConstruction = zone.nearby_infrastructure?.has_construction_nearby;
  const hasSmoke = latest_reading?.fire_summary?.possible_smoke_transport;

  return (
    <div
      onClick={() => onSelect(item)}
      className={`group bg-white hover:bg-warm-50 rounded-2xl p-4 border cursor-pointer transition-all duration-200 hover:shadow-warm hover:-translate-y-0.5 ${
        isSelected
          ? 'border-accent-500 shadow-warm ring-1 ring-accent-500/30'
          : 'border-warm-200 hover:border-warm-400'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] text-earth-400 font-semibold px-1.5 py-0.5 rounded-md bg-warm-100 border border-warm-200">
              {zone.zone_id}
            </span>
            <span className="text-[11px] text-earth-400">{zone.zone_type}</span>
          </div>
          <h3 className="font-sentinel font-bold text-sm text-earth-900 mt-1 group-hover:text-accent-600 transition-colors">
            {zone.name}
          </h3>
        </div>

        <ChevronRight className="w-4 h-4 text-earth-300 group-hover:text-accent-500 group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-1" />
      </div>

      {/* Decision Status Badge */}
      <div className="my-2.5">
        <StatusBadge
          decision={latest_decision?.decision}
          priority={latest_decision?.priority}
          size="sm"
        />
      </div>

      {/* Pollutant metrics */}
      <div className="grid grid-cols-3 gap-2 bg-warm-100/60 p-2.5 rounded-xl border border-warm-200/60 my-2 text-center">
        <div>
          <span className="text-[10px] text-earth-400 uppercase tracking-wider block">PM10</span>
          <span className="font-mono font-bold text-xs text-earth-700 font-tabular">
            {formatNumber(pm10, 0)} <span className="text-[9px] text-earth-400 font-normal">µg/m³</span>
          </span>
        </div>
        <div>
          <span className="text-[10px] text-earth-400 uppercase tracking-wider block">PM2.5</span>
          <span className="font-mono font-bold text-xs text-earth-700 font-tabular">
            {formatNumber(pm25, 0)} <span className="text-[9px] text-earth-400 font-normal">µg/m³</span>
          </span>
        </div>
        <div>
          <span className="text-[10px] text-earth-400 uppercase tracking-wider block">Ratio</span>
          <span className={`font-mono font-bold text-xs font-tabular ${ratio && ratio >= 2.0 ? 'text-accent-600 font-semibold' : 'text-earth-600'}`}>
            {formatNumber(ratio, 2)}
          </span>
        </div>
      </div>

      {/* Environmental & Context Badges */}
      <div className="flex items-center justify-between text-[11px] text-earth-400 pt-1">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 font-tabular">
            <Thermometer className="w-3 h-3 text-earth-300" />
            <span>{formatNumber(weather?.temperature_c, 0)}°C</span>
          </span>
          <span className="flex items-center gap-1 font-tabular">
            <Droplets className="w-3 h-3 text-earth-300" />
            <span>{formatNumber(weather?.relative_humidity, 0)}%</span>
          </span>
          <span className="flex items-center gap-1 font-tabular">
            <Wind className="w-3 h-3 text-earth-300" />
            <span>{formatNumber(weather?.wind_speed_kmh, 1)} km/h</span>
          </span>
        </div>

        <div className="flex items-center gap-1">
          {hasConstruction && (
            <span title="Nearby construction site within 300m" className="text-yellow-600 p-0.5 rounded-md bg-yellow-100">
              <HardHat className="w-3 h-3" />
            </span>
          )}
          {hasSmoke && (
            <span title="Active thermal anomaly / smoke transport" className="text-accent-600 p-0.5 rounded-md bg-accent-500/10">
              <Flame className="w-3 h-3" />
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
