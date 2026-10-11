import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import {
  SystemOverview,
  ZoneWithLatest,
  WaterSavingsAnalytics,
  StationObservation,
  AlertRecord,
} from '../types';
import { InteractivePollutionMap } from '../components/InteractivePollutionMap';
import { PollutionTrendChart } from '../components/PollutionTrendChart';
import { AirFlowCard } from '../components/AirFlowCard';
import { CarbonMonitoringCard } from '../components/CarbonMonitoringCard';
import { ZoneDetailDrawer } from '../components/ZoneDetailDrawer';
import { AssumptionModal } from '../components/AssumptionModal';

export const DashboardPage: React.FC = () => {
  const [searchParams] = useSearchParams();

  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [zones, setZones] = useState<ZoneWithLatest[]>([]);
  const [waterData, setWaterData] = useState<WaterSavingsAnalytics | null>(null);
  const [stations, setStations] = useState<StationObservation[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);

  const [selectedZone, setSelectedZone] = useState<ZoneWithLatest | null>(null);
  const [selectedCustomName, setSelectedCustomName] = useState<string | null>(null);
  const [customCoords, setCustomCoords] = useState<[number, number] | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [isAssumptionModalOpen, setIsAssumptionModalOpen] = useState(false);
  const [baselineRate, setBaselineRate] = useState(3.0);
  const [litersPerOp, setLitersPerOp] = useState(5000.0);
  const [elevatedTile, setElevatedTile] = useState<'trend' | 'airflow' | 'carbon' | null>(null);

  // Close elevated tile on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setElevatedTile(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load Dashboard Data
  useEffect(() => {
    const loadAll = async () => {
      try {
        setIsLoading(true);
        const [ov, zn, wt, st, al] = await Promise.all([
          api.getOverview().catch(() => null),
          api.getZones().catch(() => []),
          api.getWaterSavings(7, baselineRate, litersPerOp).catch(() => null),
          api.getStations().catch(() => []),
          api.getAlerts(10).catch(() => []),
        ]);

        if (ov) setOverview(ov);
        if (zn && zn.length > 0) {
          setZones(zn);
          setSelectedZone(zn[0]); // Default focus zone
        }
        if (wt) setWaterData(wt);
        if (st) setStations(st);
        if (al) setAlerts(al);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadAll();
  }, [baselineRate, litersPerOp]);

  // Handle URL params if any (e.g., from search bar)
  useEffect(() => {
    const lat = searchParams.get('lat');
    const lon = searchParams.get('lon');
    const name = searchParams.get('name');

    if (lat && lon) {
      const latNum = parseFloat(lat);
      const lonNum = parseFloat(lon);
      if (!isNaN(latNum) && !isNaN(lonNum)) {
        setCustomCoords([latNum, lonNum]);
        if (name) setSelectedCustomName(decodeURIComponent(name));
      }
    }
  }, [searchParams]);

  // Map Click Handler for inspecting any geographical point
  const handleMapClick = async (lat: number, lon: number) => {
    setElevatedTile(null);
    try {
      setCustomCoords([lat, lon]);
      const res = await api.reverseGeo(lat, lon);
      if (res?.display_name) {
        setSelectedCustomName(res.display_name.split(',')[0]);
      }
    } catch {
      setSelectedCustomName(`Point (${lat.toFixed(2)}, ${lon.toFixed(2)})`);
    }
  };

  // Extract metrics from selectedZone or default fallbacks
  const latestReading = selectedZone?.latest_reading;
  const weather = latestReading?.weather;

  const rainfall = weather?.precipitation_mmh ?? 0;
  const humidity = weather?.relative_humidity ?? 84;
  const temperature = weather?.temperature_c ?? 23;
  const aqiValue =
    latestReading?.pm25?.value !== null && latestReading?.pm25?.value !== undefined
      ? Math.round(latestReading.pm25.value)
      : 42;
  const windSpeedKmh = weather?.wind_speed_kmh ?? 7.5;
  const windDirectionDeg = weather?.wind_direction_deg ?? 45;
  const boundaryLayer = weather?.boundary_layer_height_m ?? 450;

  const centerCoords: [number, number] = customCoords
    ? customCoords
    : selectedZone
      ? [selectedZone.zone.latitude, selectedZone.zone.longitude]
      : [28.6139, 77.2090]; // Delhi NCR central focus

  return (
    <div className="flex flex-col gap-2 sm:gap-3 animate-fade-up w-full">

      {/* Main Full-Width Interactive Map Canvas with Floating Bubbles & Floating Analytics Cards */}
      <section className="w-full relative shadow-sm">
        <InteractivePollutionMap
          center={centerCoords}
          zoom={12}
          zones={zones}
          selectedZone={selectedZone}
          onSelectZone={(zone) => {
            setSelectedZone(zone);
            setCustomCoords(null);
            setSelectedCustomName(zone.zone.name);
          }}
          stations={stations}
          onMapClick={handleMapClick}
          selectedLocationName={selectedCustomName || selectedZone?.zone?.name}
          rainfallMm={rainfall}
          humidityPercent={humidity}
          temperatureC={temperature}
          aqiOrPm25={aqiValue}
        >
          {/* Bottom Row of 3 Floating Glass Analytics Cards Hovering Above the Map */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-12 gap-3.5 sm:gap-4.5 w-full pointer-events-none">
            {/* 1. Pollution Trend Analysis (Bottom-Left Card - 5 columns) */}
            <div className={`xl:col-span-5 h-full pointer-events-auto transition-all ${elevatedTile === 'trend' ? 'relative z-[560]' : 'relative z-[130]'}`}>
              <PollutionTrendChart
                currentAqi={aqiValue}
                currentSeverity={
                  aqiValue > 100
                    ? 'High Pollution'
                    : aqiValue > 50
                      ? 'Moderate Pollution'
                      : 'Good Air Quality'
                }
                isElevated={elevatedTile === 'trend'}
                onClick={() => setElevatedTile(elevatedTile === 'trend' ? null : 'trend')}
                className="h-full"
              />
            </div>

            {/* 2. Air Flow Status (Center Card - 4 columns) */}
            <div className={`xl:col-span-4 h-full pointer-events-auto transition-all ${elevatedTile === 'airflow' ? 'relative z-[560]' : 'relative z-[130]'}`}>
              <AirFlowCard
                windSpeedKmh={windSpeedKmh}
                windSpeedMs={windSpeedKmh ? windSpeedKmh / 3.6 : 1.0}
                windDirectionDeg={windDirectionDeg}
                boundaryLayerHeight={boundaryLayer}
                isElevated={elevatedTile === 'airflow'}
                onClick={() => setElevatedTile(elevatedTile === 'airflow' ? null : 'airflow')}
                className="h-full"
              />
            </div>

            {/* 3. Carbon Monitoring (Right Card - 3 columns) */}
            <div className={`md:col-span-2 xl:col-span-3 h-full pointer-events-auto transition-all ${elevatedTile === 'carbon' ? 'relative z-[560]' : 'relative z-[130]'}`}>
              <CarbonMonitoringCard
                netCarbonOffset="101,850,000 Ton Co2e"
                waterSavedLiters={waterData?.estimated_water_saved_liters}
                isElevated={elevatedTile === 'carbon'}
                onClick={() => setElevatedTile(elevatedTile === 'carbon' ? null : 'carbon')}
                className="h-full"
              />
            </div>
          </div>
        </InteractivePollutionMap>
      </section>

      {/* Detailed Zone Drawer on Selection */}
      <ZoneDetailDrawer
        item={selectedZone}
        onClose={() => setSelectedZone(null)}
      />

      {/* Assumptions Configuration Modal */}
      <AssumptionModal
        isOpen={isAssumptionModalOpen}
        onClose={() => setIsAssumptionModalOpen(false)}
        currentBaselineRate={baselineRate}
        currentLitersPerOp={litersPerOp}
        onApply={(r, l) => {
          setBaselineRate(r);
          setLitersPerOp(l);
        }}
      />

    </div>
  );
};

export default DashboardPage;
