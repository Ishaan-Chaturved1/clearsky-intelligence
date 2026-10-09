import React from 'react';
import {
  X,
  Compass,
  Thermometer,
  Droplets,
  Wind,
  Layers,
  HardHat,
  Flame,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';
import { ZoneWithLatest } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatNumber, formatCoordinates, formatDateTime, getConfidenceBadgeInfo } from '../utils/formatters';

interface ZoneDetailDrawerProps {
  item: ZoneWithLatest | null;
  onClose: () => void;
}

export const ZoneDetailDrawer: React.FC<ZoneDetailDrawerProps> = ({ item, onClose }) => {
  if (!item) return null;

  const { zone, latest_reading, latest_decision } = item;
  const pm25 = latest_reading?.pm25;
  const pm10 = latest_reading?.pm10;
  const ratio = latest_reading?.pm_ratio;
  const weather = latest_reading?.weather;
  const fire = latest_reading?.fire_summary;
  const infra = zone.nearby_infrastructure;
  const confidenceInfo = getConfidenceBadgeInfo(latest_decision?.confidence);

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-warm-50 border-l border-warm-200 shadow-warm-xl flex flex-col overflow-hidden">
      
      {/* Header */}
      <div className="p-5 border-b border-warm-200 bg-white flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded-lg bg-warm-100 border border-warm-200 text-accent-500">
              {zone.zone_id}
            </span>
            <span className="text-xs text-earth-400">{zone.zone_type}</span>
          </div>
          <h2 className="font-sentinel font-bold text-lg text-earth-900">
            {zone.name}
          </h2>
          <p className="font-mono text-[11px] text-earth-400 flex items-center gap-1 mt-0.5">
            <Compass className="w-3 h-3 text-earth-300" />
            <span>{formatCoordinates(zone.latitude, zone.longitude)}</span>
          </p>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-xl text-earth-400 hover:text-earth-700 hover:bg-warm-100 border border-transparent hover:border-warm-200 transition-colors"
          title="Close detail panel"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        
        {/* Current Recommendation Banner */}
        <div className="bg-white rounded-2xl p-4 border border-warm-200 shadow-warm-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-sans font-semibold text-earth-400 uppercase tracking-wider">
              Recommendation
            </span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border bg-warm-100 border-warm-200 text-earth-600`}>
              {confidenceInfo.label}
            </span>
          </div>

          <StatusBadge
            decision={latest_decision?.decision}
            priority={latest_decision?.priority}
            size="md"
          />

          {/* Decision Rationale */}
          {latest_decision?.reasons && latest_decision.reasons.length > 0 && (
            <div className="mt-4 pt-3 border-t border-warm-200/60">
              <span className="text-[11px] font-sans font-semibold text-earth-600 block mb-2">
                Supporting Evidence:
              </span>
              <ul className="space-y-1.5">
                {latest_decision.reasons.map((reason, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-earth-600">
                    <CheckCircle className="w-3.5 h-3.5 text-sage-500 flex-shrink-0 mt-0.5" />
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {latest_decision?.warnings && latest_decision.warnings.length > 0 && (
            <div className="mt-3 pt-3 border-t border-warm-200/60">
              <span className="text-[11px] font-sans font-semibold text-accent-600 block mb-2">
                Caveats & Warnings:
              </span>
              <ul className="space-y-1.5">
                {latest_decision.warnings.map((warn, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-earth-500">
                    <AlertTriangle className="w-3.5 h-3.5 text-accent-500 flex-shrink-0 mt-0.5" />
                    <span>{warn}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Pollutants Breakdown */}
        <div>
          <h3 className="font-sentinel font-bold text-sm text-earth-900 mb-3 flex items-center justify-between">
            <span>Pollutant Observations</span>
            <span className="text-[10px] font-mono text-earth-400">µg/m³</span>
          </h3>

          <div className="grid grid-cols-2 gap-3">
            {/* PM10 Card */}
            <div className="bg-white p-3.5 rounded-xl border border-warm-200">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-sans font-semibold text-earth-500">PM10</span>
                <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-md border ${
                  pm10?.data_type === 'observed' ? 'bg-sage-500/10 text-sage-600 border-sage-500/30' : 'bg-warm-200 text-earth-500 border-warm-300'
                }`}>
                  {pm10?.data_type || 'modeled'}
                </span>
              </div>
              <div className="font-sentinel font-bold text-2xl text-earth-900 font-tabular mt-1">
                {formatNumber(pm10?.value, 1)}
              </div>
              {pm10?.station_id && (
                <p className="text-[10px] text-earth-400 font-mono mt-1">
                  Station: {pm10.station_id} {pm10.station_distance_km ? `(${pm10.station_distance_km}km)` : ''}
                </p>
              )}
            </div>

            {/* PM2.5 Card */}
            <div className="bg-white p-3.5 rounded-xl border border-warm-200">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-sans font-semibold text-earth-500">PM2.5</span>
                <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-md border ${
                  pm25?.data_type === 'observed' ? 'bg-sage-500/10 text-sage-600 border-sage-500/30' : 'bg-warm-200 text-earth-500 border-warm-300'
                }`}>
                  {pm25?.data_type || 'modeled'}
                </span>
              </div>
              <div className="font-sentinel font-bold text-2xl text-earth-900 font-tabular mt-1">
                {formatNumber(pm25?.value, 1)}
              </div>
              {pm25?.station_id && (
                <p className="text-[10px] text-earth-400 font-mono mt-1">
                  Station: {pm25.station_id} {pm25.station_distance_km ? `(${pm25.station_distance_km}km)` : ''}
                </p>
              )}
            </div>
          </div>

          {/* PM Ratio Bar */}
          <div className="mt-3 bg-white p-3 rounded-xl border border-warm-200 flex items-center justify-between">
            <div>
              <span className="text-xs font-sans font-medium text-earth-700">PM10 / PM2.5 Ratio</span>
              <p className="text-[10px] text-earth-400">
                {ratio && ratio >= 2.0
                  ? '>= 2.0: Coarse dust dominance heuristic'
                  : '< 2.0: Combustion soot / vehicular emissions'}
              </p>
            </div>
            <div className={`font-mono font-bold text-lg font-tabular px-3 py-1 rounded-xl ${
              ratio && ratio >= 2.0 ? 'bg-accent-500/10 text-accent-600 border border-accent-500/30' : 'bg-warm-100 text-earth-600'
            }`}>
              {formatNumber(ratio, 2)}
            </div>
          </div>
        </div>

        {/* Meteorological Parameters */}
        <div>
          <h3 className="font-sentinel font-bold text-sm text-earth-900 mb-3">
            Weather Conditions
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            
            <div className="bg-white p-3 rounded-xl border border-warm-200">
              <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                <Thermometer className="w-3 h-3 text-accent-400" /> Temp
              </span>
              <span className="font-mono font-semibold text-sm text-earth-700 font-tabular">
                {formatNumber(weather?.temperature_c, 1)}°C
              </span>
            </div>

            <div className="bg-white p-3 rounded-xl border border-warm-200">
              <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                <Droplets className="w-3 h-3 text-sage-400" /> Humidity
              </span>
              <span className={`font-mono font-semibold text-sm font-tabular ${
                (weather?.relative_humidity || 0) >= 80 ? 'text-accent-600 font-bold' : 'text-earth-700'
              }`}>
                {formatNumber(weather?.relative_humidity, 0)}%
              </span>
            </div>

            <div className="bg-white p-3 rounded-xl border border-warm-200">
              <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                <Wind className="w-3 h-3 text-earth-400" /> Wind
              </span>
              <span className={`font-mono font-semibold text-sm font-tabular ${
                (weather?.wind_speed_kmh || 0) >= 20 ? 'text-accent-600 font-bold' : 'text-earth-700'
              }`}>
                {formatNumber(weather?.wind_speed_kmh, 1)} km/h
              </span>
            </div>

            <div className="bg-white p-3 rounded-xl border border-warm-200">
              <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                <Compass className="w-3 h-3 text-earth-400" /> Direction
              </span>
              <span className="font-mono font-semibold text-sm text-earth-700 font-tabular">
                {weather?.wind_direction_deg != null ? `${Math.round(weather.wind_direction_deg)}°` : '—'}
              </span>
            </div>

            <div className="bg-white p-3 rounded-xl border border-warm-200 col-span-2">
              <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                <Layers className="w-3 h-3 text-earth-400" /> Boundary Layer
              </span>
              <span className={`font-mono font-semibold text-sm font-tabular ${
                (weather?.boundary_layer_height_m || 999) <= 300 ? 'text-accent-600' : 'text-earth-700'
              }`}>
                {weather?.boundary_layer_height_m != null ? `${Math.round(weather.boundary_layer_height_m)}m` : '—'}
                {(weather?.boundary_layer_height_m || 999) <= 300 && (
                  <span className="text-[10px] font-normal text-accent-500 ml-1.5">(Inversion)</span>
                )}
              </span>
            </div>

          </div>
        </div>

        {/* Spatial Features */}
        <div className="space-y-3">
          <h3 className="font-sentinel font-bold text-sm text-earth-900">
            Spatial Context
          </h3>

          <div className="bg-white p-3.5 rounded-xl border border-warm-200">
            <div className="flex items-center gap-2 mb-1.5">
              <HardHat className="w-4 h-4 text-yellow-600" />
              <span className="text-xs font-sans font-semibold text-earth-700">Construction Sites (~300m)</span>
            </div>
            {infra?.has_construction_nearby ? (
              <div>
                <p className="text-xs text-yellow-700 font-medium">
                  Active construction within {infra.construction_distance_meters || 300}m
                </p>
                {infra.construction_sites && infra.construction_sites.length > 0 && (
                  <ul className="mt-1.5 space-y-1">
                    {infra.construction_sites.map((site, idx) => (
                      <li key={idx} className="text-[11px] text-earth-500 font-mono">• {site}</li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="text-xs text-earth-400">No active construction within 300m.</p>
            )}
          </div>

          <div className="bg-white p-3.5 rounded-xl border border-warm-200">
            <div className="flex items-center gap-2 mb-1.5">
              <Flame className="w-4 h-4 text-accent-500" />
              <span className="text-xs font-sans font-semibold text-earth-700">Thermal Anomalies (~50km)</span>
            </div>
            {fire && fire.nearby_fires_count > 0 ? (
              <div className="text-xs text-earth-600">
                <p className="font-medium text-accent-600">
                  {fire.nearby_fires_count} active anomalies (closest: {fire.closest_fire_distance_km}km).
                </p>
                <p className="text-[11px] text-earth-400 mt-1">
                  Smoke transport: {fire.possible_smoke_transport ? 'Upwind toward zone' : 'Deflected by wind'}.
                </p>
              </div>
            ) : (
              <p className="text-xs text-earth-400">No fire anomalies within 50km.</p>
            )}
          </div>

        </div>

        {/* Timestamps */}
        <div className="bg-warm-100 p-3.5 rounded-xl border border-warm-200 text-[11px] font-mono text-earth-500 space-y-1">
          <div className="flex items-center justify-between">
            <span>Observed:</span>
            <span className="text-earth-700">{formatDateTime(latest_reading?.timestamp)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Scored:</span>
            <span className="text-earth-700">{formatDateTime(latest_decision?.scored_at)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Mode:</span>
            <span className="text-accent-600 uppercase">{latest_decision?.data_mode || 'DEMO'}</span>
          </div>
        </div>

      </div>

    </div>
  );
};
