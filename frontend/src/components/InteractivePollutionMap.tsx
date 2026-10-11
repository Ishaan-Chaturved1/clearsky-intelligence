import React, { useState, useEffect, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import L from 'leaflet';
import { CloudRain, Droplets, Thermometer, Sparkles } from 'lucide-react';
import { ZoneWithLatest, StationObservation } from '../types';
import { MetricBubble } from './MetricBubble';
import { PollutionHeatLayer } from './PollutionHeatLayer';
import { PollutionLegend } from './PollutionLegend';
import { MapControls } from './MapControls';
import { TopPollutedDropdown } from './TopPollutedDropdown';
import { DraggableMetricSpheres } from './DraggableMetricSpheres';

interface InteractivePollutionMapProps {
  center: [number, number];
  zoom?: number;
  zones?: ZoneWithLatest[];
  selectedZone: ZoneWithLatest | null;
  onSelectZone: (zone: ZoneWithLatest) => void;
  stations?: StationObservation[];
  onMapClick?: (lat: number, lon: number) => void;
  selectedLocationName?: string;
  rainfallMm?: number | null;
  humidityPercent?: number | null;
  temperatureC?: number | null;
  aqiOrPm25?: number | string | null;
  children?: React.ReactNode;
}

// Controller to smoothly pan and zoom to target coordinates
const FlyToController: React.FC<{ targetCoords: [number, number] }> = ({ targetCoords }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(targetCoords, map.getZoom() < 11 ? 11 : map.getZoom(), {
      duration: 1.2,
      easeLinearity: 0.25,
    });
  }, [targetCoords, map]);
  return null;
};

// Map click listener
const ClickHandler: React.FC<{ onMapClick?: (lat: number, lon: number) => void }> = ({
  onMapClick,
}) => {
  useMapEvents({
    click(e) {
      if (onMapClick) onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

// Map instance capture component to safely pass Leaflet instance outside MapContainer
const MapInstanceCapture: React.FC<{ onMap: (map: L.Map) => void }> = ({ onMap }) => {
  const map = useMap();
  useEffect(() => {
    onMap(map);
  }, [map, onMap]);
  return null;
};

// Center Target Pin Marker Icon (matching the green pin in white circular badge from screenshot)
function createCenterPinIcon(label?: string) {
  const html = `
    <div class="relative flex items-center justify-center -translate-x-1/2 -translate-y-1/2">
      <!-- Outer pulsing ring -->
      <span class="absolute w-14 h-14 rounded-full bg-emerald-500/20 animate-ping"></span>
      <!-- White circular elevated badge with green pin -->
      <div class="relative w-12 h-12 rounded-full bg-white shadow-[0_10px_25px_rgba(0,0,0,0.15)] border-2 border-white flex items-center justify-center z-10">
        <div class="w-7 h-7 rounded-full bg-emerald-600 flex items-center justify-center text-white shadow-xs">
          <svg viewBox="0 0 24 24" class="w-4 h-4" fill="currentColor">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
          </svg>
        </div>
      </div>
      ${
        label
          ? `<div class="absolute -bottom-8 whitespace-nowrap bg-white/95 backdrop-blur-md px-2.5 py-1 rounded-full text-[11px] font-bold text-slate-800 shadow-md border border-slate-100">
              ${label}
            </div>`
          : ''
      }
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-center-pin',
    iconSize: [48, 48],
    iconAnchor: [24, 24],
    popupAnchor: [0, -28],
  });
}

// Station icon
function createStationIcon() {
  return L.divIcon({
    html: `
      <div class="w-3.5 h-3.5 rounded-full bg-indigo-600 border-2 border-white shadow-md flex items-center justify-center">
        <div class="w-1 h-1 rounded-full bg-cyan-300"></div>
      </div>
    `,
    className: 'station-icon',
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

export const InteractivePollutionMap: React.FC<InteractivePollutionMapProps> = ({
  center,
  zoom = 11,
  zones = [],
  selectedZone,
  onSelectZone,
  stations = [],
  onMapClick,
  selectedLocationName,
  rainfallMm = null,
  humidityPercent = null,
  temperatureC = null,
  aqiOrPm25 = null,
  children,
}) => {
  const [showContours, setShowContours] = useState(true);
  const [showStations, setShowStations] = useState(true);
  const [mapInstance, setMapInstance] = useState<L.Map | null>(null);
  const overlayContainerRef = useRef<HTMLDivElement>(null);

  const activeCenter: [number, number] = selectedZone
    ? [selectedZone.zone.latitude, selectedZone.zone.longitude]
    : center;

  const activeName =
    selectedLocationName || (selectedZone ? selectedZone.zone.name : 'Selected Area');

  return (
    <div className="relative w-full h-[calc(100vh-125px)] min-h-[500px] max-h-[820px] rounded-3xl sm:rounded-[32px] border border-white/60 shadow-xl bg-slate-100 select-none">
      
      {/* 1. Underlying Interactive Leaflet Canvas */}
      <MapContainer
        center={activeCenter}
        zoom={zoom}
        zoomControl={false}
        scrollWheelZoom={true}
        className="w-full h-full rounded-3xl sm:rounded-[32px] overflow-hidden"
        style={{ width: '100%', height: '100%', position: 'absolute', inset: 0 }}
      >
        <MapInstanceCapture onMap={setMapInstance} />
        <FlyToController targetCoords={activeCenter} />
        <ClickHandler onMapClick={onMapClick} />

        {/* Clean, watermark-free light geographical basemap */}
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com/">Esri</a>, OpenStreetMap'
          url={
            import.meta.env.VITE_CARTO_API_KEY
              ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${import.meta.env.VITE_CARTO_API_KEY}`
              : "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          }
          maxZoom={16}
        />
        {!import.meta.env.VITE_CARTO_API_KEY && (
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}"
            maxZoom={16}
          />
        )}

        {/* Organic Pollution Heat Contours */}
        <PollutionHeatLayer
          center={activeCenter}
          visible={showContours}
          zones={zones}
        />

        {/* Center Target Pin Marker */}
        <Marker position={activeCenter} icon={createCenterPinIcon(activeName)}>
          <Popup>
            <div className="p-2 min-w-[180px]">
              <div className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-0.5">
                Target Locality
              </div>
              <h4 className="font-bold text-sm text-slate-900 mb-1">{activeName}</h4>
              <p className="text-xs text-slate-500">
                Lat: {activeCenter[0].toFixed(3)}°, Lon: {activeCenter[1].toFixed(3)}°
              </p>
            </div>
          </Popup>
        </Marker>

        {/* Monitoring Stations */}
        {showStations &&
          stations.map((st) => (
            <Marker
              key={st.station_id}
              position={[st.latitude, st.longitude]}
              icon={createStationIcon()}
            >
              <Popup>
                <div className="p-1.5 text-xs text-slate-800">
                  <div className="font-bold text-slate-900">{st.station_name}</div>
                  <div className="text-[10px] text-slate-400 font-mono mb-1">{st.station_id}</div>
                  <div className="flex gap-2 text-slate-600">
                    <span>PM2.5: <b>{st.pm25 ?? '—'}</b></span>
                    <span>PM10: <b>{st.pm10 ?? '—'}</b></span>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Monitored Zones */}
        {zones.map((item) => {
          if (item.zone.zone_id === selectedZone?.zone?.zone_id) return null;
          return (
            <Marker
              key={item.zone.zone_id}
              position={[item.zone.latitude, item.zone.longitude]}
              eventHandlers={{
                click: () => onSelectZone(item),
              }}
              icon={L.divIcon({
                html: `
                  <div class="w-5 h-5 rounded-full bg-emerald-600/90 border-2 border-white shadow-sm flex items-center justify-center text-white text-[9px] font-bold cursor-pointer hover:scale-125 transition-transform">
                    •
                  </div>
                `,
                className: 'zone-marker',
                iconSize: [20, 20],
                iconAnchor: [10, 10],
              })}
            >
              <Popup>
                <div className="p-1 text-xs">
                  <div className="font-bold">{item.zone.name}</div>
                  <div className="text-slate-500">{item.zone.zone_type}</div>
                  <button
                    onClick={() => onSelectZone(item)}
                    className="mt-1 text-[10px] text-emerald-600 font-bold hover:underline"
                  >
                    Select Zone
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* 2. Floating Circular Metric Bubbles positioned over the map (matching WeatherSwim references) */}
      <div
        ref={overlayContainerRef}
        className="absolute inset-0 pointer-events-none z-[1000] p-3 sm:p-5 lg:p-6 flex flex-col justify-between"
      >
        {/* Floating Collapsible Top Polluted Localities Dropdown (Right) */}
        <div className="absolute right-3 sm:right-6 top-3 sm:top-5 z-[1001] pointer-events-auto">
          <TopPollutedDropdown
            zones={zones}
            selectedZone={selectedZone}
            onSelectZone={onSelectZone}
          />
        </div>

        {/* Draggable Environmental Metric Spheres */}
        <DraggableMetricSpheres
          rainfallMm={rainfallMm}
          humidityPercent={humidityPercent}
          temperatureC={temperatureC}
          aqiOrPm25={aqiOrPm25}
          containerRef={overlayContainerRef}
        />

        {/* Bottom Floating Legend (Left) & Controls (Right) positioned directly above the bottom cards */}
        <div className="flex items-end justify-between w-full mt-auto mb-2 sm:mb-3 pointer-events-none">
          <div className="pointer-events-auto">
            <PollutionLegend metricLabel="CO₂ / AQI concentration" />
          </div>

          <div className="pointer-events-auto">
            <MapControls
              showContours={showContours}
              onToggleContours={() => setShowContours(!showContours)}
              showStations={showStations}
              onToggleStations={() => setShowStations(!showStations)}
              onRecenter={() => {
                mapInstance?.flyTo(activeCenter, 12, { duration: 1.2 });
              }}
              onZoomIn={() => mapInstance?.zoomIn()}
              onZoomOut={() => mapInstance?.zoomOut()}
              onResetLayout={() => {
                window.dispatchEvent(new CustomEvent('clearsky-reset-spheres'));
              }}
            />
          </div>
        </div>

        {/* 3 Floating Glass Analytics Cards Hovering Directly Above the Map */}
        {children && (
          <div className="w-full pointer-events-none z-[1002] mb-1 sm:mb-2">
            {children}
          </div>
        )}
      </div>
    </div>
  );
};

export default InteractivePollutionMap;
