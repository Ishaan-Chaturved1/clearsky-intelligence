import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { ZoneWithLatest, StationObservation } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatNumber } from '../utils/formatters';
import { Radio, Crosshair } from 'lucide-react';

interface ZoneMapProps {
  zones: ZoneWithLatest[];
  selectedZone: ZoneWithLatest | null;
  onSelectZone: (zone: ZoneWithLatest) => void;
  height?: string;
  onMapClick?: (lat: number, lon: number) => void;
  selectedCustomCoords?: [number, number] | null;
  selectedCustomName?: string | null;
  stations?: StationObservation[];
}

// Controller to handle center reset and panning to selected coordinates
const MapController: React.FC<{ center: [number, number]; zoom: number; selectedCoords?: [number, number] }> = ({
  selectedCoords
}) => {
  const map = useMap();

  useEffect(() => {
    if (selectedCoords) {
      map.flyTo(selectedCoords, 13, { duration: 1.2 });
    }
  }, [selectedCoords, map]);

  return null;
};

// Map click listener component
const MapClickHandler: React.FC<{ onMapClick?: (lat: number, lon: number) => void }> = ({ onMapClick }) => {
  useMapEvents({
    click(e) {
      if (onMapClick) {
        onMapClick(e.latlng.lat, e.latlng.lng);
      }
    }
  });
  return null;
};

// Custom SVG marker generator for operational zones
function createZoneMarkerIcon(decision?: string, priority?: number | null) {
  let color = '#A08B72'; // Advisory warm gray
  let isPulse = false;

  if (decision === 'INTERVENTION_RECOMMENDED') {
    color = '#3DA88E'; // Sage green
    if (priority && priority >= 4) {
      color = '#F06B42'; // Coral accent for priority 4 & 5
      isPulse = true;
    }
  } else if (decision === 'INTERVENTION_NOT_RECOMMENDED' || decision === 'INTERVENTION_DISCOURAGED') {
    color = '#D95430'; // Warm red
  } else if (decision === 'ALTERNATIVE_DUST_CONTROL_SUGGESTED') {
    color = '#D97706'; // Amber
  }

  const svgHtml = `
    <div class="relative flex items-center justify-center">
      ${isPulse ? `<span class="absolute w-8 h-8 rounded-full bg-accent-500/30 animate-ping"></span>` : ''}
      <div style="background-color: ${color}; box-shadow: 0 0 10px ${color}88;" class="w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-white text-[10px] font-mono font-bold shadow-md">
        ${priority ? priority : '•'}
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-zone-marker',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -14]
  });
}

// Marker icon for dynamic selected custom location
function createSelectedCustomIcon() {
  const svgHtml = `
    <div class="relative flex items-center justify-center">
      <span class="absolute w-10 h-10 rounded-full bg-sky-500/30 animate-ping"></span>
      <div class="w-8 h-8 rounded-full bg-sky-600 border-2 border-white shadow-lg flex items-center justify-center text-white">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="22" y1="12" x2="18" y2="12"></line>
          <line x1="6" y1="12" x2="2" y2="12"></line>
          <line x1="12" y1="6" x2="12" y2="2"></line>
          <line x1="12" y1="22" x2="12" y2="18"></line>
        </svg>
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-selected-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18]
  });
}

// Marker icon for real environmental monitoring stations
function createStationMarkerIcon() {
  const svgHtml = `
    <div class="relative flex items-center justify-center">
      <div class="w-4 h-4 rounded-full bg-indigo-600 border-2 border-white shadow-md flex items-center justify-center text-white">
        <div class="w-1.5 h-1.5 rounded-full bg-cyan-300"></div>
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-station-marker',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -10]
  });
}

export const ZoneMap: React.FC<ZoneMapProps> = ({
  zones,
  selectedZone,
  onSelectZone,
  height = '520px',
  onMapClick,
  selectedCustomCoords,
  selectedCustomName,
  stations = []
}) => {
  const defaultCenter: [number, number] = [28.63, 77.18];
  const defaultZoom = 11;
  const [showStations, setShowStations] = useState(true);

  const activeCoords: [number, number] | undefined = selectedCustomCoords
    ? selectedCustomCoords
    : selectedZone
    ? [selectedZone.zone.latitude, selectedZone.zone.longitude]
    : undefined;

  return (
    <div className="relative isolate z-0 rounded-2xl overflow-hidden border border-warm-200 bg-warm-100 shadow-warm">
      
      {/* Map Legend & Layer Controls Overlay */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2 max-w-full pointer-events-auto">
        <div className="bg-white/95 backdrop-blur-md px-3 py-1.5 rounded-xl border border-warm-200 text-xs flex items-center gap-3 shadow-warm-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sage-500 inline-block" />
            <span className="text-earth-600 font-medium">Recommended</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-accent-600 inline-block" />
            <span className="text-earth-600 font-medium">Discouraged</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-earth-400 inline-block" />
            <span className="text-earth-600 font-medium">Advisory</span>
          </div>
        </div>

        {stations.length > 0 && (
          <button
            onClick={() => setShowStations(!showStations)}
            className={`px-3 py-1.5 rounded-xl text-xs font-sans flex items-center gap-1.5 border shadow-warm-sm transition-all ${
              showStations
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold'
                : 'bg-white/90 border-warm-200 text-earth-500 hover:text-earth-700'
            }`}
            title="Toggle ground monitoring stations"
          >
            <Radio className="w-3 h-3 text-indigo-500" />
            <span>Stations ({stations.length})</span>
          </button>
        )}

        <div className="hidden sm:flex bg-white/90 backdrop-blur-md px-2.5 py-1.5 rounded-xl border border-warm-200 text-[11px] text-earth-500 items-center gap-1 shadow-warm-sm">
          <Crosshair className="w-3 h-3 text-accent-500" />
          <span>Click map to inspect any locality</span>
        </div>
      </div>

      <div style={{ height }}>
        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <MapController center={defaultCenter} zoom={defaultZoom} selectedCoords={activeCoords} />
          <MapClickHandler onMapClick={onMapClick} />
          
          {/* Free watermark-free OpenStreetMap basemap by default, or CARTO if API key is provided */}
          <TileLayer
            attribution={
              import.meta.env.VITE_CARTO_API_KEY
                ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }
            url={
              import.meta.env.VITE_CARTO_API_KEY
                ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${import.meta.env.VITE_CARTO_API_KEY}`
                : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }
          />

          {/* Render Predefined Operational Sectors */}
          {zones.map((item) => {
            const { zone, latest_reading, latest_decision } = item;
            const icon = createZoneMarkerIcon(latest_decision?.decision, latest_decision?.priority);

            return (
              <Marker
                key={zone.zone_id}
                position={[zone.latitude, zone.longitude]}
                icon={icon}
                eventHandlers={{
                  click: () => onSelectZone(item)
                }}
              >
                <Popup>
                  <div className="p-1 min-w-[200px]">
                    <div className="font-mono text-[10px] text-accent-500 font-semibold mb-0.5">
                      {zone.zone_id}
                    </div>
                    <h4 className="font-sentinel font-bold text-sm text-earth-900 mb-1.5">
                      {zone.name}
                    </h4>

                    <div className="mb-2">
                      <StatusBadge
                        decision={latest_decision?.decision}
                        priority={latest_decision?.priority}
                        size="sm"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-1 text-[11px] font-mono text-earth-600 bg-warm-100 p-1.5 rounded-lg mb-2">
                      <div>PM10: {formatNumber(latest_reading?.pm10?.value, 0)}</div>
                      <div>PM2.5: {formatNumber(latest_reading?.pm25?.value, 0)}</div>
                      <div className="col-span-2">Ratio: {formatNumber(latest_reading?.pm_ratio, 2)}</div>
                    </div>

                    <button
                      onClick={() => onSelectZone(item)}
                      className="w-full text-center text-xs font-sans font-semibold py-1.5 px-2 rounded-xl bg-accent-500 hover:bg-accent-600 text-white transition-colors"
                    >
                      Inspect Sector Dossier
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Render Real Ground Monitoring Stations */}
          {showStations && stations.map((st) => (
            <Marker
              key={st.station_id}
              position={[st.latitude, st.longitude]}
              icon={createStationMarkerIcon()}
            >
              <Popup>
                <div className="p-1 min-w-[190px]">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full bg-indigo-500" />
                    <span className="font-mono text-[10px] text-indigo-700 font-bold uppercase">Ground Station</span>
                  </div>
                  <h4 className="font-sentinel font-bold text-xs text-earth-900 mb-1">
                    {st.station_name}
                  </h4>
                  <p className="text-[10px] font-mono text-earth-500 mb-2">
                    {st.distance_km > 0 ? `Distance: ${st.distance_km} km` : 'Reference Station'}
                  </p>
                  <div className="grid grid-cols-2 gap-1 text-[10px] font-mono bg-warm-100 p-1.5 rounded-lg mb-1">
                    <div>PM10: {st.pm10 != null ? `${st.pm10} µg/m³` : 'N/A'}</div>
                    <div>PM2.5: {st.pm25 != null ? `${st.pm25} µg/m³` : 'N/A'}</div>
                  </div>
                  <p className="text-[9px] text-earth-400 italic">
                    Source: {st.provider}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Render Selected Dynamic Location Marker */}
          {selectedCustomCoords && (
            <Marker
              position={selectedCustomCoords}
              icon={createSelectedCustomIcon()}
            >
              <Popup>
                <div className="p-1 min-w-[180px]">
                  <div className="font-mono text-[10px] text-sky-600 font-bold mb-0.5">
                    SELECTED LOCALITY
                  </div>
                  <h4 className="font-sentinel font-bold text-sm text-earth-900 mb-1">
                    {selectedCustomName || 'Selected Geographic Point'}
                  </h4>
                  <p className="font-mono text-[11px] text-earth-500">
                    {selectedCustomCoords[0].toFixed(4)}°N, {selectedCustomCoords[1].toFixed(4)}°E
                  </p>
                </div>
              </Popup>
            </Marker>
          )}

        </MapContainer>
      </div>

    </div>
  );
};
