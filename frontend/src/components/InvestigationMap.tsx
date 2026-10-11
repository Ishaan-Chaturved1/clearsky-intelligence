import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import { CandidateSource, TrajectoryPoint, FireDetectionRecord } from '../types';
import { Compass, Flame, Factory, Construction, AlertTriangle, ShieldCheck } from 'lucide-react';

interface InvestigationMapProps {
  centerLat: number;
  centerLon: number;
  radiusKm: number;
  candidateSources: CandidateSource[];
  trajectoryPoints: TrajectoryPoint[];
  fireRecords: FireDetectionRecord[];
  targetName?: string;
  height?: string;
  onMapClick?: (lat: number, lon: number) => void;
}

// Controller to fly to center coordinates
const MapRecenter: React.FC<{ coords: [number, number] }> = ({ coords }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(coords, 12, { duration: 1.0 });
  }, [coords, map]);
  return null;
};

// Target Location Icon
const targetIcon = L.divIcon({
  className: 'custom-target-marker',
  html: `
    <div style="position: relative; width: 36px; height: 36px;">
      <div style="position: absolute; inset: 0; background: #3B82F6; opacity: 0.3; border-radius: 9999px; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>
      <div style="position: absolute; inset: 4px; background: #1D4ED8; border: 2.5px solid white; border-radius: 9999px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
        <div style="width: 8px; height: 8px; background: white; border-radius: 9999px;"></div>
      </div>
    </div>
  `,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

// Category-specific Candidate Source Icon generator
function createCandidateIcon(category: string) {
  let bgColor = '#8B5CF6'; // purple industrial
  let iconSvg = '🏭';

  if (category.toLowerCase().includes('road') || category.toLowerCase().includes('traffic')) {
    bgColor = '#3B82F6'; // blue
    iconSvg = '🛣️';
  } else if (category.toLowerCase().includes('construction')) {
    bgColor = '#F59E0B'; // amber
    iconSvg = '🚧';
  } else if (category.toLowerCase().includes('waste') || category.toLowerCase().includes('landfill')) {
    bgColor = '#78350F'; // brown
    iconSvg = '🗑️';
  } else if (category.toLowerCase().includes('biomass') || category.toLowerCase().includes('fire')) {
    bgColor = '#EF4444'; // red
    iconSvg = '🔥';
  }

  return L.divIcon({
    className: 'custom-candidate-marker',
    html: `
      <div style="background: ${bgColor}; width: 28px; height: 28px; border-radius: 9999px; border: 2px solid white; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.2); font-size: 13px;">
        ${iconSvg}
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

// Satellite Fire Icon
function createFireIcon(isCorridorAligned: boolean) {
  const border = isCorridorAligned ? '2.5px solid #FEF08A' : '1.5px solid white';
  const shadow = isCorridorAligned ? 'box-shadow: 0 0 10px #F97316;' : 'box-shadow: 0 2px 4px rgba(0,0,0,0.2);';
  return L.divIcon({
    className: 'custom-fire-marker',
    html: `
      <div style="background: #EA580C; width: 26px; height: 26px; border-radius: 9999px; ${border} display: flex; align-items: center; justify-content: center; ${shadow} font-size: 13px;">
        🔥
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

// Trajectory Step Node Icon
function createTrajectoryStepIcon(stepHour: number) {
  return L.divIcon({
    className: 'custom-step-marker',
    html: `
      <div style="background: #0284C7; color: white; width: 20px; height: 20px; border-radius: 9999px; border: 1.5px solid white; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.3);">
        -${Math.round(stepHour)}h
      </div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

export const InvestigationMap: React.FC<InvestigationMapProps> = ({
  centerLat,
  centerLon,
  radiusKm,
  candidateSources,
  trajectoryPoints,
  fireRecords,
  targetName = 'Investigation Origin',
  height = '520px',
  onMapClick
}) => {
  const centerCoords: [number, number] = [centerLat, centerLon];

  // Polyline coordinates for backward trajectory
  const trajectoryLatLngs: [number, number][] = trajectoryPoints.map((p) => [p.latitude, p.longitude]);

  return (
    <div className="relative w-full rounded-2xl overflow-hidden border border-warm-200 shadow-warm-sm bg-warm-100">
      <MapContainer
        center={centerCoords}
        zoom={12}
        style={{ height, width: '100%' }}
        scrollWheelZoom={true}
      >
        <MapRecenter coords={centerCoords} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Search Radius Boundary Circle */}
        <Circle
          center={centerCoords}
          radius={radiusKm * 1000}
          pathOptions={{
            color: '#3B82F6',
            fillColor: '#3B82F6',
            fillOpacity: 0.04,
            dashArray: '4 6',
            weight: 1.5
          }}
        />

        {/* Backward Atmospheric Transport Trajectory Polyline */}
        {trajectoryLatLngs.length > 1 && (
          <Polyline
            positions={trajectoryLatLngs}
            pathOptions={{
              color: '#0284C7',
              weight: 3.5,
              opacity: 0.85,
              dashArray: '8 6',
            }}
          />
        )}

        {/* Step Nodes along Trajectory */}
        {trajectoryPoints.map((pt, idx) => {
          if (idx === 0) return null; // Origin node handled by targetIcon
          return (
            <Marker
              key={`traj_pt_${idx}`}
              position={[pt.latitude, pt.longitude]}
              icon={createTrajectoryStepIcon(pt.step_hours_back)}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs">
                  <div className="font-semibold text-earth-900">
                    Trajectory Step -{pt.step_hours_back}h
                  </div>
                  <div className="text-earth-680 text-[11px]">
                    Time: {new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
                  </div>
                  <div className="text-earth-700">
                    Wind: {pt.wind_speed_kmh} km/h from {pt.wind_direction_deg}°
                  </div>
                  {pt.boundary_layer_height_m && (
                    <div className="text-earth-700">
                      Boundary Layer: {Math.round(pt.boundary_layer_height_m)} m
                    </div>
                  )}
                  <div className="text-[10px] text-earth-500 italic mt-1">
                    {pt.is_forecast ? 'Modeled forecast meteorological step' : 'Observed historical weather step'}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Target Investigation Origin Marker */}
        <Marker position={centerCoords} icon={targetIcon}>
          <Popup>
            <div className="p-1 text-xs">
              <div className="font-bold text-earth-900">{targetName}</div>
              <div className="text-earth-600 text-[11px]">
                {centerLat.toFixed(4)}°N, {centerLon.toFixed(4)}°E
              </div>
              <div className="mt-1 text-[11px] font-medium text-blue-700">
                Investigation Target Location
              </div>
            </div>
          </Popup>
        </Marker>

        {/* Candidate Local Sources (OSM) */}
        {candidateSources.map((cand) => {
          if (!cand.latitude || !cand.longitude) return null;
          return (
            <Marker
              key={`cand_${cand.source_id}`}
              position={[cand.latitude, cand.longitude]}
              icon={createCandidateIcon(cand.category)}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs max-w-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-earth-900">{cand.name}</span>
                  </div>
                  <div className="text-[10px] font-semibold tracking-wider uppercase text-purple-700">
                    Category: {cand.category.replace(/_/g, ' ')}
                  </div>
                  {cand.distance_km && (
                    <div className="text-earth-700 text-[11px]">
                      Distance: {cand.distance_km.toFixed(1)} km ({cand.compass_direction || 'vicinity'})
                    </div>
                  )}
                  <div className="text-earth-500 text-[10px]">
                    Source: {cand.provider}
                  </div>
                  <div className="bg-amber-50 text-amber-800 p-1.5 rounded text-[10px] border border-amber-200 mt-1">
                    <strong>Status: {cand.verification_status}</strong>
                    <br />
                    Mapped infrastructure feature; real emissions unverified without localized physical sensors.
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* NASA FIRMS Satellite Fire Detections */}
        {fireRecords.map((fire) => (
          <Marker
            key={`fire_${fire.fire_id}`}
            position={[fire.latitude, fire.longitude]}
            icon={createFireIcon(fire.plausible_smoke_corridor)}
          >
            <Popup>
              <div className="p-1 space-y-1 text-xs max-w-xs">
                <div className="font-bold text-red-900 flex items-center gap-1">
                  <span>Satellite Thermal Anomaly</span>
                </div>
                <div className="text-earth-700 text-[11px]">
                  Distance: {fire.distance_from_event_km.toFixed(1)} km {fire.bearing_compass}
                </div>
                <div className="text-earth-700 text-[11px]">
                  Sensor: {fire.satellite_instrument} | Brightness: {fire.brightness} K
                </div>
                {fire.distance_to_trajectory_km !== null && (
                  <div className="text-earth-700 text-[11px]">
                    Distance to Upwind Trajectory: {fire.distance_to_trajectory_km} km
                  </div>
                )}
                {fire.plausible_smoke_corridor ? (
                  <div className="bg-orange-50 text-orange-800 p-1.5 rounded text-[10px] border border-orange-200 font-medium">
                    Aligned with backward atmospheric transport corridor (&le; 25 km).
                  </div>
                ) : (
                  <div className="bg-gray-50 text-gray-700 p-1.5 rounded text-[10px] border border-gray-200">
                    Outside primary upwind transport corridor.
                  </div>
                )}
                <div className="text-[10px] text-earth-500 italic mt-1">
                  Thermal detection alone does not identify fuel type or confirm AQI contribution.
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      {/* Accessible Map Legend */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-white/95 backdrop-blur-md rounded-xl p-3 border border-warm-200 shadow-warm-md text-xs space-y-2 pointer-events-auto max-w-xs">
        <div className="font-bold text-earth-900 border-b border-warm-200 pb-1 text-[11px] uppercase tracking-wider">
          Investigation Map Legend
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] text-earth-700">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-blue-600 border border-white inline-block shadow-sm"></span>
            <span>Target Location</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 border-t-2 border-dashed border-sky-600 inline-block"></span>
            <span>Upwind Path</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-purple-500 border border-white inline-block"></span>
            <span>Candidate Source</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-orange-600 border border-white inline-block"></span>
            <span>Satellite Fire</span>
          </div>
        </div>
        <div className="text-[10px] text-earth-500 italic border-t border-warm-100 pt-1">
          Candidate sources represent mapped infrastructure, not confirmed emitters.
        </div>
      </div>
    </div>
  );
};
