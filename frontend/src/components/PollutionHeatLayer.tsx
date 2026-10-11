import React, { useMemo } from 'react';
import { SVGOverlay } from 'react-leaflet';
import L from 'leaflet';
import { ZoneWithLatest } from '../types';

interface PollutionHeatLayerProps {
  center: [number, number];
  intensity?: number; // 0 to 500 AQI
  visible?: boolean;
  zones?: ZoneWithLatest[];
}

export const PollutionHeatLayer: React.FC<PollutionHeatLayerProps> = ({
  center,
  intensity = 160,
  visible = true,
  zones = [],
}) => {
  if (!visible) return null;

  // Compute bounding box around primary center (approx 25km radius)
  const primaryBounds: L.LatLngBoundsExpression = useMemo(() => {
    const latSpan = 0.22;
    const lonSpan = 0.26;
    return [
      [center[0] - latSpan, center[1] - lonSpan],
      [center[0] + latSpan, center[1] + lonSpan],
    ];
  }, [center]);

  // Secondary candidate zones with significant particulate levels
  const secondaryHotspots = useMemo(() => {
    return zones
      .filter((item) => {
        const isFarFromCenter =
          Math.abs(item.zone.latitude - center[0]) > 0.04 ||
          Math.abs(item.zone.longitude - center[1]) > 0.04;
        const pm = item.latest_reading?.pm10?.value || item.latest_reading?.pm25?.value || 0;
        return isFarFromCenter && pm > 120;
      })
      .slice(0, 3)
      .map((item) => {
        const latSpan = 0.11;
        const lonSpan = 0.13;
        return {
          id: item.zone.zone_id,
          bounds: [
            [item.zone.latitude - latSpan, item.zone.longitude - lonSpan],
            [item.zone.latitude + latSpan, item.zone.longitude + lonSpan],
          ] as L.LatLngBoundsExpression,
          pm: item.latest_reading?.pm10?.value || 140,
        };
      });
  }, [zones, center]);

  return (
    <>
      {/* 1. Primary Selected Center Seamless Atmospheric Plume */}
      <SVGOverlay bounds={primaryBounds}>
        <svg
          viewBox="0 0 1000 1000"
          className="w-full h-full pointer-events-none select-none transition-opacity duration-700 ease-out"
          style={{ overflow: 'visible' }}
        >
          <defs>
            {/* Gaussian blur to completely eliminate stepped rings and blend atmospheric plume */}
            <filter id="atmosphericSoftBlur" x="-35%" y="-35%" width="170%" height="170%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="32" />
            </filter>

            {/* Continuous smooth multi-stop progression: Red -> Coral -> Orange -> Amber -> Yellow -> Lime -> Green -> 0% Transparent */}
            <radialGradient id="seamlessPrimaryPlume" cx="50%" cy="50%" r="50%" fx="50%" fy="50%">
              <stop offset="0%" stopColor="#dc2626" stopOpacity="0.52" />
              <stop offset="12%" stopColor="#ef4444" stopOpacity="0.48" />
              <stop offset="24%" stopColor="#f97316" stopOpacity="0.42" />
              <stop offset="38%" stopColor="#f59e0b" stopOpacity="0.34" />
              <stop offset="52%" stopColor="#eab308" stopOpacity="0.26" />
              <stop offset="66%" stopColor="#84cc16" stopOpacity="0.18" />
              <stop offset="80%" stopColor="#22c55e" stopOpacity="0.10" />
              <stop offset="92%" stopColor="#15803d" stopOpacity="0.03" />
              <stop offset="100%" stopColor="#15803d" stopOpacity="0.0" />
            </radialGradient>
          </defs>

          {/* Organic breathing atmospheric cloud */}
          <circle
            cx="500"
            cy="500"
            r="480"
            fill="url(#seamlessPrimaryPlume)"
            filter="url(#atmosphericSoftBlur)"
            className="plume-animate"
          />
        </svg>
      </SVGOverlay>

      {/* 2. Secondary Monitored Hotspots (Blended seamlessly into the map) */}
      {secondaryHotspots.map((spot) => (
        <SVGOverlay key={`hotspot-${spot.id}`} bounds={spot.bounds}>
          <svg
            viewBox="0 0 600 600"
            className="w-full h-full pointer-events-none select-none"
            style={{ overflow: 'visible' }}
          >
            <defs>
              <filter id={`blur-${spot.id}`} x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="20" />
              </filter>
              <radialGradient id={`grad-${spot.id}`} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#f97316" stopOpacity="0.40" />
                <stop offset="30%" stopColor="#f59e0b" stopOpacity="0.30" />
                <stop offset="60%" stopColor="#eab308" stopOpacity="0.18" />
                <stop offset="85%" stopColor="#84cc16" stopOpacity="0.08" />
                <stop offset="100%" stopColor="#22c55e" stopOpacity="0.0" />
              </radialGradient>
            </defs>
            <circle
              cx="300"
              cy="300"
              r="280"
              fill={`url(#grad-${spot.id})`}
              filter={`url(#blur-${spot.id})`}
              className="plume-animate"
            />
          </svg>
        </SVGOverlay>
      ))}
    </>
  );
};

export default PollutionHeatLayer;
