import React from 'react';
import { Sparkles } from 'lucide-react';
import { AiDailyBrief } from '../types';

interface DailyBriefBannerProps {
  brief?: AiDailyBrief | null;
}

export const DailyBriefBanner: React.FC<DailyBriefBannerProps> = ({ brief }) => {
  if (!brief) return null;

  return (
    <div className="bg-white rounded-2xl p-5 border border-accent-400/30 shadow-warm relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-accent-400/5 rounded-full blur-2xl pointer-events-none" />
      
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-warm-200">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <span className="font-sentinel font-bold text-sm text-earth-900">
            Daily Atmospheric Brief
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-[10px] text-earth-500 font-mono">
          <span>Provider: <span className="text-earth-700 font-medium">{brief.provider}</span></span>
        </div>
      </div>

      <p className="text-earth-700 text-sm leading-relaxed mb-3 font-clarendon">
        {brief.summary_text}
      </p>

      {brief.high_priority_zones && brief.high_priority_zones.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-warm-200/60">
          <span className="text-[11px] font-sans font-medium text-accent-600">Hotspots:</span>
          {brief.high_priority_zones.map((zone, idx) => (
            <span
              key={idx}
              className="text-[11px] font-mono px-2 py-0.5 rounded-lg bg-warm-100 border border-warm-200 text-earth-700"
            >
              {zone}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
