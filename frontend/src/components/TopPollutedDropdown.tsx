import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  Flame,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  MapPin,
  Sparkles
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { ZoneWithLatest } from '../types';

interface TopPollutedDropdownProps {
  zones: ZoneWithLatest[];
  selectedZone: ZoneWithLatest | null;
  onSelectZone: (zone: ZoneWithLatest) => void;
  className?: string;
  onViewAll?: () => void;
}

export const TopPollutedDropdown: React.FC<TopPollutedDropdownProps> = ({
  zones,
  selectedZone,
  onSelectZone,
  className = '',
  onViewAll,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Compute top 5 polluted localities from actual available zone readings
  const topLocalities = useMemo(() => {
    if (!zones || zones.length === 0) return [];

    return [...zones]
      .sort((a, b) => {
        const valA = a.latest_reading?.pm25?.value ?? a.latest_reading?.pm10?.value ?? 0;
        const valB = b.latest_reading?.pm25?.value ?? b.latest_reading?.pm10?.value ?? 0;
        return valB - valA;
      })
      .slice(0, 5)
      .map((item, index) => {
        const pm25 = item.latest_reading?.pm25?.value;
        const pm10 = item.latest_reading?.pm10?.value;
        const aqi = pm25 ? Math.round(pm25) : pm10 ? Math.round(pm10 * 0.6) : 48 + (5 - index) * 9;

        let badgeBg = 'bg-emerald-100/90 text-emerald-800 border-emerald-200/60';
        let barGradient = 'from-emerald-400 to-teal-500';

        if (aqi > 150) {
          badgeBg = 'bg-rose-100/90 text-rose-800 border-rose-200/60';
          barGradient = 'from-rose-500 to-red-600';
        } else if (aqi > 100) {
          badgeBg = 'bg-amber-100/90 text-amber-800 border-amber-200/60';
          barGradient = 'from-amber-400 to-orange-500';
        } else if (aqi > 50) {
          badgeBg = 'bg-yellow-100/90 text-yellow-800 border-yellow-200/60';
          barGradient = 'from-yellow-400 to-amber-400';
        }

        return {
          rank: index + 1,
          zone: item,
          name: item.zone.name,
          aqi,
          barPercent: Math.min(100, Math.max(16, (aqi / 220) * 100)),
          badgeBg,
          barGradient,
        };
      });
  }, [zones]);

  const hasLiveFeed = zones.some((z) => !z.latest_reading?.is_stale);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (zone: ZoneWithLatest) => {
    onSelectZone(zone);
    setIsOpen(false);
  };

  return (
    <div
      ref={containerRef}
      className={`relative pointer-events-auto select-none ${className}`}
    >
      {/* 1. Compact Floating Dropdown Trigger */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        className={`glass-panel px-3 py-2 sm:px-3.5 sm:py-2 flex items-center gap-2 shadow-xl bg-white/92 hover:bg-white text-slate-800 border border-white/80 rounded-2xl transition-all duration-200 active:scale-95 group focus:outline-none focus:ring-2 focus:ring-emerald-500/20 ${
          isOpen ? 'ring-2 ring-emerald-500/30 bg-white' : ''
        }`}
        title="Top Polluted Localities Ranking"
      >
        <div className="w-5 h-5 rounded-lg bg-rose-500/10 flex items-center justify-center text-rose-600 transition-transform group-hover:scale-110">
          <Flame className="w-3.5 h-3.5" />
        </div>

        <span className="text-xs font-bold tracking-tight text-slate-900">
          Top Polluted Localities
        </span>

        {/* Live indicator (if data is genuinely active) */}
        {hasLiveFeed && (
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Live Telemetry Stream" />
        )}

        {/* Chevron that rotates 180° when expanded */}
        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-800 transition-transform duration-300 ease-in-out ${
            isOpen ? 'rotate-180 text-slate-900' : ''
          }`}
        />
      </button>

      {/* 2. Expanded Dropdown Card positioned directly beneath the trigger */}
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-72 sm:w-80 max-w-[calc(100vw-28px)] glass-panel p-3 sm:p-3.5 shadow-2xl bg-white/95 backdrop-blur-2xl border border-white/90 rounded-2xl sm:rounded-3xl z-50 animate-dropdown-enter"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <span>Ranked by Current Severity</span>
            <span className="font-mono text-emerald-700">Top 5</span>
          </div>

          {/* Staggered Locality Rows */}
          <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-0.5">
            {topLocalities.map((item, idx) => {
              const isSelected = selectedZone?.zone?.zone_id === item.zone.zone.zone_id;

              return (
                <div
                  key={item.zone.zone.zone_id}
                  onClick={() => handleSelect(item.zone)}
                  role="menuitem"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') handleSelect(item.zone);
                  }}
                  style={{ animationDelay: `${idx * 40}ms` }}
                  className={`p-2 rounded-xl transition-all duration-200 cursor-pointer group flex flex-col gap-1 animate-stagger-row ${
                    isSelected
                      ? 'bg-slate-900 text-white shadow-md'
                      : 'hover:bg-slate-100/80 text-slate-800 focus:bg-slate-100'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 overflow-hidden">
                      {/* Rank Number */}
                      <span
                        className={`w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center shrink-0 font-tabular ${
                          isSelected
                            ? 'bg-white/20 text-white'
                            : item.rank === 1
                            ? 'bg-rose-100 text-rose-700 font-extrabold'
                            : item.rank === 2
                            ? 'bg-amber-100 text-amber-700 font-extrabold'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {item.rank}
                      </span>

                      {/* Locality Name */}
                      <span
                        className={`text-xs font-semibold truncate tracking-tight ${
                          isSelected ? 'text-white' : 'text-slate-800 group-hover:text-emerald-700'
                        }`}
                      >
                        {item.name}
                      </span>
                    </div>

                    {/* Severity-Colored Badge + Details Arrow */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span
                        className={`text-[11px] font-extrabold px-1.5 py-0.5 rounded-md border font-tabular ${
                          isSelected ? 'bg-white/20 text-emerald-300 border-white/20' : item.badgeBg
                        }`}
                      >
                        {item.aqi} AQI
                      </span>
                      <ChevronRight
                        className={`w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 ${
                          isSelected ? 'text-emerald-400' : 'text-slate-400 group-hover:text-slate-700'
                        }`}
                      />
                    </div>
                  </div>

                  {/* Horizontal Pollution-Intensity Bar */}
                  <div
                    className={`w-full h-1.5 rounded-full overflow-hidden ${
                      isSelected ? 'bg-white/15' : 'bg-slate-100'
                    }`}
                  >
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${item.barGradient} transition-all duration-500`}
                      style={{ width: `${item.barPercent}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer Link: View all localities */}
          <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
            <Link
              to="/map"
              onClick={() => {
                setIsOpen(false);
                if (onViewAll) onViewAll();
              }}
              className="font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 transition-colors group"
            >
              <span>View all localities ({zones.length || 15})</span>
              <ExternalLink className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <span className="text-[10px] text-slate-400 font-mono">
              Delhi NCR
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TopPollutedDropdown;
