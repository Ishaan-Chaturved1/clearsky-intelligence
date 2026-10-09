import React from 'react';
import { ShieldCheck, Droplets, Info } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white/50 backdrop-blur-sm border-t border-warm-200 mt-16 text-earth-500 text-xs py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-6 border-b border-warm-200">
          
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="font-sentinel font-bold text-earth-900 text-sm">ClearSky Intelligence</span>
              <span className="text-[10px] text-accent-600 font-mono font-medium px-1.5 py-0.5 bg-accent-500/10 rounded-md border border-accent-500/20">v1.2</span>
            </div>
            <p className="font-clarendon text-earth-500 leading-relaxed text-[11px]">
              AI-powered environmental decision support for municipal air quality operations.
            </p>
          </div>

          <div>
            <span className="font-sentinel font-bold text-earth-800 text-xs block mb-2">
              Engineering Team
            </span>
            <p className="text-[11px] text-earth-500 mb-1">
              <span className="text-earth-700 font-medium">Team:</span> Quantified Minds
            </p>
            <p className="text-[11px] text-earth-500">
              <span className="text-earth-700 font-medium">Engineers:</span> Ishaan Chaturvedi &amp; Ankit Kumar Tiwari
            </p>
          </div>

          <div>
            <div className="flex items-center gap-1.5 text-accent-600 text-[11px] font-medium mb-1">
              <Info className="w-3.5 h-3.5 flex-shrink-0" />
              <span>Scientific Disclaimer</span>
            </div>
            <p className="text-[11px] text-earth-400 leading-relaxed">
              ClearSky Intelligence does not claim anti-smog mist guns eliminate fine PM2.5. Water savings represent model-projected avoidance relative to configurable baseline schedules.
            </p>
          </div>

        </div>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-earth-400">
          <p>© {new Date().getFullYear()} ClearSky Intelligence by Quantified Minds.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 text-earth-500">
              <ShieldCheck className="w-3.5 h-3.5 text-sage-500" />
              <span>Rule Audited</span>
            </span>
            <span className="flex items-center gap-1 text-earth-500">
              <Droplets className="w-3.5 h-3.5 text-sage-400" />
              <span>Water Conservation</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
