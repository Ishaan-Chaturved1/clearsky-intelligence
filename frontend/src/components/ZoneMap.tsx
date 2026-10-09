import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { ZoneWithLatest } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatNumber } from '../utils/formatters';

interface ZoneMapProps {
  zones: ZoneWithLatest[];
  selectedZone: ZoneWithLatest | null;
  onSelectZone: (zone: ZoneWithLatest) => void;
  height?: string;
}

// Controller to handle center reset and panning to selected zone
const MapController: React.FC<{ center: [number, number]; zoom: number; selectedCoords?: [number, number] }> = ({
  center,
  zoom,
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

// Custom SVG marker generator with warm theme
function createZoneMarkerIcon(decision?: string, priority?: number | null) {
  let color = '#A08B72'; // Advisory warm gray
  let isPulse = false;

  if (decision === 'INTERVENTION_RECOMMENDED') {
    color = '#3DA88E'; // Sage green
    if (priority && priority >= 4) {
      color = '#F06B42'; // Coral accent for priority 4 & 5
      isPulse = true;
    }
  } else if (decision === 'INTERVENTION_NOT_RECOMMENDED') {
    color = '#D95430'; // Warm red
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

export const ZoneMap: React.FC<ZoneMapProps> = ({
  zones,
  selectedZone,
  onSelectZone,
  height = '520px'
}) => {
  const defaultCenter: [number, number] = [28.63, 77.18];
  const defaultZoom = 11;

  const selectedCoords: [number, number] | undefined = selectedZone
    ? [selectedZone.zone.latitude, selectedZone.zone.longitude]
    : undefined;

  return (
    <div className="relative rounded-2xl overflow-hidden border border-warm-200 bg-warm-100 shadow-warm">
      
      {/* Map Legend Header Overlay */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2">
        <div className="bg-white/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-warm-200 text-xs flex items-center gap-3 shadow-warm-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sage-500 inline-block" />
            <span className="text-earth-600">Recommended</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-accent-600 inline-block" />
            <span className="text-earth-600">Discouraged</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-earth-400 inline-block" />
            <span className="text-earth-600">Advisory</span>
          </div>
        </div>
      </div>

      <div style={{ height }}>
        <MapContainer
          center={defaultCenter}
          zoom={defaultZoom}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          <MapController center={defaultCenter} zoom={defaultZoom} selectedCoords={selectedCoords} />
          
          {/* Free watermark-free OpenStreetMap basemap by default, or CARTO if API key is provided */}
          <TileLayer
            attribution={
              import.meta.env.VITE_CARTO_API_KEY
                ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }
            url={
              import.meta.env.VITE_CARTO_API_KEY
                ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?api_key=${import.meta.env.VITE_CARTO_API_KEY}`
                : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }
          />

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
                      View Details
                    </button>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>

    </div>
  );
};
