import React, { useState, useEffect } from 'react';
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
  Clock,
  Gauge,
  CloudRain,
  Sun,
  ShieldAlert,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Sliders,
  Target,
  Radio,
  Activity
} from 'lucide-react';
import {
  ZoneWithLatest,
  CandidateRoadSegment,
  ForecastWindow,
  LocationAnalysisResponse,
  AtmosphericAnalysis
} from '../types';
import { StatusBadge } from './StatusBadge';
import { api } from '../services/api';
import { formatNumber, formatCoordinates, formatDateTime, getConfidenceBadgeInfo } from '../utils/formatters';

interface ZoneDetailDrawerProps {
  item: ZoneWithLatest | null;
  dynamicAnalysis?: LocationAnalysisResponse | null;
  onClose: () => void;
}

export const ZoneDetailDrawer: React.FC<ZoneDetailDrawerProps> = ({ item, dynamicAnalysis, onClose }) => {
  const [activeTab, setActiveTab] = useState<'ATMOSPHERE' | 'PLANNING' | 'SPATIAL'>('ATMOSPHERE');
  const [segments, setSegments] = useState<CandidateRoadSegment[]>([]);
  const [forecastWindows, setForecastWindows] = useState<ForecastWindow[]>([]);
  const [atmAnalysis, setAtmAnalysis] = useState<AtmosphericAnalysis | null>(null);
  const [isLoadingPlanning, setIsLoadingPlanning] = useState(false);

  useEffect(() => {
    if (dynamicAnalysis) {
      setSegments(dynamicAnalysis.candidate_segments || []);
      setForecastWindows(dynamicAnalysis.forecast_windows || []);
      setIsLoadingPlanning(false);
      return;
    }

    if (!item) return;

    setIsLoadingPlanning(true);
    Promise.all([
      api.getZoneCandidateSegments(item.zone.zone_id).catch(() => null),
      api.getZoneForecastWindows(item.zone.zone_id).catch(() => null),
      api.getZoneAtmosphericAnalysis(item.zone.zone_id).catch(() => null)
    ])
      .then(([segRes, winRes, atmRes]) => {
        if (segRes?.segments) setSegments(segRes.segments);
        if (winRes?.windows) setForecastWindows(winRes.windows);
        if (atmRes) setAtmAnalysis(atmRes);
      })
      .finally(() => setIsLoadingPlanning(false));
  }, [item?.zone.zone_id, dynamicAnalysis]);

  if (!item && !dynamicAnalysis) return null;

  // Extract properties depending on whether viewing a predefined sector or dynamic location
  const zoneName = dynamicAnalysis ? dynamicAnalysis.display_name : item?.zone.name || 'Monitored Sector';
  const zoneId = dynamicAnalysis ? `GEO-${dynamicAnalysis.latitude.toFixed(2)}-${dynamicAnalysis.longitude.toFixed(2)}` : item?.zone.zone_id;
  const zoneType = dynamicAnalysis ? 'Discovered Geographic Locality' : item?.zone.zone_type;
  const latitude = dynamicAnalysis ? dynamicAnalysis.latitude : item?.zone.latitude || 28.61;
  const longitude = dynamicAnalysis ? dynamicAnalysis.longitude : item?.zone.longitude || 77.21;

  const pm25 = dynamicAnalysis ? dynamicAnalysis.pm25 : item?.latest_reading?.pm25;
  const pm10 = dynamicAnalysis ? dynamicAnalysis.pm10 : item?.latest_reading?.pm10;
  const ratio = dynamicAnalysis ? dynamicAnalysis.pm_ratio : item?.latest_reading?.pm_ratio;
  const weather = dynamicAnalysis ? dynamicAnalysis.weather : item?.latest_reading?.weather;
  const fire = dynamicAnalysis ? dynamicAnalysis.fire_summary : item?.latest_reading?.fire_summary;
  const infra = dynamicAnalysis ? dynamicAnalysis.nearby_infrastructure : item?.zone.nearby_infrastructure;

  const decision = dynamicAnalysis ? dynamicAnalysis.decision : item?.latest_decision?.decision;
  const priority = dynamicAnalysis ? dynamicAnalysis.priority : item?.latest_decision?.priority;
  const confidence = dynamicAnalysis ? dynamicAnalysis.confidence : item?.latest_decision?.confidence;
  const reasons = dynamicAnalysis ? dynamicAnalysis.reasons : item?.latest_decision?.reasons || [];
  const warnings = dynamicAnalysis ? dynamicAnalysis.warnings : item?.latest_decision?.warnings || [];
  const conditionsToChange = dynamicAnalysis ? dynamicAnalysis.conditions_to_change : item?.latest_decision?.conditions_to_change || [];
  const dataMode = dynamicAnalysis ? dynamicAnalysis.data_mode : item?.latest_decision?.data_mode || 'DEMO';
  const timestamp = dynamicAnalysis ? dynamicAnalysis.timestamp : item?.latest_reading?.timestamp;

  const aqiValue = dynamicAnalysis ? dynamicAnalysis.aqi_estimate : atmAnalysis?.aqi_estimate;
  const nearestStation = dynamicAnalysis?.nearest_station;
  const stationDist = dynamicAnalysis
    ? (nearestStation?.distance_km ?? (pm10?.station_distance_km || pm25?.station_distance_km))
    : atmAnalysis?.nearest_station_distance_km;

  const confidenceInfo = getConfidenceBadgeInfo(confidence);

  // Helper for AQI category color
  const getAqiCategory = (aqi: number | null | undefined) => {
    if (aqi == null) return { label: 'Unavailable', color: 'text-earth-500 bg-warm-100 border-warm-300' };
    if (aqi <= 50) return { label: 'Good (0-50)', color: 'text-emerald-700 bg-emerald-50 border-emerald-300' };
    if (aqi <= 100) return { label: 'Satisfactory (51-100)', color: 'text-green-700 bg-green-50 border-green-300' };
    if (aqi <= 200) return { label: 'Moderate (101-200)', color: 'text-yellow-700 bg-yellow-50 border-yellow-300' };
    if (aqi <= 300) return { label: 'Poor (201-300)', color: 'text-orange-700 bg-orange-50 border-orange-300' };
    if (aqi <= 400) return { label: 'Very Poor (301-400)', color: 'text-rose-700 bg-rose-50 border-rose-300' };
    return { label: 'Severe (>400)', color: 'text-red-800 bg-red-100 border-red-400' };
  };

  const aqiCategory = getAqiCategory(aqiValue);

  return (
    <>
      {/* Dimmed backdrop */}
      <div
        className="fixed inset-0 bg-earth-900/40 backdrop-blur-xs z-[1999] transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="fixed inset-y-0 right-0 z-[2000] w-full max-w-2xl bg-warm-50 border-l border-warm-200 shadow-2xl flex flex-col overflow-hidden">
      
      {/* Header */}
      <div className="p-5 border-b border-warm-200 bg-white flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded-lg bg-warm-100 border border-warm-200 text-accent-500">
              {zoneId}
            </span>
            <span className="text-xs text-earth-400 font-sans">{zoneType}</span>
            <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-bold uppercase ${
              dataMode === 'LIVE' ? 'bg-sage-50 text-sage-700 border-sage-300' : 'bg-warm-100 text-earth-600 border-warm-300'
            }`}>
              {dataMode} DATA
            </span>
          </div>
          <h2 className="font-sentinel font-bold text-xl text-earth-900">
            {zoneName}
          </h2>
          <p className="font-mono text-[11px] text-earth-400 flex items-center gap-1 mt-0.5">
            <Compass className="w-3 h-3 text-earth-300" />
            <span>{formatCoordinates(latitude, longitude)}</span>
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

      {/* Navigation Tabs */}
      <div className="flex border-b border-warm-200 bg-white px-5 gap-4">
        {[
          { key: 'ATMOSPHERE', label: 'Atmospheric Intelligence' },
          { key: 'PLANNING', label: 'Intervention Planning & Corridors' },
          { key: 'SPATIAL', label: 'Geospatial Context' }
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key as any)}
            className={`py-2.5 text-xs font-sans font-medium border-b-2 transition-all ${
              activeTab === t.key
                ? 'border-accent-500 text-accent-600 font-semibold'
                : 'border-transparent text-earth-500 hover:text-earth-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        
        {/* Operational Status Banner */}
        <div className="bg-white rounded-2xl p-4 border border-warm-200 shadow-warm-sm">
          <div className="flex items-center justify-between gap-2 mb-3">
            <span className="text-xs font-sans font-semibold text-earth-400 uppercase tracking-wider">
              Operational Decision
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-lg border bg-warm-100 border-warm-200 text-earth-600">
              Confidence: {confidenceInfo.label}
            </span>
          </div>

          <StatusBadge
            decision={decision}
            priority={priority}
            size="md"
          />

          {/* Decision Rationale */}
          {reasons && reasons.length > 0 && (
            <div className="mt-4 pt-3 border-t border-warm-200/60">
              <span className="text-[11px] font-sans font-semibold text-earth-600 block mb-2">
                Scientific Rationale &amp; Evidence:
              </span>
              <ul className="space-y-1.5">
                {reasons.map((reason, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-earth-600">
                    <CheckCircle className="w-3.5 h-3.5 text-sage-500 flex-shrink-0 mt-0.5" />
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Caveats & Warnings */}
          {warnings && warnings.length > 0 && (
            <div className="mt-3 pt-3 border-t border-warm-200/60">
              <span className="text-[11px] font-sans font-semibold text-accent-600 block mb-2">
                Caveats &amp; Safety Warnings:
              </span>
              <ul className="space-y-1.5">
                {warnings.map((warn, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-earth-500">
                    <AlertTriangle className="w-3.5 h-3.5 text-accent-500 flex-shrink-0 mt-0.5" />
                    <span>{warn}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conditions that would change decision */}
          {conditionsToChange && conditionsToChange.length > 0 && (
            <div className="mt-3 pt-3 border-t border-warm-200/60">
              <span className="text-[11px] font-sans font-semibold text-earth-500 block mb-1">
                Conditions to Alter Decision:
              </span>
              <ul className="space-y-1 text-xs text-earth-600 list-disc list-inside">
                {conditionsToChange.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* TAB 1: ATMOSPHERE */}
        {activeTab === 'ATMOSPHERE' && (
          <div className="space-y-5 animate-fade-up">
            
            {/* CPCB Air Quality Index & Nearest Station Card */}
            <div className="bg-white p-4 rounded-xl border border-warm-200 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-sans font-semibold text-earth-600 flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-accent-500" />
                  Indian National AQI (CPCB Breakpoint Standard)
                </span>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold ${aqiCategory.color}`}>
                  {aqiCategory.label}
                </span>
              </div>

              <div className="flex items-baseline gap-3">
                <div className="font-sentinel font-bold text-3xl text-earth-900 font-tabular">
                  {aqiValue != null ? aqiValue : 'Unavailable'}
                </div>
                <p className="text-xs text-earth-500 font-sans">
                  {aqiValue != null
                    ? 'Evaluated per Indian CPCB standard sub-index formulas using validated particulate mass.'
                    : 'AQI calculation requires valid dual PM10 & PM2.5 concentrations; raw values are never mislabeled as AQI.'}
                </p>
              </div>

              {/* Nearest Station Provenance */}
              <div className="p-2.5 rounded-lg bg-warm-50 border border-warm-200/80 text-xs flex items-start gap-2">
                <Radio className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-earth-800 font-medium font-sans">
                    {nearestStation
                      ? `${nearestStation.station_name} (${nearestStation.distance_km.toFixed(1)} km away)`
                      : stationDist
                      ? `Nearest Observation Station: ~${stationDist.toFixed(1)} km away`
                      : 'No ground station detected within 25km radius; regional atmospheric chemistry model applied'}
                  </div>
                  <div className="text-[10px] font-mono text-earth-400 mt-0.5">
                    Data Source: {nearestStation?.provider || 'OpenAQ v3 Ground Stations & Open-Meteo Reanalysis'}
                  </div>
                </div>
              </div>
            </div>

            {/* Pollutants Breakdown */}
            <div>
              <h3 className="font-sentinel font-bold text-sm text-earth-900 mb-3 flex items-center justify-between">
                <span>Particulate Speciation &amp; Mass</span>
                <span className="text-[10px] font-mono text-earth-400">µg/m³</span>
              </h3>

              <div className="grid grid-cols-2 gap-3">
                {/* PM10 Card */}
                <div className="bg-white p-3.5 rounded-xl border border-warm-200">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-sans font-semibold text-earth-500">PM10 (Coarse Dust)</span>
                    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-md border ${
                      pm10?.data_type === 'observed' ? 'bg-sage-500/10 text-sage-600 border-sage-500/30' : 'bg-warm-200 text-earth-500 border-warm-300'
                    }`}>
                      {pm10?.data_type || 'modeled'}
                    </span>
                  </div>
                  <div className="font-sentinel font-bold text-2xl text-earth-900 font-tabular mt-1">
                    {pm10?.value != null ? formatNumber(pm10.value, 1) : 'Unavailable'}
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
                    <span className="text-xs font-sans font-semibold text-earth-500">PM2.5 (Fine Soot)</span>
                    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-md border ${
                      pm25?.data_type === 'observed' ? 'bg-sage-500/10 text-sage-600 border-sage-500/30' : 'bg-warm-200 text-earth-500 border-warm-300'
                    }`}>
                      {pm25?.data_type || 'modeled'}
                    </span>
                  </div>
                  <div className="font-sentinel font-bold text-2xl text-earth-900 font-tabular mt-1">
                    {pm25?.value != null ? formatNumber(pm25.value, 1) : 'Unavailable'}
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
                  <span className="text-xs font-sans font-medium text-earth-700">PM10 / PM2.5 Ratio Heuristic</span>
                  <p className="text-[10px] text-earth-400">
                    {ratio && ratio >= 2.0
                      ? '>= 2.0: Dominance of mechanical road & construction dust'
                      : '< 2.0: Combustion smoke, diesel soot, or regional agricultural plume'}
                  </p>
                </div>
                <div className={`font-mono font-bold text-lg font-tabular px-3 py-1 rounded-xl ${
                  ratio && ratio >= 2.0 ? 'bg-accent-500/10 text-accent-600 border border-accent-500/30' : 'bg-warm-100 text-earth-600'
                }`}>
                  {ratio != null ? formatNumber(ratio, 2) : '—'}
                </div>
              </div>
            </div>

            {/* Atmospheric Pressure & Synoptic Evolution */}
            <div className="bg-white p-4 rounded-xl border border-warm-200 space-y-3">
              <h3 className="font-sentinel font-bold text-sm text-earth-900 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Gauge className="w-4 h-4 text-accent-500" />
                  Atmospheric Pressure &amp; Barometric Trends
                </span>
                <span className="text-[10px] font-mono text-earth-400">hPa</span>
              </h3>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="bg-warm-50 p-2.5 rounded-lg border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase block font-sans">Surface Pressure</span>
                  <span className="font-mono font-bold text-sm text-earth-800">
                    {weather?.surface_pressure_hpa ? `${formatNumber(weather.surface_pressure_hpa, 1)} hPa` : '—'}
                  </span>
                </div>

                <div className="bg-warm-50 p-2.5 rounded-lg border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase block font-sans">3h Trend</span>
                  <span className={`font-mono font-bold text-sm flex items-center gap-0.5 ${
                    (weather?.pressure_trend_3h_hpa || 0) < 0 ? 'text-accent-600' : 'text-sage-600'
                  }`}>
                    {(weather?.pressure_trend_3h_hpa || 0) >= 0 ? '+' : ''}{formatNumber(weather?.pressure_trend_3h_hpa, 1)} hPa
                  </span>
                </div>

                <div className="bg-warm-50 p-2.5 rounded-lg border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase block font-sans">6h Trend</span>
                  <span className="font-mono font-bold text-sm text-earth-700">
                    {(weather?.pressure_trend_6h_hpa || 0) >= 0 ? '+' : ''}{formatNumber(weather?.pressure_trend_6h_hpa, 1)} hPa
                  </span>
                </div>

                <div className="bg-warm-50 p-2.5 rounded-lg border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase block font-sans">Tendency</span>
                  <span className="font-mono font-bold text-xs px-2 py-0.5 rounded bg-warm-200 text-earth-700 inline-block mt-0.5">
                    {weather?.pressure_tendency || 'STEADY'}
                  </span>
                </div>
              </div>

              <p className="text-[11px] text-earth-500 font-sans italic bg-warm-50/70 p-2.5 rounded-lg border border-warm-200/60">
                Atmospheric pressure is evaluated as supporting meteorological context. Falling pressure indicates regional airmass instability or approaching troughs; it is never used as an isolated trigger for intervention.
              </p>
            </div>

            {/* Meteorological Parameters */}
            <div>
              <h3 className="font-sentinel font-bold text-sm text-earth-900 mb-3">
                Current Meteorological Conditions
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                
                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <Thermometer className="w-3 h-3 text-accent-400" /> Temperature
                  </span>
                  <span className="font-mono font-semibold text-sm text-earth-700 font-tabular">
                    {weather?.temperature_c != null ? `${formatNumber(weather.temperature_c, 1)}°C` : '—'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <Droplets className="w-3 h-3 text-sage-400" /> Relative Humidity
                  </span>
                  <span className={`font-mono font-semibold text-sm font-tabular ${
                    (weather?.relative_humidity || 0) >= 80 ? 'text-accent-600 font-bold' : 'text-earth-700'
                  }`}>
                    {weather?.relative_humidity != null ? `${formatNumber(weather.relative_humidity, 0)}%` : '—'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <Wind className="w-3 h-3 text-earth-400" /> Wind Speed
                  </span>
                  <span className={`font-mono font-semibold text-sm font-tabular ${
                    (weather?.wind_speed_kmh || 0) >= 20 ? 'text-accent-600 font-bold' : 'text-earth-700'
                  }`}>
                    {weather?.wind_speed_kmh != null ? `${formatNumber(weather.wind_speed_kmh, 1)} km/h` : '—'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <CloudRain className="w-3 h-3 text-sky-500" /> Precipitation
                  </span>
                  <span className="font-mono font-semibold text-sm text-earth-700 font-tabular">
                    {weather?.precipitation_mmh != null ? `${formatNumber(weather.precipitation_mmh, 1)} mm/h` : '0.0 mm/h'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <Sun className="w-3 h-3 text-amber-500" /> Surface Drying Time
                  </span>
                  <span className="font-mono font-semibold text-sm text-earth-700 font-tabular">
                    {weather?.estimated_surface_drying_time_min ? `~${weather.estimated_surface_drying_time_min} min` : '—'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-xl border border-warm-200">
                  <span className="text-[10px] text-earth-400 uppercase flex items-center gap-1 mb-1 font-sans">
                    <Layers className="w-3 h-3 text-earth-400" /> Boundary Layer
                  </span>
                  <span className={`font-mono font-semibold text-sm font-tabular ${
                    (weather?.boundary_layer_height_m || 999) <= 300 ? 'text-accent-600 font-bold' : 'text-earth-700'
                  }`}>
                    {weather?.boundary_layer_height_m != null ? `${Math.round(weather.boundary_layer_height_m)}m` : '—'}
                  </span>
                </div>

              </div>
            </div>

          </div>
        )}

        {/* TAB 2: PLANNING */}
        {activeTab === 'PLANNING' && (
          <div className="space-y-5 animate-fade-up">
            
            {/* Candidate Road Corridors */}
            <div className="bg-white p-4 rounded-xl border border-warm-200 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-sentinel font-bold text-sm text-earth-900 flex items-center gap-1.5">
                  <Target className="w-4 h-4 text-accent-500" />
                  Candidate Municipal Corridors (OpenStreetMap)
                </h3>
                <span className="text-[11px] font-mono text-earth-400">
                  {segments.length} corridors evaluated
                </span>
              </div>

              {isLoadingPlanning ? (
                <div className="p-6 text-center text-xs text-earth-400">Loading candidate road segments...</div>
              ) : segments.length === 0 ? (
                <div className="p-6 text-center text-xs text-earth-400">No candidate segments generated for this location.</div>
              ) : (
                <div className="space-y-2.5">
                  {segments.map((seg) => (
                    <div key={seg.segment_id} className="p-3 rounded-xl bg-warm-50 border border-warm-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-white border border-warm-300 text-earth-600">
                            {seg.road_classification.toUpperCase()}
                          </span>
                          <span className="font-sans font-semibold text-xs text-earth-800">
                            {seg.road_name}
                          </span>
                          {seg.construction_adjacent && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 font-mono">
                              Construction {seg.construction_distance_m || 200}m
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-[11px] text-earth-400 mt-1 flex flex-wrap gap-3">
                          <span>Length: {seg.length_km} km</span>
                          <span>Width: {seg.estimated_width_m} m</span>
                          <span>Area: {formatNumber(seg.surface_area_m2, 0)} m²</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 sm:text-right">
                        <div>
                          <div className="font-mono font-bold text-xs text-earth-800">
                            {formatNumber(seg.water_required_liters, 0)} L
                          </div>
                          <div className="text-[10px] font-mono text-earth-400">
                            {seg.tanker_trips_required} tanker trip{seg.tanker_trips_required > 1 ? 's' : ''} (₹{formatNumber(seg.estimated_cost_inr, 0)})
                          </div>
                        </div>

                        <span className={`font-mono text-xs font-bold px-2 py-1 rounded-lg border ${
                          seg.priority_score >= 4 ? 'bg-rose-100 text-rose-700 border-rose-300' : 'bg-warm-200 text-earth-700 border-warm-300'
                        }`}>
                          P{seg.priority_score}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Operating Windows Ranking (Best Time to Spray) */}
            <div className="bg-white p-4 rounded-xl border border-warm-200 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-sentinel font-bold text-sm text-earth-900 flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-accent-500" />
                  Forecast Operating Windows (Ranked Best Time to Spray)
                </h3>
                <span className="text-[11px] font-mono text-earth-400">Next 12 Hours (Open-Meteo)</span>
              </div>

              {isLoadingPlanning ? (
                <div className="p-6 text-center text-xs text-earth-400">Evaluating hourly weather suitability...</div>
              ) : forecastWindows.length === 0 ? (
                <div className="p-6 text-center text-xs text-earth-400 font-sans">
                  Hourly forecast windows currently unavailable from Open-Meteo for this coordinate.
                </div>
              ) : (
                <div className="space-y-2">
                  {forecastWindows.slice(0, 5).map((win) => (
                    <div key={win.window_id} className="p-3 rounded-xl bg-warm-50 border border-warm-200 flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-xs text-earth-900">{win.hour_label}</span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                            win.suitability_label === 'OPTIMAL' ? 'bg-sage-100 text-sage-800 border-sage-300' :
                            win.suitability_label === 'MODERATE' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                            'bg-rose-100 text-rose-800 border-rose-300'
                          }`}>
                            {win.suitability_label} ({win.suitability_score}/100)
                          </span>
                        </div>
                        <p className="text-[11px] text-earth-600 mt-1 font-sans">{win.rationale}</p>
                        {win.safety_concerns.length > 0 && (
                          <p className="text-[10px] text-accent-600 mt-0.5 font-sans">
                            Caution: {win.safety_concerns.join(', ')}
                          </p>
                        )}
                      </div>

                      <div className="text-right font-mono text-[11px] text-earth-500 whitespace-nowrap">
                        <div>{win.forecast_temp_c}°C | {win.forecast_rh_percent}% RH</div>
                        <div>Wind: {win.forecast_wind_kmh} km/h</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* TAB 3: SPATIAL */}
        {activeTab === 'SPATIAL' && (
          <div className="space-y-3 animate-fade-up">
            <h3 className="font-sentinel font-bold text-sm text-earth-900">
              Surrounding Infrastructure &amp; Environmental Evidence
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
                <p className="text-xs text-earth-400 font-sans">No active construction tagged within 300m.</p>
              )}
            </div>

            <div className="bg-white p-3.5 rounded-xl border border-warm-200">
              <div className="flex items-center gap-2 mb-1.5">
                <Flame className="w-4 h-4 text-accent-500" />
                <span className="text-xs font-sans font-semibold text-earth-700">Satellite Thermal Anomalies (~50km)</span>
              </div>
              {fire && fire.nearby_fires_count > 0 ? (
                <div className="text-xs text-earth-600 font-sans">
                  <p className="font-medium text-accent-600">
                    {fire.nearby_fires_count} active anomalies (closest: {fire.closest_fire_distance_km}km).
                  </p>
                  <p className="text-[11px] text-earth-400 mt-1">
                    Smoke transport: {fire.possible_smoke_transport ? 'Upwind toward sector corridor' : 'Deflected downwind'}.
                  </p>
                </div>
              ) : (
                <p className="text-xs text-earth-400 font-sans">No satellite thermal anomalies detected within 50km.</p>
              )}
            </div>
          </div>
        )}

        {/* Timestamps & Audit Footnote */}
        <div className="bg-warm-100 p-3.5 rounded-xl border border-warm-200 text-[11px] font-mono text-earth-500 space-y-1">
          <div className="flex items-center justify-between">
            <span>Observed At:</span>
            <span className="text-earth-700">{formatDateTime(timestamp)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Evaluated At:</span>
            <span className="text-earth-700">{formatDateTime(timestamp)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Data Mode:</span>
            <span className="text-accent-600 uppercase">{dataMode}</span>
          </div>
        </div>

      </div>

    </div>
    </>
  );
};
