import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Wind, Droplets, ShieldCheck, MapPin, Sparkles, Activity, Layers, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { SystemOverview } from '../types';

export const LandingPage: React.FC = () => {
  const [overview, setOverview] = useState<SystemOverview | null>(null);

  useEffect(() => {
    api.getOverview().then(setOverview).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-warm-50 text-earth-800 font-clarendon selection:bg-accent-500 selection:text-white">

      {/* Editorial Top Navigation */}
      <header className="w-full max-w-6xl mx-auto px-6 py-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-warm-100 border border-warm-300 flex items-center justify-center p-1.5 shadow-warm-sm">
            <svg viewBox="0 0 32 32" className="w-full h-full" fill="none">
              <circle cx="16" cy="16" r="13" stroke="#D4C5B3" strokeWidth="1.5" strokeDasharray="2 2" />
              <path d="M6 21 Q 16 11 26 21" stroke="#F06B42" strokeWidth="2.5" strokeLinecap="round" />
              <path d="M8 15 Q 16 6 24 15" stroke="#3DA88E" strokeWidth="2" strokeLinecap="round" />
              <circle cx="16" cy="11" r="2.5" fill="#F06B42" />
            </svg>
          </div>
          <div>
            <span className="font-sentinel font-bold text-xl text-earth-900 tracking-tight">ClearSky</span>
            <span className="font-sans text-[10px] tracking-wider uppercase ml-1.5 px-2 py-0.5 rounded-full bg-accent-500/10 text-accent-600 font-semibold border border-accent-500/20">
              Intelligence
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-6">
          <Link
            to="/citizen-watch"
            className="hidden sm:inline-flex items-center gap-1.5 font-sans text-xs font-semibold text-accent-600 hover:text-accent-700 transition-colors"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Citizen Watch</span>
          </Link>
          <Link
            to="/methodology"
            className="hidden sm:inline-block font-sans text-xs font-medium text-earth-600 hover:text-earth-900 transition-colors"
          >
            Scientific Methodology
          </Link>
          <Link
            to="/water-analytics"
            className="hidden sm:inline-block font-sans text-xs font-medium text-earth-600 hover:text-earth-900 transition-colors"
          >
            Water Audits
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-earth-900 hover:bg-earth-800 text-warm-50 font-sans text-xs font-semibold shadow-warm transition-all hover:-translate-y-0.5"
          >
            <span>Command Center</span>
            <ArrowRight className="w-3.5 h-3.5 text-accent-400" />
          </Link>
        </nav>
      </header>

      {/* Main Minimal Hero */}
      <main className="flex-1 flex flex-col justify-center max-w-4xl mx-auto px-6 pt-12 pb-24 text-center">
        
        {/* Live Status Pill */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/80 border border-warm-300 shadow-warm-sm mx-auto mb-8 animate-fade-up">
          <span className="w-2 h-2 rounded-full bg-sage-500 animate-pulse" />
          <span className="font-sans text-xs font-medium text-earth-600">
            Delhi NCR Environmental Telemetry • 15 Corridors Active
          </span>
        </div>

        {/* Hero Headline in Sentinel */}
        <h1 className="font-sentinel font-bold text-5xl sm:text-6xl md:text-7xl text-earth-900 tracking-tight leading-[1.08] mb-8 animate-fade-up">
          Smarter environmental decisions.
          <span className="block italic font-medium text-accent-500 mt-1">
            Cleaner, sustainable cities.
          </span>
        </h1>

        {/* Hero Narrative in Clarendon */}
        <p className="font-clarendon text-lg sm:text-xl text-earth-600 leading-relaxed max-w-2xl mx-auto mb-12 animate-fade-up">
          ClearSky Intelligence combines ground air observations, atmospheric dispersion models, and thermal anomaly tracking to ensure urban dust suppression operates only when scientifically effective—conserving millions of liters of municipal water.
        </p>

        {/* Refined Action CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-20 animate-fade-up">
          <Link
            to="/dashboard"
            className="group flex items-center justify-center gap-2.5 w-full sm:w-auto px-8 py-4 rounded-2xl bg-accent-500 hover:bg-accent-600 text-white font-sans font-semibold text-base shadow-warm-lg hover:shadow-warm-xl transition-all duration-300 hover:-translate-y-0.5"
          >
            <span>Open Regional Dashboard</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>

          <Link
            to="/map"
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 rounded-2xl bg-white hover:bg-warm-100 text-earth-800 font-sans font-medium text-base border border-warm-300 shadow-warm-sm hover:shadow-warm transition-all duration-300"
          >
            <MapPin className="w-4 h-4 text-accent-500" />
            <span>Interactive NCR Map</span>
          </Link>

          <Link
            to="/citizen-watch"
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 rounded-2xl bg-white hover:bg-warm-100 text-earth-800 font-sans font-medium text-base border border-warm-300 shadow-warm-sm hover:shadow-warm transition-all duration-300"
          >
            <ShieldAlert className="w-4 h-4 text-accent-500" />
            <span>Citizen Watch &amp; Eco-Points</span>
          </Link>
        </div>

        {/* Minimal 3-Pillar Clean Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          
          <div className="p-6 rounded-2xl bg-white/90 border border-warm-200 shadow-warm-sm hover:shadow-warm transition-all duration-300">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500 mb-4">
              <Wind className="w-5 h-5" />
            </div>
            <h3 className="font-sentinel font-bold text-lg text-earth-900 mb-2">
              Surgical Suppression
            </h3>
            <p className="font-clarendon text-xs text-earth-600 leading-relaxed">
              Anti-smog guns only impact heavy coarse dust (PM10). ClearSky prevents ineffective deployment during biomass smoke or fine haze.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-white/90 border border-warm-200 shadow-warm-sm hover:shadow-warm transition-all duration-300">
            <div className="w-10 h-10 rounded-xl bg-sage-500/10 border border-sage-500/20 flex items-center justify-center text-sage-500 mb-4">
              <Droplets className="w-5 h-5" />
            </div>
            <h3 className="font-sentinel font-bold text-lg text-earth-900 mb-2">
              Water Preservation
            </h3>
            <p className="font-clarendon text-xs text-earth-600 leading-relaxed">
              Dynamic suppression replaces uncalibrated 3x daily schedules, saving 60%–75% of tanker water for genuine urban hotspots.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-white/90 border border-warm-200 shadow-warm-sm hover:shadow-warm transition-all duration-300">
            <div className="w-10 h-10 rounded-xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center text-accent-500 mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="font-sentinel font-bold text-lg text-earth-900 mb-2">
              Auditable AI Logic
            </h3>
            <p className="font-clarendon text-xs text-earth-600 leading-relaxed">
              Every mitigation recommendation exposes plain-English scientific reasoning, confidence bounds, and meteorological triggers.
            </p>
          </div>

        </div>

        {/* Minimal Live Stats Snapshot */}
        <div className="mt-12 p-6 rounded-2xl bg-warm-100/70 border border-warm-300/80 flex flex-col sm:flex-row items-center justify-around gap-6 text-center">
          <div>
            <div className="font-sans text-xs uppercase tracking-wider text-earth-500 font-semibold mb-1">
              Monitored Corridors
            </div>
            <div className="font-sentinel font-bold text-2xl sm:text-3xl text-earth-900">
              {overview?.total_monitored_zones || 15} Sectors
            </div>
          </div>

          <div className="hidden sm:block w-px h-10 bg-warm-300" />

          <div>
            <div className="font-sans text-xs uppercase tracking-wider text-earth-500 font-semibold mb-1">
              Active Candidates
            </div>
            <div className="font-sentinel font-bold text-2xl sm:text-3xl text-accent-500">
              {overview?.intervention_candidates ?? 4} Targeted
            </div>
          </div>

          <div className="hidden sm:block w-px h-10 bg-warm-300" />

          <div>
            <div className="font-sans text-xs uppercase tracking-wider text-earth-500 font-semibold mb-1">
              Suppressed / Saved
            </div>
            <div className="font-sentinel font-bold text-2xl sm:text-3xl text-sage-600">
              {overview?.intervention_discouraged ?? 8} Avoided
            </div>
          </div>
        </div>

        {/* Minimal byline */}
        <div className="mt-14 text-xs font-sans text-earth-500">
          Engineered by <span className="font-semibold text-earth-800">Quantified Minds</span> — Ishaan Chaturvedi &amp; Ankit Kumar Tiwari
        </div>

      </main>

    </div>
  );
};
